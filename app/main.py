
import sys
import os
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
import json
import uuid


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


try:
    from config.settings import settings
    from app.agents.conversation_agent import conversation_agent
    from app.agents.kyc_agent import kyc_agent
    from app.agents.credit_agent import credit_agent
    from app.agents.orchestrator import orchestrator
    from app.agents.transcript_agent import transcript_agent
    from app.agents.document_analyzer import document_analyzer
    from app.services.database_service import db_service
    from app.services.llm_service import llm_service
    from app.services.report_generator import report_generator
    from app.services.communication_service import communication_service
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}")
    raise


app = FastAPI(
    title="Tezloan API",
    description="Complete AI-powered loan conversation and processing system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConversationRequest(BaseModel):
    session_id: str
    message: str
    customer_phone: Optional[str] = None

class ConversationResponse(BaseModel):
    session_id: str
    ai_response: str
    current_stage: str
    next_stage: str
    customer_qualified: bool
    customer_summary: dict
    recommended_action: str

class TranscriptRequest(BaseModel):
    session_id: str
    transcript: str
    metadata: Optional[Dict[str, Any]] = {}

class DocumentRequest(BaseModel):
    session_id: str
    documents: Dict[str, Any]

class ReportRequest(BaseModel):
    session_id: str
    transcript_data: Dict[str, Any]
    document_data: Dict[str, Any]
    additional_data: Optional[Dict[str, Any]] = {}

class CommunicationRequest(BaseModel):
    session_id: str
    customer_data: Dict[str, Any]
    report_path: Optional[str] = None

class CompleteWorkflowRequest(BaseModel):
    session_id: Optional[str] = None
    transcript: str
    documents: Dict[str, Any]
    customer_contact: Dict[str, Any]


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Tezloan API",
        "version": "1.0.0",
        "status": "running",
        "description": "AI-powered loan conversation and processing system",
        "features": [
            "Multi-agent conversation processing",
            "Document analysis and verification",
            "Credit assessment and scoring",
            "Report generation and communication",
            "Complete loan application workflow"
        ],
        "endpoints": {
            "health": "/health",
            "conversation": "/api/conversation",
            "transcript_processing": "/api/process-transcript",
            "document_analysis": "/api/analyze-documents",
            "report_generation": "/api/generate-report",
            "communication": "/api/generate-communication-package",
            "complete_workflow": "/api/complete-workflow-no-email"
        },
        "timestamp": datetime.utcnow().isoformat(),
        "powered_by": "Tezloan AI • Groq • LangChain"
    }

@app.get("/health")
async def health_check():
    """System health check"""
    try:
       
        db_health = db_service.health_check()
        llm_health = llm_service.health_check()
        communication_stats = communication_service.get_communication_analytics()
        
        
        overall_status = "healthy"
        if not llm_health.get("groq_connected", False):
            overall_status = "degraded"
        
     
        config_validation = settings.validate()
        
        health_response = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.ENVIRONMENT,
            "version": settings.VERSION,
            "services": {
                "database": {
                    "status": db_health["overall"],
                    "details": db_health
                },
                "llm": {
                    "status": llm_health["status"],
                    "model": llm_health.get("model", "unknown"),
                    "groq_connected": llm_health.get("groq_connected", False)
                },
                "communication": {
                    "status": "healthy",
                    "stats": communication_stats["summary"]
                }
            },
            "configuration": {
                "valid": config_validation["valid"],
                "issues": config_validation.get("issues", [])
            },
            "system_info": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": sys.platform,
                "project_root": str(project_root)
            }
        }
        
        return health_response
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )



