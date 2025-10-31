# app/agents/transcript_agent.py
from .base_agent import BaseAgent
from typing import Dict, Any, List
import logging
import re
from datetime import datetime
import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class TranscriptAgent(BaseAgent):
    """Process voice conversation transcripts and extract loan information"""
    
    def __init__(self):
        super().__init__(
            name="TranscriptAgent",
            description="Processes conversation transcripts and extracts structured loan data"
        )
        
        self.extraction_categories = {
            "personal_info": [
                "name", "age", "phone", "email", "address", "marital_status"
            ],
            "employment_info": [
                "employer", "designation", "experience", "monthly_income", "employment_type"
            ],
            "loan_details": [
                "loan_amount", "loan_purpose", "loan_tenure", "urgency", "existing_loans"
            ],
            "financial_info": [
                "bank_account", "monthly_expenses", "other_income", "assets", "liabilities"
            ],
            "preferences": [
                "preferred_emi", "preferred_tenure", "concerns", "questions"
            ]
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcript and extract structured information"""
        self.log_processing("transcript_processing_start", input_data)
        
        try:
            session_id = input_data.get("session_id", "")
            transcript = input_data.get("transcript", "")
            conversation_metadata = input_data.get("metadata", {})
            
            # Validate input
            if not transcript.strip():
                raise ValueError("Empty transcript provided")
            
            # Clean and preprocess transcript
            cleaned_transcript = self._clean_transcript(transcript)
            
            # Extract structured information using AI
            extracted_data = await self._extract_information_with_ai(cleaned_transcript)
            
            # Parse conversation flow
            conversation_analysis = self._analyze_conversation_flow(cleaned_transcript)
            
            # Generate conversation summary
            summary = await self._generate_conversation_summary(cleaned_transcript, extracted_data)
            
            # Create structured report data
            report_data = self._create_report_structure(
                extracted_data, conversation_analysis, summary, conversation_metadata
            )
            
            result = {
                "agent": self.name,
                "session_id": session_id,
                "transcript_processed": True,
                "extracted_data": extracted_data,
                "conversation_analysis": conversation_analysis,
                "summary": summary,
                "report_data": report_data,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "transcript_stats": {
                    "original_length": len(transcript),
                    "cleaned_length": len(cleaned_transcript),
                    "word_count": len(cleaned_transcript.split()),
                    "conversation_turns": len(cleaned_transcript.split('\n'))
                }
            }
            
            self.log_processing("transcript_processing_complete", result)
            return result
            
        except Exception as e:
            logger.error(f"Transcript processing failed: {e}")
            return {
                "agent": self.name,
                "session_id": session_id,
                "error": str(e),
                "transcript_processed": False,
                "message": "Failed to process transcript. Please try again."
            }
    
    def _clean_transcript(self, transcript: str) -> str:
        """Clean and normalize transcript text"""
        # Remove timestamps if present
        cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', transcript)
        
        # Remove speaker labels like "Agent:", "Customer:", "User:"
        cleaned = re.sub(r'^(Agent|Customer|User|Assistant|Human):\s*', '', cleaned, flags=re.MULTILINE)
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        
        # Remove filler words for better analysis
        filler_words = ['um', 'uh', 'like', 'you know', 'basically', 'actually']
        for word in filler_words:
            cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    async def _extract_information_with_ai(self, transcript: str) -> Dict[str, Any]:
        """Use AI to extract structured information from transcript"""
        extraction_prompt = f"""
        You are an expert at extracting loan application information from conversation transcripts.
        
        Extract the following information from this conversation transcript:
        
        TRANSCRIPT:
        {transcript}
        
        Extract and return ONLY the following information in JSON format:
        
        {{
            "personal_info": {{
                "name": "extracted name or null",
                "age": "extracted age or null", 
                "phone": "phone number or null",
                "email": "email address or null",
                "address": "address or null",
                "marital_status": "married/single/null"
            }},
            "employment_info": {{
                "employer": "company name or null",
                "designation": "job title or null", 
                "monthly_income": "income amount as number or null",
                "employment_type": "permanent/contract/null",
                "experience": "years of experience or null"
            }},
            "loan_details": {{
                "loan_amount": "requested amount as number or null",
                "loan_purpose": "wedding/business/home/personal/medical/education or null",
                "loan_tenure": "preferred years or null",
                "urgency": "urgent/normal/flexible or null"
            }},
            "financial_info": {{
                "monthly_expenses": "expense amount or null",
                "existing_loans": "existing loan details or null",
                "other_income": "additional income or null"
            }},
            "preferences": {{
                "preferred_emi": "preferred EMI amount or null",
                "concerns": "customer concerns or null",
                "questions": "customer questions or null"
            }}
        }}
        
        IMPORTANT: 
        - Return only valid JSON
        - Use null for missing information
        - Convert amounts to numbers where possible
        - Keep text responses concise
        """
        
        try:
            # Generate extraction using AI
            extraction_result = await llm_service.generate_response(extraction_prompt, {
                "stage": "data_extraction",
                "task": "transcript_parsing"
            })
            
            # Parse JSON response
            extracted_data = json.loads(extraction_result.strip())
            return extracted_data
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"AI extraction failed: {e}")
            # Fallback to manual extraction
            return self._manual_extraction_fallback(transcript)
    
    def _manual_extraction_fallback(self, transcript: str) -> Dict[str, Any]:
        """Manual extraction as fallback when AI parsing fails"""
        transcript_lower = transcript.lower()
        extracted = {
            "personal_info": {},
            "employment_info": {},
            "loan_details": {},
            "financial_info": {},
            "preferences": {}
        }
        
        # Extract name patterns
        name_patterns = [
            r'(?:my name is|i am|i\'m|call me)\s+([a-zA-Z\s]+)',
            r'this is\s+([a-zA-Z\s]+)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, transcript_lower)
            if match:
                extracted["personal_info"]["name"] = match.group(1).strip().title()
                break
        
        # Extract loan amount
        amount_patterns = [
            (r'(\d+)\s*lakh(?:s)?', lambda x: int(x) * 100000),
            (r'(\d+)\s*crore(?:s)?', lambda x: int(x) * 10000000),
            (r'₹\s*(\d+(?:,\d+)*)', lambda x: int(x.replace(',', ''))),
            (r'(\d{5,8})', lambda x: int(x))
        ]
        
        for pattern, converter in amount_patterns:
            match = re.search(pattern, transcript_lower)
            if match:
                try:
                    extracted["loan_details"]["loan_amount"] = converter(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Extract purpose
        purpose_keywords = {
            'wedding': ['wedding', 'marriage', 'shaadi'],
            'business': ['business', 'startup', 'shop'],
            'home': ['home', 'house', 'property'],
            'education': ['education', 'study', 'college'],
            'medical': ['medical', 'hospital', 'treatment'],
            'personal': ['personal', 'emergency', 'urgent']
        }
        
        for purpose, keywords in purpose_keywords.items():
            if any(word in transcript_lower for word in keywords):
                extracted["loan_details"]["loan_purpose"] = purpose
                break
        
        # Extract income
        if any(word in transcript_lower for word in ['salary', 'income', 'earn']):
            income_patterns = [
                (r'(\d+)k\b', lambda x: int(x) * 1000),
                (r'(\d+)\s*thousand', lambda x: int(x) * 1000),
                (r'(\d{4,6})', lambda x: int(x))
            ]
            
            for pattern, converter in income_patterns:
                match = re.search(pattern, transcript_lower)
                if match:
                    try:
                        income = converter(match.group(1))
                        if 15000 <= income <= 1000000:
                            extracted["employment_info"]["monthly_income"] = income
                            break
                    except ValueError:
                        continue
        
        return extracted
    
    def _analyze_conversation_flow(self, transcript: str) -> Dict[str, Any]:
        """Analyze conversation flow and identify stages"""
        lines = transcript.split('\n')
        
        analysis = {
            "conversation_stages": [],
            "customer_sentiment": "neutral",
            "agent_effectiveness": "good",
            "key_moments": [],
            "objections_raised": [],
            "information_gaps": []
        }
        
        # Identify conversation stages based on content
        stage_keywords = {
            "greeting": ["hello", "hi", "good morning", "welcome"],
            "needs_analysis": ["need", "looking for", "want", "require"],
            "qualification": ["income", "salary", "work", "employed"],
            "presentation": ["offer", "rate", "emi", "interest"],
            "objection_handling": ["but", "however", "concern", "worried"],
            "closing": ["proceed", "interested", "yes", "okay"]
        }
        
        current_stage = "greeting"
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            for stage, keywords in stage_keywords.items():
                if any(keyword in line_lower for keyword in keywords):
                    if stage != current_stage:
                        analysis["conversation_stages"].append({
                            "stage": stage,
                            "line_number": i + 1,
                            "content": line[:100] + "..." if len(line) > 100 else line
                        })
                        current_stage = stage
                    break
        
        # Analyze sentiment
        positive_words = ["great", "excellent", "perfect", "good", "yes", "interested"]
        negative_words = ["no", "but", "concern", "worried", "problem", "issue"]
        
        positive_count = sum(1 for word in positive_words if word in transcript.lower())
        negative_count = sum(1 for word in negative_words if word in transcript.lower())
        
        if positive_count > negative_count:
            analysis["customer_sentiment"] = "positive"
        elif negative_count > positive_count:
            analysis["customer_sentiment"] = "negative"
        else:
            analysis["customer_sentiment"] = "neutral"
        
        return analysis
    
    async def _generate_conversation_summary(self, transcript: str, extracted_data: Dict[str, Any]) -> str:
        """Generate AI-powered conversation summary"""
        summary_prompt = f"""
        Create a professional summary of this loan conversation transcript:
        
        TRANSCRIPT: {transcript[:2000]}...
        
        EXTRACTED DATA: {json.dumps(extracted_data, indent=2)}
        
        Write a concise 3-paragraph summary covering:
        1. Customer profile and loan requirements
        2. Key conversation highlights and decisions
        3. Next steps and recommendations
        
        Keep it professional and factual.
        """
        
        try:
            summary = await llm_service.generate_response(summary_prompt, {
                "stage": "summary_generation",
                "task": "conversation_summary"
            })
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return self._generate_basic_summary(extracted_data)
    
    def _generate_basic_summary(self, extracted_data: Dict[str, Any]) -> str:
        """Generate basic summary as fallback"""
        personal = extracted_data.get("personal_info", {})
        employment = extracted_data.get("employment_info", {})
        loan = extracted_data.get("loan_details", {})
        
        name = personal.get("name", "Customer")
        amount = loan.get("loan_amount", "Not specified")
        purpose = loan.get("loan_purpose", "personal use")
        income = employment.get("monthly_income", "Not provided")
        
        summary = f"""
        Conversation Summary:
        
        Customer {name} has inquired about a personal loan of ₹{amount:,} for {purpose}. 
        The customer's monthly income is ₹{income:,}. Based on the conversation, 
        the customer appears interested in proceeding with the loan application.
        
        Next steps include document verification and credit assessment to finalize 
        the loan approval process.
        """
        
        return summary.strip()
    
    def _create_report_structure(self, extracted_data: Dict[str, Any], 
                                conversation_analysis: Dict[str, Any],
                                summary: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured data for report generation"""
        return {
            "report_type": "loan_conversation_analysis",
            "generated_at": datetime.utcnow().isoformat(),
            "session_metadata": metadata,
            "customer_profile": {
                **extracted_data.get("personal_info", {}),
                **extracted_data.get("employment_info", {})
            },
            "loan_requirements": extracted_data.get("loan_details", {}),
            "financial_profile": extracted_data.get("financial_info", {}),
            "conversation_insights": conversation_analysis,
            "executive_summary": summary,
            "recommendations": self._generate_recommendations(extracted_data),
            "next_actions": self._determine_next_actions(extracted_data, conversation_analysis)
        }
    
    def _generate_recommendations(self, extracted_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on extracted data"""
        recommendations = []
        
        loan_amount = extracted_data.get("loan_details", {}).get("loan_amount", 0)
        monthly_income = extracted_data.get("employment_info", {}).get("monthly_income", 0)
        
        if loan_amount and monthly_income:
            annual_income = monthly_income * 12
            loan_to_income_ratio = loan_amount / annual_income
            
            if loan_to_income_ratio <= 3:
                recommendations.append("Customer qualifies for the requested loan amount based on income criteria")
            else:
                recommendations.append("Consider reducing loan amount or extending tenure to improve eligibility")
        
        purpose = extracted_data.get("loan_details", {}).get("loan_purpose")
        if purpose == "wedding":
            recommendations.append("Offer special wedding loan rates and flexible EMI options")
        elif purpose == "business":
            recommendations.append("Consider business loan products with longer tenure")
        
        return recommendations
    
    def _determine_next_actions(self, extracted_data: Dict[str, Any], 
                              conversation_analysis: Dict[str, Any]) -> List[str]:
        """Determine next actions based on conversation analysis"""
        actions = []
        
        # Check what information is still needed
        personal = extracted_data.get("personal_info", {})
        employment = extracted_data.get("employment_info", {})
        loan = extracted_data.get("loan_details", {})
        
        if not personal.get("name"):
            actions.append("Collect customer name and contact details")
        
        if not loan.get("loan_amount"):
            actions.append("Clarify exact loan amount required")
        
        if not employment.get("monthly_income"):
            actions.append("Obtain monthly income verification")
        
        if conversation_analysis.get("customer_sentiment") == "positive":
            actions.append("Proceed with KYC document collection")
            actions.append("Prepare loan application form")
        elif conversation_analysis.get("customer_sentiment") == "negative":
            actions.append("Address customer concerns and objections")
            actions.append("Schedule follow-up call")
        
        actions.append("Send loan pre-approval form link")
        actions.append("Schedule document verification appointment")
        
        return actions

# Global instance
transcript_agent = TranscriptAgent()
