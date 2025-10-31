# app/api/document_endpoints.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import logging
from datetime import datetime
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.agents.kyc_agent import kyc_agent
from app.agents.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/upload")
async def upload_documents(
    session_id: str,
    files: List[UploadFile] = File(...)
):
    """Upload KYC documents"""
    try:
        logger.info(f"📄 Document upload for session: {session_id}")
        
        # Process uploaded files
        documents = {}
        for file in files:
            # In a real system, you'd save files and process them
            # For demo, we'll simulate document processing
            
            file_content = await file.read()
            
            # Determine document type based on filename
            filename_lower = file.filename.lower()
            
            if "pan" in filename_lower:
                doc_type = "pan_card"
            elif "aadhar" in filename_lower or "aadhaar" in filename_lower:
                doc_type = "aadhar_card"
            elif "salary" in filename_lower or "slip" in filename_lower:
                doc_type = "salary_slip"
            elif "bank" in filename_lower or "statement" in filename_lower:
                doc_type = "bank_statement"
            else:
                doc_type = "other_document"
            
            documents[doc_type] = {
                "filename": file.filename,
                "size": len(file_content),
                "upload_time": datetime.utcnow().isoformat(),
                "content_type": file.content_type
            }
        
        # Process through KYC agent
        kyc_input = {
            "customer_id": session_id,
            "documents": documents,
            "type": "document_upload"
        }
        
        kyc_result = await kyc_agent.process(kyc_input)
        
        return {
            "status": "success",
            "message": f"Processed {len(files)} documents successfully",
            "session_id": session_id,
            "uploaded_documents": list(documents.keys()),
            "verification_result": kyc_result,
            "next_step": "credit_assessment" if kyc_result["verification_status"] == "VERIFIED" else "upload_missing_docs"
        }
        
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")

@router.get("/status/{session_id}")
async def get_document_status(session_id: str):
    """Get document verification status"""
    try:
        # Get workflow status from orchestrator
        status = await orchestrator.get_workflow_status(session_id)
        
        return {
            "session_id": session_id,
            "document_status": "in_progress",  # Mock status
            "verification_progress": status.get("progress_percentage", 0),
            "required_documents": [
                {"type": "pan_card", "status": "pending", "description": "PAN Card"},
                {"type": "aadhar_card", "status": "pending", "description": "Aadhar Card"},
                {"type": "salary_slip", "status": "pending", "description": "Latest 3 Salary Slips"},
                {"type": "bank_statement", "status": "pending", "description": "6 Month Bank Statement"}
            ],
            "next_steps": status.get("next_recommended_action", "Upload pending documents")
        }
        
    except Exception as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document status")

@router.post("/verify")
async def verify_documents(session_id: str):
    """Manually trigger document verification"""
    try:
        # Trigger KYC verification through orchestrator
        input_data = {
            "session_id": session_id,
            "documents": {
                # Mock documents for demo
                "pan_card": {"status": "uploaded"},
                "aadhar_card": {"status": "uploaded"},
                "salary_slip": {"status": "uploaded"}
            }
        }
        
        result = await orchestrator.process_customer_request("kyc_verification", input_data)
        
        return {
            "status": "success",
            "message": "Document verification completed",
            "verification_result": result,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Document verification failed: {e}")
        raise HTTPException(status_code=500, detail="Document verification failed")