@app.post("/api/conversation", response_model=ConversationResponse)
async def process_conversation(request: ConversationRequest):
    """Main conversation processing endpoint"""
    try:
        logger.info(f"🎯 New conversation: {request.session_id}")
        
       
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Empty message")
        
        if not request.session_id.strip():
            raise HTTPException(status_code=400, detail="Empty session_id")
        
       
        result = await conversation_agent.process_message(
            session_id=request.session_id,
            message=request.message
        )
        
      
        if 'error' in result:
            logger.error(f"Agent error: {result['error']}")
            raise HTTPException(status_code=500, detail="Processing failed")
        
        
        return ConversationResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Conversation processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session data"""
    try:
        session_data = db_service.load_conversation(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
       
        return {
            "session_id": session_data.get("session_id"),
            "stage": session_data.get("stage"),
            "customer_data": session_data.get("customer_data", {}),
            "message_count": len(session_data.get("messages", [])),
            "created_at": session_data.get("created_at"),
            "last_updated": session_data.get("last_updated"),
            "processing_summary": {
                "total_turns": len(session_data.get("messages", [])),
                "current_stage": session_data.get("stage"),
                "qualified": session_data.get("stage") in ["PRESENTATION", "CLOSING"]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process-transcript")
async def process_transcript(request: TranscriptRequest):
    """Process voice conversation transcript from Deepam's voice assistant"""
    try:
        logger.info(f"📝 Processing transcript for session: {request.session_id}")
       
        if not request.transcript.strip():
            raise HTTPException(status_code=400, detail="Empty transcript provided")
        
        result = await transcript_agent.process({
            "session_id": request.session_id,
            "transcript": request.transcript,
            "metadata": request.metadata
        })
        
       
        result["processing_summary"] = {
            "transcript_length": len(request.transcript),
            "word_count": len(request.transcript.split()),
            "processing_timestamp": datetime.utcnow().isoformat(),
            "extracted_entities": len(result.get("extracted_data", {})),
            "conversation_stages_identified": len(result.get("conversation_analysis", {}).get("conversation_stages", []))
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcript processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/analyze-documents")
async def analyze_documents(request: DocumentRequest):
    """Analyze uploaded KYC documents (PAN, Aadhar, Salary Slips)"""
    try:
        logger.info(f"📄 Analyzing documents for session: {request.session_id}")
        
        
        if not request.documents:
            raise HTTPException(status_code=400, detail="No documents provided")
        
        result = await document_analyzer.process({
            "session_id": request.session_id,
            "documents": request.documents
        })
     
        result["processing_summary"] = {
            "documents_count": len(request.documents),
            "documents_analyzed": list(request.documents.keys()),
            "verification_score": result.get("verification_score", 0),
            "overall_status": result.get("overall_status", "unknown"),
            "processing_timestamp": datetime.utcnow().isoformat()
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/upload")
async def upload_documents(
    session_id: str,
    files: List[UploadFile] = File(...)
):
    """Upload multiple documents for KYC verification"""
    try:
        logger.info(f"📤 Document upload for session: {session_id}, files: {len(files)}")
        
        
        documents = {}
        for file in files:
            
            file_content = await file.read()
            
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
                doc_type = f"document_{len(documents) + 1}"
            
            documents[doc_type] = {
                "filename": file.filename,
                "size": len(file_content),
                "upload_time": datetime.utcnow().isoformat(),
                "content_type": file.content_type,
                "status": "uploaded"
            }
       
        kyc_result = await kyc_agent.process({
            "customer_id": session_id,
            "documents": documents,
            "type": "document_upload"
        })
        
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


@app.post("/api/generate-report")
async def generate_comprehensive_report(request: ReportRequest):
    """Generate comprehensive PDF report from transcript and document analysis"""
    try:
        logger.info(f"📊 Generating report for session: {request.session_id}")
        
        
        if not request.transcript_data and not request.document_data:
            raise HTTPException(status_code=400, detail="Either transcript_data or document_data must be provided")
      
        report_path = report_generator.generate_comprehensive_report(
            request.session_id,
            request.transcript_data,
            request.document_data,
            request.additional_data
        )
        
        download_link = communication_service.generate_report_download_link(request.session_id, report_path)
        
        
        file_size = os.path.getsize(report_path) if os.path.exists(report_path) else 0
        
        return {
            "status": "success",
            "report_generated": True,
            "report_path": report_path,
            "download_link": download_link,
            "session_id": request.session_id,
            "file_info": {
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "generated_at": datetime.utcnow().isoformat()
            },
            "expires_at": (datetime.utcnow().timestamp() + 7*24*3600)  # 7 days from now
        }
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/report/{download_token}")
async def download_report(download_token: str):
    """Download report using secure token"""
    try:
       
        validation = communication_service.validate_download_token(download_token)
        
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["error"])
        
        report_path = validation["report_path"]
        
       
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report file not found")
        
        return FileResponse(
            report_path,
            media_type="application/pdf",
            filename=f"Tezloan_report_{validation['session_id']}.pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Tezloan_report_{validation['session_id']}.pdf",
                "X-Downloads-Remaining": str(validation["downloads_remaining"])
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-communication-package")
async def generate_communication_package(request: CommunicationRequest):
    """Generate complete communication package without email dependency"""
    try:
        logger.info(f"📱 Generating communication package for session: {request.session_id}")
      
        package = communication_service.generate_multi_channel_response(
            request.session_id,
            request.customer_data,
            request.report_path
        )
        
        return package
        
    except Exception as e:
        logger.error(f"Communication package generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/communication-templates/{session_id}")
async def get_communication_templates(session_id: str):
    """Get ready-to-use communication templates for manual sending"""
    try:
        
        session_data = db_service.load_conversation(session_id)
        
        if session_data:
            customer_data = session_data.get("customer_data", {})
        else:
            
            customer_data = {
                "personal_info": {"name": "Valued Customer"},
                "loan_details": {"loan_amount": 500000, "loan_purpose": "personal"}
            }
        
       
        templates = communication_service.generate_multi_channel_response(
            session_id, customer_data
        )
        
        return templates
        
    except Exception as e:
        logger.error(f"Template generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/qr-code")
async def generate_qr_code_api(url: str, label: str = "Scan to Access"):
    """Generate QR code for any URL"""
    try:
        qr_code_data = communication_service.generate_qr_code(url, label)
        
        if not qr_code_data:
            raise HTTPException(status_code=500, detail="QR code generation failed")
        
        return {
            "status": "success",
            "qr_code": qr_code_data,
            "url": url,
            "label": label,
            "format": "base64_png",
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"QR code generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/communication-analytics")
async def get_communication_analytics():
    """Get communication analytics dashboard"""
    try:
        analytics = communication_service.get_communication_analytics()
        return {
            "status": "success",
            "analytics": analytics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analytics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orchestrator/process")
async def orchestrator_process(request_data: dict):
    """Process request through agent orchestrator"""
    try:
        request_type = request_data.get("type", "conversation")
        result = await orchestrator.process_customer_request(request_type, request_data)
        return result
    except Exception as e:
        logger.error(f"Orchestrator processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orchestrator/status/{session_id}")
async def get_workflow_status(session_id: str):
    """Get workflow status from orchestrator"""
    try:
        status = await orchestrator.get_workflow_status(session_id)
        return status
    except Exception as e:
        logger.error(f"Workflow status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/complete-journey")
async def complete_loan_journey(request_data: dict):
    """Process complete loan journey through orchestrator"""
    try:
        result = await orchestrator.process_customer_request("complete_loan_journey", request_data)
        return result
    except Exception as e:
        logger.error(f"Complete journey processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/complete-workflow-no-email")
async def complete_deepam_workflow_no_email(request: CompleteWorkflowRequest):
    """Complete workflow: Transcript + Documents → Report → Communication (NO EMAIL)"""
    try:
       
        session_id = request.session_id or f"deepam_session_{int(datetime.utcnow().timestamp())}"
        
        logger.info(f"🚀 Starting complete workflow for session: {session_id}")
        
        results = {
            "session_id": session_id,
            "workflow_steps": [],
            "processing_started": datetime.utcnow().isoformat()
        }
        
    
        transcript_result = None
        if request.transcript.strip():
            logger.info("📝 Step 1: Processing transcript...")
            transcript_result = await transcript_agent.process({
                "session_id": session_id,
                "transcript": request.transcript,
                "metadata": {"source": "deepam_voice_assistant", "customer_contact": request.customer_contact}
            })
            results["transcript_analysis"] = transcript_result
            results["workflow_steps"].append("transcript_processed")
            logger.info("✅ Transcript processing completed")
        
        
        document_result = None
        if request.documents:
            logger.info("📄 Step 2: Analyzing documents...")
            document_result = await document_analyzer.process({
                "session_id": session_id,
                "documents": request.documents
            })
            results["document_analysis"] = document_result
            results["workflow_steps"].append("documents_analyzed")
            logger.info("✅ Document analysis completed")
        
        
        report_path = None
        if transcript_result or document_result:
            logger.info("📊 Step 3: Generating comprehensive report...")
            report_path = report_generator.generate_comprehensive_report(
                session_id,
                transcript_result or {},
                document_result or {}
            )
            
            
            download_link = communication_service.generate_report_download_link(session_id, report_path)
            
            results["report"] = {
                "path": report_path,
                "download_link": download_link,
                "file_size": os.path.getsize(report_path) if os.path.exists(report_path) else 0
            }
            results["workflow_steps"].append("report_generated")
            logger.info("✅ Report generation completed")
        
        
        logger.info("📱 Step 4: Generating communication package...")
        
        customer_data = {}
        if transcript_result:
            customer_data = transcript_result.get("extracted_data", {})
        
        if request.customer_contact:
            if "personal_info" not in customer_data:
                customer_data["personal_info"] = {}
            customer_data["personal_info"].update(request.customer_contact)
        
        communication_package = communication_service.generate_multi_channel_response(
            session_id, customer_data, report_path
        )
        
        results["communication_package"] = communication_package
        results["workflow_steps"].append("communication_package_generated")
        logger.info("✅ Communication package generated")
        
        results["workflow_completed"] = True
        results["processing_completed"] = datetime.utcnow().isoformat()
        results["ready_to_share"] = True
        results["summary"] = {
            "customer_name": customer_data.get("personal_info", {}).get("name", "Customer"),
            "loan_amount": customer_data.get("loan_details", {}).get("loan_amount"),
            "loan_purpose": customer_data.get("loan_details", {}).get("loan_purpose"),
            "documents_analyzed": len(request.documents) if request.documents else 0,
            "transcript_processed": bool(request.transcript.strip()),
            "report_generated": bool(report_path),
            "communication_ready": bool(communication_package.get("status") == "success")
        }
        
        logger.info(f"🎉 Complete workflow finished for session: {session_id}")
        
        return {
            "status": "success",
            "message": "Complete workflow executed successfully - Ready for client communication",
            **results
        }
        
    except Exception as e:
        logger.error(f"Complete workflow failed: {e}")
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Workflow processing failed",
            "session_id": session_id if 'session_id' in locals() else None,
            "failed_at": datetime.utcnow().isoformat()
        })


@app.get("/api/config")
async def get_public_config():
    """Get public configuration information"""
    validation = settings.validate()
    
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "api_info": {
            "host": settings.API_HOST,
            "port": settings.API_PORT
        },
        "loan_limits": {
            "min_amount": settings.MIN_LOAN,
            "max_amount": settings.MAX_LOAN,
            "base_rate": settings.BASE_RATE,
            "income_ratio": settings.INCOME_RATIO
        },
        "llm_info": {
            "model": settings.GROQ_MODEL,
            "provider": "Groq"
        },
        "configuration_status": {
            "valid": validation["valid"],
            "issues_count": len(validation.get("issues", []))
        },
        "features": {
            "conversation_processing": True,
            "transcript_analysis": True,
            "document_verification": True,
            "report_generation": True,
            "multi_channel_communication": True,
            "email_free_operation": True
        }
    }

