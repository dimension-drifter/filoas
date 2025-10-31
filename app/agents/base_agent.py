# app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import logging
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.llm_service import llm_service
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.agent_id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.processing_count = 0
        
        logger.info(f"✅ Initialized agent: {self.name}")
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return response"""
        pass
    
    def log_processing(self, action: str, input_data: Dict[str, Any] = None):
        """Log agent processing"""
        self.processing_count += 1
        logger.info(f"[{self.name}] {action} - Processing #{self.processing_count}")
    
    async def save_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Save session data"""
        data['last_agent'] = self.name
        data['last_updated'] = datetime.utcnow().isoformat()
        return db_service.save_conversation(session_id, data)
    
    async def load_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data"""
        return db_service.load_conversation(session_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Agent health check"""
        return {
            "agent": self.name,
            "status": "healthy",
            "processing_count": self.processing_count,
            "created_at": self.created_at.isoformat()
        }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "processing_count": self.processing_count
        }
