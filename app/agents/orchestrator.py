# app/agents/orchestrator.py
from typing import Dict, Any
import logging
from datetime import datetime
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .conversation_agent import conversation_agent
from .kyc_agent import kyc_agent
from .credit_agent import credit_agent
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Orchestrates multiple agents for complete loan processing"""
    
    def __init__(self):
        self.agents = {
            "conversation": conversation_agent,
            "kyc": kyc_agent,
            "credit": credit_agent
        }
        
        self.workflow_stages = {
            "CONVERSATION": "conversation",
            "KYC_VERIFICATION": "kyc", 
            "CREDIT_ASSESSMENT": "credit",
            "LOAN_FINALIZATION": "conversation"
        }
        
        logger.info("🎯 Agent Orchestrator initialized")
    
    async def process_customer_request(self, request_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process customer request through appropriate agents"""
        try:
            session_id = input_data.get("session_id", "")
            
            # Load session context
            session_data = db_service.load_conversation(session_id) or {}
            
            # Route to appropriate workflow
            if request_type == "conversation":
                return await self._handle_conversation_flow(input_data, session_data)
            elif request_type == "kyc_verification":
                return await self._handle_kyc_flow(input_data, session_data)
            elif request_type == "credit_assessment":
                return await self._handle_credit_flow(input_data, session_data)
            elif request_type == "complete_loan_journey":
                return await self._handle_complete_journey(input_data, session_data)
            else:
                raise ValueError(f"Unknown request type: {request_type}")
                
        except Exception as e:
            logger.error(f"Orchestrator processing failed: {e}")
            return {
                "status": "error",
                "message": "Unable to process request. Please try again.",
                "error": str(e)
            }
    
    async def _handle_conversation_flow(self, input_data: Dict[str, Any], 
                                      session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conversation-based interactions"""
        session_id = input_data["session_id"]
        message = input_data["message"]
        
        # Process through conversation agent
        result = await conversation_agent.process_message(session_id, message)
        
        # Check if customer is qualified for next steps
        if result.get("customer_qualified"):
            # Automatically trigger KYC if customer is qualified
            result["next_workflow"] = "KYC_VERIFICATION"
            result["workflow_message"] = "Perfect! Let's now verify your documents to proceed with the loan approval."
        
        return {
            "status": "success",
            "agent_used": "conversation",
            "result": result,
            "session_id": session_id
        }
    
    async def _handle_kyc_flow(self, input_data: Dict[str, Any],
                             session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KYC verification workflow"""
        # Process through KYC agent
        kyc_result = await kyc_agent.process(input_data)
        
        # If KYC is verified, trigger credit assessment
        if kyc_result.get("verification_status") == "VERIFIED":
            # Prepare data for credit assessment
            customer_data = session_data.get("customer_data", {})
            customer_data.update(kyc_result.get("extracted_customer_info", {}))
            
            # Automatically run credit assessment
            credit_input = {
                "customer_data": customer_data,
                "loan_amount": customer_data.get("loan_amount", 500000),
                "loan_purpose": customer_data.get("purpose", "personal"),
                "kyc_data": kyc_result.get("extracted_customer_info", {})
            }
            
            credit_result = await credit_agent.process(credit_input)
            
            return {
                "status": "success",
                "agent_used": "kyc_and_credit",
                "kyc_result": kyc_result,
                "credit_result": credit_result,
                "workflow_complete": credit_result["loan_decision"]["approved"],
                "next_steps": "loan_finalization" if credit_result["loan_decision"]["approved"] else "improvement_plan"
            }
        
        return {
            "status": "success", 
            "agent_used": "kyc",
            "result": kyc_result,
            "next_workflow": "KYC_PENDING"
        }
    
    async def _handle_credit_flow(self, input_data: Dict[str, Any],
                                session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle credit assessment workflow"""
        credit_result = await credit_agent.process(input_data)
        
        return {
            "status": "success",
            "agent_used": "credit", 
            "result": credit_result,
            "loan_approved": credit_result["loan_decision"]["approved"]
        }
    
    async def _handle_complete_journey(self, input_data: Dict[str, Any],
                                     session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle complete loan application journey"""
        results = {}
        
        # Step 1: Initial conversation
        conv_result = await conversation_agent.process_message(
            input_data["session_id"],
            input_data.get("initial_message", "I need a loan")
        )
        results["conversation"] = conv_result
        
        # Step 2: Mock KYC (if customer qualified)
        if conv_result.get("customer_qualified"):
            kyc_input = {
                "customer_id": input_data["session_id"],
                "documents": input_data.get("documents", {}),
                "type": "complete_kyc"
            }
            kyc_result = await kyc_agent.process(kyc_input)
            results["kyc"] = kyc_result
            
            # Step 3: Credit assessment (if KYC passed)
            if kyc_result.get("verification_status") == "VERIFIED":
                customer_data = conv_result.get("customer_summary", {})
                customer_data.update(kyc_result.get("extracted_customer_info", {}))
                
                credit_input = {
                    "customer_data": customer_data,
                    "loan_amount": input_data.get("loan_amount", 500000),
                    "loan_purpose": input_data.get("loan_purpose", "personal"),
                    "kyc_data": kyc_result.get("extracted_customer_info", {})
                }
                
                credit_result = await credit_agent.process(credit_input)
                results["credit"] = credit_result
        
        # Generate final summary
        final_status = self._generate_journey_summary(results)
        
        return {
            "status": "success",
            "journey_complete": True,
            "results": results,
            "final_status": final_status,
            "processing_time": datetime.utcnow().isoformat()
        }
    
    def _generate_journey_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of complete customer journey"""
        summary = {
            "conversation_completed": "conversation" in results,
            "kyc_completed": "kyc" in results,
            "credit_assessment_completed": "credit" in results,
            "loan_approved": False,
            "overall_status": "incomplete"
        }
        
        if "credit" in results:
            credit_result = results["credit"]
            summary["loan_approved"] = credit_result["loan_decision"]["approved"]
            
            if summary["loan_approved"]:
                summary["overall_status"] = "approved"
                summary["loan_offer"] = credit_result.get("loan_offer")
            else:
                summary["overall_status"] = "rejected"
                summary["rejection_reason"] = credit_result["loan_decision"]["reason"]
        
        return summary
    
    async def get_workflow_status(self, session_id: str) -> Dict[str, Any]:
        """Get current workflow status for a session"""
        session_data = db_service.load_conversation(session_id)
        
        if not session_data:
            return {"status": "not_found", "message": "Session not found"}
        
        # Analyze session progress
        stage = session_data.get("stage", "GREETING")
        messages = session_data.get("messages", [])
        customer_data = session_data.get("customer_data", {})
        
        return {
            "session_id": session_id,
            "current_stage": stage,
            "conversation_turns": len(messages),
            "customer_qualified": stage in ["PRESENTATION", "CLOSING"],
            "customer_data": customer_data,
            "next_recommended_action": self._get_next_action(stage, customer_data),
            "progress_percentage": self._calculate_progress(stage, customer_data)
        }
    
    def _get_next_action(self, stage: str, customer_data: Dict[str, Any]) -> str:
        """Get next recommended action based on current stage"""
        if stage == "GREETING":
            return "Continue conversation to understand loan needs"
        elif stage == "NEEDS_ANALYSIS":
            return "Gather loan amount and purpose details"
        elif stage == "QUALIFICATION":
            return "Collect income and employment information"
        elif stage == "PRESENTATION":
            return "Present loan offer and handle objections"
        elif stage == "CLOSING":
            return "Proceed with KYC document collection"
        else:
            return "Continue conversation"
    
    def _calculate_progress(self, stage: str, customer_data: Dict[str, Any]) -> int:
        """Calculate completion percentage"""
        progress_map = {
            "GREETING": 10,
            "NEEDS_ANALYSIS": 30, 
            "QUALIFICATION": 50,
            "PRESENTATION": 70,
            "CLOSING": 90
        }
        
        base_progress = progress_map.get(stage, 0)
        
        # Add bonus for data completeness
        data_bonus = 0
        if customer_data.get("loan_amount"):
            data_bonus += 5
        if customer_data.get("purpose"):
            data_bonus += 5
        if customer_data.get("monthly_income"):
            data_bonus += 10
        
        return min(100, base_progress + data_bonus)

# Global instance
orchestrator = AgentOrchestrator()
