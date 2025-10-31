# app/agents/kyc_agent.py
from .base_agent import BaseAgent
from typing import Dict, Any, List
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class KYCAgent(BaseAgent):
    """KYC (Know Your Customer) Agent for document verification"""
    
    def __init__(self):
        super().__init__(
            name="KYCAgent",
            description="Handles customer verification and document processing"
        )
        
        self.required_documents = [
            "pan_card", "aadhar_card", "bank_statement", 
            "salary_slip", "employment_certificate"
        ]
        
        self.verification_status = {
            "PENDING": "Documents pending upload",
            "SUBMITTED": "Documents submitted for verification", 
            "VERIFIED": "All documents verified successfully",
            "REJECTED": "Documents need resubmission"
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process KYC verification request"""
        self.log_processing("kyc_verification_start", input_data)
        
        try:
            customer_id = input_data.get("customer_id")
            documents = input_data.get("documents", {})
            verification_type = input_data.get("type", "basic_kyc")
            
            # Perform document verification
            verification_result = await self._verify_documents(documents)
            
            # Extract customer information from documents
            extracted_info = self._extract_customer_info(documents)
            
            # Determine verification status
            status = self._determine_verification_status(verification_result)
            
            # Generate verification response
            response_text = await self._generate_kyc_response(status, verification_result)
            
            result = {
                "agent": self.name,
                "customer_id": customer_id,
                "verification_status": status,
                "documents_verified": verification_result,
                "extracted_customer_info": extracted_info,
                "response_text": response_text,
                "next_steps": self._get_next_steps(status),
                "compliance_score": self._calculate_compliance_score(verification_result),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.log_processing("kyc_verification_complete", result)
            return result
            
        except Exception as e:
            logger.error(f"KYC verification failed: {e}")
            return {
                "agent": self.name,
                "error": str(e),
                "verification_status": "ERROR",
                "response_text": "KYC verification encountered an error. Please try again."
            }
    
    async def _verify_documents(self, documents: Dict[str, Any]) -> Dict[str, Any]:
        """Verify uploaded documents"""
        verification_result = {}
        
        for doc_type in self.required_documents:
            doc_data = documents.get(doc_type)
            
            if doc_data:
                # Simulate document verification (in real system, use OCR/ML)
                verification_result[doc_type] = {
                    "status": "verified",
                    "confidence": 0.95,
                    "extracted_data": self._mock_extract_data(doc_type, doc_data),
                    "issues": []
                }
            else:
                verification_result[doc_type] = {
                    "status": "missing",
                    "confidence": 0.0,
                    "extracted_data": {},
                    "issues": ["Document not provided"]
                }
        
        return verification_result
    
    def _mock_extract_data(self, doc_type: str, doc_data: Any) -> Dict[str, Any]:
        """Mock data extraction from documents"""
        extracted_data = {}
        
        if doc_type == "pan_card":
            extracted_data = {
                "pan_number": "ABCDE1234F",
                "name": "Rahul Kumar",
                "father_name": "Suresh Kumar",
                "date_of_birth": "15/08/1995"
            }
        elif doc_type == "aadhar_card":
            extracted_data = {
                "aadhar_number": "1234-5678-9012",
                "name": "Rahul Kumar", 
                "address": "123, MG Road, Bangalore",
                "date_of_birth": "15/08/1995"
            }
        elif doc_type == "salary_slip":
            extracted_data = {
                "gross_salary": 75000,
                "net_salary": 65000,
                "employer": "Infosys Limited",
                "month": "September 2025"
            }
        
        return extracted_data
    
    def _extract_customer_info(self, documents: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and consolidate customer information"""
        customer_info = {
            "name": "",
            "date_of_birth": "",
            "address": "",
            "pan_number": "",
            "aadhar_number": "",
            "monthly_salary": 0,
            "employer": ""
        }
        
        # Extract from PAN card
        pan_data = documents.get("pan_card", {})
        if pan_data:
            customer_info["name"] = "Rahul Kumar"
            customer_info["pan_number"] = "ABCDE1234F"
            customer_info["date_of_birth"] = "15/08/1995"
        
        # Extract from salary slip
        salary_data = documents.get("salary_slip", {})
        if salary_data:
            customer_info["monthly_salary"] = 65000
            customer_info["employer"] = "Infosys Limited"
        
        return customer_info
    
    def _determine_verification_status(self, verification_result: Dict[str, Any]) -> str:
        """Determine overall verification status"""
        verified_count = sum(1 for doc in verification_result.values() if doc["status"] == "verified")
        total_required = len(self.required_documents)
        
        if verified_count == total_required:
            return "VERIFIED"
        elif verified_count >= total_required * 0.6:  # At least 60% verified
            return "SUBMITTED"
        else:
            return "PENDING"
    
    async def _generate_kyc_response(self, status: str, verification_result: Dict[str, Any]) -> str:
        """Generate human-readable KYC response"""
        if status == "VERIFIED":
            return "Congratulations! All your documents have been successfully verified. You can now proceed with your loan application."
        elif status == "SUBMITTED":
            missing_docs = [doc for doc, result in verification_result.items() if result["status"] == "missing"]
            return f"Good progress! We still need these documents to complete verification: {', '.join(missing_docs)}. Please upload them to proceed."
        else:
            return "Welcome! To process your loan application, we need you to upload your KYC documents. This helps us serve you better and comply with regulations."
    
    def _get_next_steps(self, status: str) -> List[str]:
        """Get next steps based on verification status"""
        if status == "VERIFIED":
            return ["Proceed to credit assessment", "Generate loan offer", "Prepare sanction letter"]
        elif status == "SUBMITTED":
            return ["Upload missing documents", "Wait for verification", "Check status"]
        else:
            return ["Upload PAN card", "Upload Aadhar card", "Upload salary slips", "Upload bank statements"]
    
    def _calculate_compliance_score(self, verification_result: Dict[str, Any]) -> float:
        """Calculate compliance score (0-100)"""
        verified_count = sum(1 for doc in verification_result.values() if doc["status"] == "verified")
        total_docs = len(verification_result)
        
        base_score = (verified_count / total_docs) * 100
        
        # Add quality bonus
        quality_bonus = 0
        for doc_result in verification_result.values():
            if doc_result["status"] == "verified" and doc_result["confidence"] > 0.9:
                quality_bonus += 5
        
        return min(100, base_score + quality_bonus)

# Global instance
kyc_agent = KYCAgent()