@app.get("/api/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        db_stats = db_service.health_check()
        comm_stats = communication_service.get_communication_analytics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "sessions_stored": db_stats.get("sessions_count", 0),
                "status": db_stats.get("overall", "unknown")
            },
            "communication": comm_stats,
            "system": {
                "uptime": "N/A",  # Would implement proper uptime tracking
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT
            }
        }
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint was not found",
            "available_endpoints": {
                "health": "/health",
                "docs": "/docs",
                "conversation": "/api/conversation",
                "complete_workflow": "/api/complete-workflow-no-email"
            }
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting Tezloan API Server...")
    logger.info(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔖 Version: {settings.VERSION}")
    
    validation = settings.validate()
    if not validation["valid"]:
        logger.error("❌ Invalid configuration:")
        for issue in validation["issues"]:
            logger.error(f"   - {issue}")
        logger.warning("⚠️ Server starting with configuration issues")
    else:
        logger.info("✅ Configuration validated successfully")
    
    try:
        db_health = db_service.health_check()
        logger.info(f"✅ Database service: {db_health['overall']}")
        
        llm_health = llm_service.health_check()
        logger.info(f"✅ LLM service: {llm_health['status']}")
        
    except Exception as e:
        logger.error(f"❌ Service initialization warning: {e}")
    
    logger.info("🎉 Tezloan API Server is ready!")
    logger.info(f"📊 API Documentation: http://localhost:{settings.API_PORT}/docs")
    logger.info(f"🔍 Health Check: http://localhost:{settings.API_PORT}/health")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Tezloan API Server...")
    logger.info("👋 Goodbye from Tezloan!")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Tezloan API Server...")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌍 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug Mode: {settings.DEBUG}")
    print(f"📡 Host: {settings.API_HOST}")
    print(f"🚪 Port: {settings.API_PORT}")
    print()
    
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=settings.DEBUG,
            log_level="info" if not settings.DEBUG else "debug",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/form/loan-application/{form_token}")
