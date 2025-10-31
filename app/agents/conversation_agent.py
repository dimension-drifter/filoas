# app/agents/conversation_agent.py
from typing import Dict, Any, List
import re
import logging
from datetime import datetime
from app.services.llm_service import llm_service
from app.services.database_service import db_service
from config.settings import settings

logger = logging.getLogger(__name__)

class ConversationAgent:
    """Main conversation agent for loan sales"""
    
    def __init__(self):
        self.name = "ConversationAgent"
        self.stages = [
            "GREETING", "NEEDS_ANALYSIS", "QUALIFICATION", 
            "PRESENTATION", "OBJECTION_HANDLING", "CLOSING"
        ]
    
    async def process_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Process customer message and generate response"""
        try:
            logger.info(f"🎯 Processing message for session: {session_id}")
            
            # Load session data
            session_data = db_service.load_conversation(session_id) or {
                'session_id': session_id,
                'stage': 'GREETING',
                'messages': [],
                'customer_data': {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Extract customer information
            extracted_info = self._extract_info(message)
            
            # Update customer data
            customer_data = session_data.get('customer_data', {})
            customer_data.update(extracted_info)
            
            # Determine next stage
            current_stage = session_data.get('stage', 'GREETING')
            next_stage = self._determine_next_stage(current_stage, message, customer_data)
            
            # Prepare context for LLM
            context = {
                'stage': current_stage,
                'customer_data': customer_data,
                'history': session_data.get('messages', [])
            }
            
            # Generate AI response
            ai_response = await llm_service.generate_response(message, context)
            
            # Check if customer is qualified
            qualified = self._check_qualification(customer_data, next_stage)
            
            # Create message record
            message_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'customer_message': message,
                'ai_response': ai_response,
                'stage': current_stage,
                'next_stage': next_stage,
                'extracted_info': extracted_info
            }
            
            # Update session data
            session_data['messages'].append(message_record)
            session_data['stage'] = next_stage
            session_data['customer_data'] = customer_data
            session_data['last_updated'] = datetime.utcnow().isoformat()
            
            # Save session
            db_service.save_conversation(session_id, session_data)
            
            # Prepare response
            result = {
                'session_id': session_id,
                'ai_response': ai_response,
                'current_stage': current_stage,
                'next_stage': next_stage,
                'customer_qualified': qualified,
                'extracted_info': extracted_info,
                'customer_summary': self._create_summary(customer_data),
                'recommended_action': 'send_application_link' if qualified else 'continue_conversation',
                'processing_time': datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Message processed successfully: {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Message processing failed: {e}")
            return {
                'session_id': session_id,
                'ai_response': "I apologize for the technical issue. Let me help you right away!",
                'current_stage': 'GREETING',
                'next_stage': 'GREETING',
                'customer_qualified': False,
                'error': str(e)
            }
    
    def _extract_info(self, message: str) -> Dict[str, Any]:
        """Extract customer information from message"""
        extracted = {}
        message_lower = message.lower()
        
        # Extract loan amount
        amount_patterns = [
            (r'(\d+)\s*lakh(?:s)?', lambda x: int(x) * 100000),
            (r'₹\s*(\d+(?:,\d+)*)', lambda x: int(x.replace(',', ''))),
            (r'(\d+)\s*thousand', lambda x: int(x) * 1000),
            (r'(\d{5,8})', lambda x: int(x))
        ]
        
        for pattern, converter in amount_patterns:
            match = re.search(pattern, message_lower)
            if match:
                try:
                    amount = converter(match.group(1))
                    if settings.MIN_LOAN <= amount <= settings.MAX_LOAN:
                        extracted['loan_amount'] = amount
                        break
                except ValueError:
                    continue
        
        # Extract purpose
        purposes = {
            'wedding': ['wedding', 'marriage', 'shaadi'],
            'business': ['business', 'startup', 'shop'],
            'home': ['home', 'house', 'property'],
            'education': ['education', 'study', 'college'],
            'medical': ['medical', 'hospital', 'treatment'],
            'personal': ['personal', 'emergency', 'urgent']
        }
        
        for purpose, keywords in purposes.items():
            if any(word in message_lower for word in keywords):
                extracted['purpose'] = purpose
                break
        
        # Extract income
        if any(word in message_lower for word in ['salary', 'income', 'earn']):
            income_patterns = [
                (r'(\d+)k\b', lambda x: int(x) * 1000),
                (r'(\d+)\s*thousand', lambda x: int(x) * 1000),
                (r'(\d{4,6})', lambda x: int(x))
            ]
            
            for pattern, converter in income_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    try:
                        income = converter(match.group(1))
                        if 15000 <= income <= 1000000:
                            extracted['income'] = income
                            break
                    except ValueError:
                        continue
        
        # Extract name
        name_patterns = [
            r'(?:i am|i\'m|my name is)\s+([a-zA-Z]+)',
            r'this is\s+([a-zA-Z]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                extracted['name'] = match.group(1).title()
                break
        
        return extracted
    
    def _determine_next_stage(self, current_stage: str, message: str, customer_data: Dict) -> str:
        """Determine next conversation stage"""
        message_lower = message.lower()
        
        if current_stage == "GREETING":
            if any(word in message_lower for word in ['loan', 'money', 'borrow']):
                return "NEEDS_ANALYSIS"
        
        elif current_stage == "NEEDS_ANALYSIS":
            if customer_data.get('loan_amount') and customer_data.get('purpose'):
                return "QUALIFICATION"
        
        elif current_stage == "QUALIFICATION":
            if customer_data.get('income'):
                return "PRESENTATION"
        
        elif current_stage == "PRESENTATION":
            if any(word in message_lower for word in ['yes', 'interested', 'okay', 'good']):
                return "CLOSING"
            elif any(word in message_lower for word in ['but', 'concern', 'expensive']):
                return "OBJECTION_HANDLING"
        
        elif current_stage == "OBJECTION_HANDLING":
            if any(word in message_lower for word in ['okay', 'fine', 'proceed']):
                return "CLOSING"
        
        return current_stage  # Stay in current stage
    
    def _check_qualification(self, customer_data: Dict, stage: str) -> bool:
        """Check if customer is qualified for loan"""
        if stage != "CLOSING":
            return False
        
        loan_amount = customer_data.get('loan_amount', 0)
        income = customer_data.get('income', 0)
        
        if loan_amount and income:
            # Check income ratio (loan should be <= 3x annual income)
            annual_income = income * 12
            return loan_amount <= (annual_income * settings.INCOME_RATIO)
        
        return False
    
    def _create_summary(self, customer_data: Dict) -> Dict[str, Any]:
        """Create customer data summary"""
        summary = {}
        
        if customer_data.get('name'):
            summary['name'] = customer_data['name']
        if customer_data.get('loan_amount'):
            summary['loan_amount'] = f"₹{customer_data['loan_amount']:,}"
        if customer_data.get('purpose'):
            summary['purpose'] = customer_data['purpose'].title()
        if customer_data.get('income'):
            summary['monthly_income'] = f"₹{customer_data['income']:,}"
            
            if customer_data.get('loan_amount'):
                annual_income = customer_data['income'] * 12
                ratio = customer_data['loan_amount'] / annual_income
                summary['income_ratio'] = f"{ratio:.1f}x"
                summary['eligible'] = ratio <= settings.INCOME_RATIO
        
        return summary

# Global instance
conversation_agent = ConversationAgent()
