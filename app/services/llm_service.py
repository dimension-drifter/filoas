# app/services/llm_service.py (UPDATE THE TOP)
import os
from dotenv import load_dotenv

# CRITICAL: Load .env file FIRST
load_dotenv()

from groq import Groq
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any
import logging
from config.settings import settings
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

class LLMService:
    """Groq LLM Service for Tezloan"""
    
    def __init__(self):
        self.groq_client = None
        self.llm = None
        self._setup_groq()
    
    def _setup_groq(self):
        """Initialize Groq LLM"""
        try:
            # Get API key directly from environment
            groq_api_key = os.getenv("GROQ_API_KEY")
            
            if not groq_api_key:
                raise ValueError(f"GROQ_API_KEY not found in environment. Current env vars: {list(os.environ.keys())[:5]}...")
            
            print(f"✅ Found Groq API key: {groq_api_key[:10]}...")
            
            # Direct Groq client
            self.groq_client = Groq(api_key=groq_api_key)
            
            # LangChain Groq LLM
            self.llm = ChatGroq(
                groq_api_key=groq_api_key,
                model_name="llama-3.1-8b-instant"
            )
            
            logger.info("✅ Groq LLM initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Groq initialization failed: {e}")
            raise
    
    def get_system_prompt(self) -> str:
        """Loan sales system prompt"""
        return """You are an expert loan sales assistant for Tezloan, India's AI-powered lending platform.

Your personality:
- Warm, friendly, and professional
- Empathetic to customer financial needs
- Confident about Tezloan's benefits
- Expert at handling objections

Your knowledge:
- Loans: ₹50K to ₹20L 
- Interest rates: Starting 10.5%
- Approval: 15-20 minutes
- 50,000+ happy customers

Conversation stages:
1. GREETING: Welcome warmly
2. NEEDS_ANALYSIS: Understand loan need
3. QUALIFICATION: Check eligibility  
4. PRESENTATION: Present loan offer
5. OBJECTION_HANDLING: Address concerns
6. CLOSING: Ready for application

Guidelines:
- Keep responses natural (50-80 words)
- Use customer's name if provided
- Show excitement for weddings/business
- Address price concerns with benefits
- Build trust with facts

Respond as a caring friend helping with finances."""

    async def generate_response(self, customer_message: str, context: Dict[str, Any]) -> str:
        """Generate AI response using Groq"""
        try:
            # Check cache first
            cache_key = f"response:{hash(customer_message + str(context.get('stage', '')))}"
            cached = db_service.cache_get(cache_key)
            if cached:
                logger.info("💾 Using cached response")
                return cached
            
            # Build prompt with context
            stage = context.get('stage', 'GREETING')
            history = context.get('history', [])
            customer_data = context.get('customer_data', {})
            
            context_info = []
            context_info.append(f"Stage: {stage}")
            
            if customer_data.get('name'):
                context_info.append(f"Customer: {customer_data['name']}")
            if customer_data.get('loan_amount'):
                context_info.append(f"Amount: ₹{customer_data['loan_amount']:,}")
            if customer_data.get('purpose'):
                context_info.append(f"Purpose: {customer_data['purpose']}")
            if customer_data.get('income'):
                context_info.append(f"Income: ₹{customer_data['income']:,}")
            
            context_str = " | ".join(context_info)
            
            # Create prompt
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", self.get_system_prompt()),
                ("human", f"[CONTEXT: {context_str}]\n\nCustomer says: {customer_message}")
            ])
            
            # Generate response
            chain = prompt_template | self.llm
            response = await chain.ainvoke({})
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Cache response
            db_service.cache_set(cache_key, response_text, ttl=1800)
            
            logger.info("🧠 Generated fresh AI response")
            return response_text
            
        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Let me help you in just a moment!"
    
    def health_check(self) -> Dict[str, Any]:
        """Check LLM health"""
        return {
            "groq_connected": self.llm is not None,
            "model": settings.GROQ_MODEL,
            "status": "healthy" if self.llm else "error"
        }

# Global instance
llm_service = LLMService()
