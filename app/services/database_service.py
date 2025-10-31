from pymongo import MongoClient
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseService:
    """Simple MongoDB Atlas + In-Memory Cache Service"""
    
    def __init__(self):
        self.mongo_client = None
        self.database = None
        self.conversations = None
        
        # In-memory cache (Redis replacement)
        self._cache = {}
        
        self._setup_mongodb()
    
    def _setup_mongodb(self):
        """Setup MongoDB Atlas connection"""
        try:
            if settings.MONGODB_URL:
                self.mongo_client = MongoClient(
                    settings.MONGODB_URL,
                    serverSelectionTimeoutMS=5000
                )
                # Test connection
                self.mongo_client.admin.command('ping')
                
                self.database = self.mongo_client[settings.DATABASE_NAME]
                self.conversations = self.database.conversations
                
                logger.info("✅ MongoDB Atlas connected successfully")
            else:
                logger.warning("⚠️ MongoDB URL not provided, using memory only")
                
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            logger.info("📝 Continuing with memory storage only")
    
    def save_conversation(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Save conversation to MongoDB or memory"""
        try:
            # Add metadata
            data['session_id'] = session_id
            data['updated_at'] = datetime.now(timezone.utc)  # <-- FIX 1
            
            # Try MongoDB first
            if self.conversations is not None:  # <-- FIX 2
                self.conversations.replace_one(
                    {'session_id': session_id},
                    data,
                    upsert=True
                )
                logger.debug(f"💾 Saved to MongoDB: {session_id}")
                return True
            
            # Fallback to memory
            self._cache[f"session:{session_id}"] = data
            logger.debug(f"💾 Saved to memory: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")
            # Emergency fallback to memory
            self._cache[f"session:{session_id}"] = data
            return True
    
    def load_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load conversation from MongoDB or memory"""
        try:
            # Try MongoDB first
            if self.conversations is not None:  # <-- FIX 3
                doc = self.conversations.find_one({'session_id': session_id})
                if doc:
                    doc.pop('_id', None)  # Remove MongoDB ID
                    logger.debug(f"📖 Loaded from MongoDB: {session_id}")
                    return doc
            
            # Try memory cache
            data = self._cache.get(f"session:{session_id}")
            if data:
                logger.debug(f"📖 Loaded from memory: {session_id}")
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Load failed: {e}")
            return self._cache.get(f"session:{session_id}")
    
    def cache_set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set cache value (in-memory)"""
        try:
            self._cache[key] = {
                'value': value,
                'expires_at': datetime.now(timezone.utc).timestamp() + ttl  # <-- FIX 4
            }
            return True
        except Exception as e:
            logger.error(f"❌ Cache set failed: {e}")
            return False
    
    def cache_get(self, key: str) -> Optional[str]:
        """Get cache value (in-memory)"""
        try:
            cached = self._cache.get(key)
            if not cached:
                return None
            
            # Check expiration
            if datetime.now(timezone.utc).timestamp() > cached['expires_at']:  # <-- FIX 5
                del self._cache[key]
                return None
            
            return cached['value']
            
        except Exception as e:
            logger.error(f"❌ Cache get failed: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        # This was already correct in your code, but confirmed
        mongodb_status = "connected" if self.conversations is not None else "disconnected"
        cache_status = "active"
        
        return {
            "mongodb": mongodb_status,
            "cache": cache_status,
            "overall": "healthy"
        }

# Global instance
db_service = DatabaseService()
