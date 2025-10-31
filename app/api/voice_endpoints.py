# app/api/voice_endpoints.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import logging
from datetime import datetime, UTC
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.agents.conversation_agent import conversation_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

class VoiceMessage(BaseModel):
    session_id: str
    audio_data: str  # Base64 encoded audio
    language: str = "en"

class VoiceResponse(BaseModel):
    session_id: str
    text_response: str
    audio_response: str  # Base64 encoded audio response
    conversation_stage: str

@router.post("/process", response_model=VoiceResponse)
async def process_voice_message(voice_message: VoiceMessage):
    """Process voice message and return voice response"""
    try:
        logger.info(f"🎤 Voice message for session: {voice_message.session_id}")
        
        # In a real system, you'd:
        # 1. Convert audio to text using speech-to-text
        # 2. Process through conversation agent  
        # 3. Convert response to audio using text-to-speech
        
        # For demo, we'll simulate speech-to-text conversion
        transcribed_text = "I need a 5 lakh loan for my wedding next month"
        
        logger.info(f"🔄 Transcribed: {transcribed_text}")
        
        # Process through conversation agent
        result = await conversation_agent.process_message(
            voice_message.session_id,
            transcribed_text
        )
        
        # Simulate text-to-speech conversion
        audio_response = "base64_encoded_audio_response_here"
        
        return VoiceResponse(
            session_id=voice_message.session_id,
            text_response=result["ai_response"],
            audio_response=audio_response,
            conversation_stage=result["next_stage"]
        )
        
    except Exception as e:
        logger.error(f"Voice processing failed: {e}")
        raise HTTPException(status_code=500, detail="Voice processing failed")

@router.post("/upload-audio")
async def upload_audio_file(
    session_id: str,
    audio_file: UploadFile = File(...)
):
    """Upload audio file for processing"""
    try:
        logger.info(f"🎵 Audio file upload for session: {session_id}")
        
        # Read audio file
        audio_content = await audio_file.read()
        
        # Simulate speech-to-text processing
        transcribed_text = "Hello, I am interested in getting a personal loan"
        
        # Process through conversation agent
        result = await conversation_agent.process_message(session_id, transcribed_text)
        
        return {
            "status": "success",
            "message": "Audio processed successfully",
            "session_id": session_id,
            "transcribed_text": transcribed_text,
            "ai_response": result["ai_response"],
            "conversation_stage": result["next_stage"],
            "file_info": {
                "filename": audio_file.filename,
                "size": len(audio_content),
                "content_type": audio_file.content_type
            }
        }
        
    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail="Audio upload failed")

@router.get("/tts/{session_id}")
async def text_to_speech(session_id: str, text: str):
    """Convert text to speech"""
    try:
        # In a real system, use TTS service like AWS Polly or Google TTS
        # For demo, we'll return mock audio data
        
        mock_audio_data = f"base64_encoded_audio_for_{len(text)}_characters"
        
        return {
            "status": "success",
            "session_id": session_id,
            "input_text": text,
            "audio_data": mock_audio_data,
            "audio_format": "mp3",
            "duration_seconds": len(text) * 0.1  # Mock duration
        }
        
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail="Text-to-speech conversion failed")

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "supported_languages": [
            {"code": "en", "name": "English"},
            {"code": "hi", "name": "Hindi"}
        ],
        "default_language": "en"
    }