async def serve_loan_application_form(form_token: str):
    """Serve personalized loan application form"""
    try:
       
        validation = communication_service.validate_form_token(form_token)
        
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["error"])
        
        
        html_path = Path("frontend/loan-application-form.html")
        if not html_path.exists():
            raise HTTPException(status_code=404, detail="Form not found")
        
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        
        customer_data = validation["customer_data"]
        session_id = validation["session_id"]
        
        
        html_content = html_content.replace(
            'value=""',  # Empty session ID
            f'value="{session_id}"'
        )
        
        
        customer_name = customer_data.get("personal_info", {}).get("name", "")
        if customer_name:
            html_content = html_content.replace(
                'placeholder="First Name"',
                f'value="{customer_name.split()[0]}" placeholder="First Name"'
            )
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Form serving failed: {e}")
        raise HTTPException(status_code=500, detail="Could not load form")

@app.get("/thank-you")
async def serve_thank_you_page(session: str = ""):
    """Serve thank you page after application submission"""
    try:
        html_path = Path("frontend/thank-you.html")
        if html_path.exists():
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        else:
            return {"message": "Thank you for your application! We'll contact you soon."}
    except Exception as e:
        logger.error(f"Failed to serve thank-you page: {e}")
        raise HTTPException(status_code=500, detail="Could not load thank-you page")