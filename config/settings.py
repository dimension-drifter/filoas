# config/settings.py (UPDATE THE TOP)
import os
from typing import Dict, Any
from dotenv import load_dotenv

# CRITICAL: Load .env file FIRST THING
load_dotenv()
print(f"📝 .env loaded. GROQ_API_KEY present: {bool(os.getenv('GROQ_API_KEY'))}")

class Settings:
    """Tezloan Settings - Simple & Working"""
    
    # Project
    PROJECT_NAME = "Tezloan"
    VERSION = "1.0.0"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # LLM - Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = "llama-3.1-8b-instant"
    
    # Database - MongoDB Atlas (optional)
    MONGODB_URL = os.getenv("MONGODB_ATLAS_URL", "")
    DATABASE_NAME = "loan_genie"
    
    # Loan Business Logic
    MIN_LOAN = 50000
    MAX_LOAN = 2000000
    BASE_RATE = 10.5
    INCOME_RATIO = 3.0
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Quick validation"""
        issues = []
        
        if not cls.GROQ_API_KEY:
            issues.append("GROQ_API_KEY missing - get from console.groq.com")
            issues.append(f"Current environment has these vars: {list(os.environ.keys())[:10]}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

# Global instance
settings = Settings()
