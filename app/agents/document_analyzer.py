# app/agents/document_analyzer.py
from .base_agent import BaseAgent
from typing import Dict, Any, List
import logging
from datetime import datetime
import re
import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class DocumentAnalyzer(BaseAgent):
    """Analyze uploaded documents (PAN, Aadhar, Salary Slips) and extract information"""
    
    def __init__(self):
        super().__init__(
            name="DocumentAnalyzer",
            description="Analyzes KYC documents and extracts structured information"
        )
        
        self.document_types = {
            "pan_card": {
                "required_fields": ["pan_number", "name", "father_name", "date_of_birth"],
                "validation_patterns": {
                    "pan_number": r"[A-Z]{5}[0-9]{4}[A-Z]{1}"
                }
            },
            "aadhar_card": {
                "required_fields": ["aadhar_number", "name", "address", "date_of_birth", "gender"],
                "validation_patterns": {
                    "aadhar_number": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}"
                }
            },
            "salary_slip": {
                "required_fields": ["employee_name", "designation", "basic_salary", "gross_salary", "net_salary", "employer", "month_year"],
                "validation_patterns": {
                    "employee_id": r"[A-Z0-9]{4,10}"
                }
            }
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process uploaded documents and extract information"""
        self.log_processing("document_analysis_start", input_data)
        
        try:
            session_id = input_data.get("session_id", "")
            documents = input_data.get("documents", {})
            
            if not documents:
                raise ValueError("No documents provided for analysis")
            
            analysis_results = {}
            
            # Analyze each document type
            for doc_type, doc_data in documents.items():
                if doc_type in self.document_types:
                    analysis_results[doc_type] = await self._analyze_document(doc_type, doc_data)
                else:
                    analysis_results[doc_type] = {
                        "status": "unsupported",
                        "message": f"Document type {doc_type} not supported"
                    }
            
            # Cross-validate information across documents
            validation_report = self._cross_validate_documents(analysis_results)
            
            # Generate consolidated profile
            consolidated_profile = self._create_consolidated_profile(analysis_results)
            
            # Calculate document verification score
            verification_score = self._calculate_verification_score(analysis_results, validation_report)
            
            result = {
                "agent": self.name,
                "session_id": session_id,
                "documents_analyzed": list(documents.keys()),
                "analysis_results": analysis_results,
                "validation_report": validation_report,
                "consolidated_profile": consolidated_profile,
                "verification_score": verification_score,
                "overall_status": "verified" if verification_score >= 80 else "needs_review",
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            self.log_processing("document_analysis_complete", result)
            return result
            
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return {
                "agent": self.name,
                "session_id": session_id,
                "error": str(e),
                "overall_status": "error",
                "message": "Failed to analyze documents. Please try again."
            }
    
    async def _analyze_document(self, doc_type: str, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual document and extract information"""
        try:
            # In a real system, you'd use OCR/ML to extract text from images
            # For demo, we'll simulate document analysis
            
            if doc_type == "pan_card":
                return self._analyze_pan_card(doc_data)
            elif doc_type == "aadhar_card":
                return self._analyze_aadhar_card(doc_data)
            elif doc_type == "salary_slip":
                return self._analyze_salary_slip(doc_data)
            else:
                return {
                    "status": "unsupported",
                    "message": f"Analysis not implemented for {doc_type}"
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze {doc_type}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "extracted_data": {}
            }
    
    def _analyze_pan_card(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze PAN card and extract information"""
        # Simulate PAN card OCR extraction
        extracted_data = {
            "pan_number": "ABCDE1234F",
            "name": "RAHUL KUMAR",
            "father_name": "SURESH KUMAR",
            "date_of_birth": "15/08/1995",
            "document_type": "PAN CARD"
        }
        
        # Validate PAN format
        pan_valid = bool(re.match(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", extracted_data["pan_number"]))
        
        # Calculate confidence based on data completeness
        confidence = 95 if pan_valid else 60
        
        issues = []
        if not pan_valid:
            issues.append("Invalid PAN number format")
        
        return {
            "status": "verified" if confidence >= 80 else "needs_review",
            "confidence": confidence,
            "extracted_data": extracted_data,
            "validation_results": {
                "pan_format_valid": pan_valid,
                "name_extracted": bool(extracted_data.get("name")),
                "dob_extracted": bool(extracted_data.get("date_of_birth"))
            },
            "issues": issues
        }
    
    def _analyze_aadhar_card(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Aadhar card and extract information"""
        # Simulate Aadhar card OCR extraction
        extracted_data = {
            "aadhar_number": "1234-5678-9012",
            "name": "Rahul Kumar",
            "address": "123, MG Road, Koramangala, Bangalore, Karnataka - 560034",
            "date_of_birth": "15/08/1995",
            "gender": "MALE",
            "document_type": "AADHAR CARD"
        }
        
        # Validate Aadhar format
        aadhar_valid = bool(re.match(r"\d{4}[-\s]?\d{4}[-\s]?\d{4}", extracted_data["aadhar_number"]))
        
        confidence = 92 if aadhar_valid else 65
        
        issues = []
        if not aadhar_valid:
            issues.append("Invalid Aadhar number format")
        
        return {
            "status": "verified" if confidence >= 80 else "needs_review",
            "confidence": confidence,
            "extracted_data": extracted_data,
            "validation_results": {
                "aadhar_format_valid": aadhar_valid,
                "name_extracted": bool(extracted_data.get("name")),
                "address_extracted": bool(extracted_data.get("address")),
                "dob_extracted": bool(extracted_data.get("date_of_birth"))
            },
            "issues": issues
        }
    
    def _analyze_salary_slip(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze salary slip and extract information"""
        # Simulate salary slip OCR extraction (could be multiple slips)
        extracted_data = {
            "employee_name": "RAHUL KUMAR",
            "employee_id": "INF12345",
            "designation": "SOFTWARE ENGINEER",
            "department": "TECHNOLOGY",
            "employer": "INFOSYS LIMITED",
            "month_year": "SEPTEMBER 2025",
            "basic_salary": 45000,
            "hra": 18000,
            "special_allowance": 12000,
            "gross_salary": 75000,
            "pf_deduction": 5400,
            "tax_deduction": 4600,
            "net_salary": 65000,
            "bank_account": "HDFC Bank - ****1234"
        }
        
        # Validate salary data
        salary_valid = (
            extracted_data.get("gross_salary", 0) > 0 and
            extracted_data.get("net_salary", 0) > 0 and
            extracted_data.get("employer", "").strip() != ""
        )
        
        confidence = 88 if salary_valid else 50
        
        issues = []
        if not salary_valid:
            issues.append("Incomplete salary information")
        
        return {
            "status": "verified" if confidence >= 80 else "needs_review",
            "confidence": confidence,
            "extracted_data": extracted_data,
            "validation_results": {
                "salary_data_complete": salary_valid,
                "employer_identified": bool(extracted_data.get("employer")),
                "net_salary_valid": extracted_data.get("net_salary", 0) > 0
            },
            "issues": issues
        }
    
    def _cross_validate_documents(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-validate information across different documents"""
        validation_report = {
            "name_consistency": {"status": "unknown", "details": []},
            "dob_consistency": {"status": "unknown", "details": []},
            "identity_verification": {"status": "unknown", "details": []},
            "income_verification": {"status": "unknown", "details": []}
        }
        
        # Extract names from different documents
        names = {}
        if "pan_card" in analysis_results:
            pan_name = analysis_results["pan_card"].get("extracted_data", {}).get("name", "").upper()
            if pan_name:
                names["pan"] = pan_name
        
        if "aadhar_card" in analysis_results:
            aadhar_name = analysis_results["aadhar_card"].get("extracted_data", {}).get("name", "").upper()
            if aadhar_name:
                names["aadhar"] = aadhar_name
        
        if "salary_slip" in analysis_results:
            salary_name = analysis_results["salary_slip"].get("extracted_data", {}).get("employee_name", "").upper()
            if salary_name:
                names["salary"] = salary_name
        
        # Validate name consistency
        if len(names) >= 2:
            name_values = list(names.values())
            # Simple name matching (in real system, use fuzzy matching)
            names_match = all(name.replace(" ", "") == name_values[0].replace(" ", "") for name in name_values)
            
            validation_report["name_consistency"] = {
                "status": "consistent" if names_match else "inconsistent",
                "details": [f"{doc}: {name}" for doc, name in names.items()],
                "match_score": 100 if names_match else 60
            }
        
        # Extract and validate dates of birth
        dobs = {}
        if "pan_card" in analysis_results:
            pan_dob = analysis_results["pan_card"].get("extracted_data", {}).get("date_of_birth")
            if pan_dob:
                dobs["pan"] = pan_dob
        
        if "aadhar_card" in analysis_results:
            aadhar_dob = analysis_results["aadhar_card"].get("extracted_data", {}).get("date_of_birth")
            if aadhar_dob:
                dobs["aadhar"] = aadhar_dob
        
        if len(dobs) >= 2:
            dob_values = list(dobs.values())
            dobs_match = all(dob == dob_values[0] for dob in dob_values)
            
            validation_report["dob_consistency"] = {
                "status": "consistent" if dobs_match else "inconsistent",
                "details": [f"{doc}: {dob}" for doc, dob in dobs.items()],
                "match_score": 100 if dobs_match else 40
            }
        
        return validation_report
    
    def _create_consolidated_profile(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create consolidated customer profile from all documents"""
        profile = {
            "personal_details": {},
            "employment_details": {},
            "financial_details": {},
            "address_details": {},
            "identity_details": {}
        }
        
        # Consolidate from PAN card
        if "pan_card" in analysis_results:
            pan_data = analysis_results["pan_card"].get("extracted_data", {})
            profile["personal_details"]["name"] = pan_data.get("name", "").title()
            profile["personal_details"]["father_name"] = pan_data.get("father_name", "").title()
            profile["personal_details"]["date_of_birth"] = pan_data.get("date_of_birth")
            profile["identity_details"]["pan_number"] = pan_data.get("pan_number")
        
        # Consolidate from Aadhar card
        if "aadhar_card" in analysis_results:
            aadhar_data = analysis_results["aadhar_card"].get("extracted_data", {})
            if not profile["personal_details"].get("name"):
                profile["personal_details"]["name"] = aadhar_data.get("name", "").title()
            profile["personal_details"]["gender"] = aadhar_data.get("gender", "").title()
            profile["address_details"]["full_address"] = aadhar_data.get("address")
            profile["identity_details"]["aadhar_number"] = aadhar_data.get("aadhar_number")
        
        # Consolidate from salary slip
        if "salary_slip" in analysis_results:
            salary_data = analysis_results["salary_slip"].get("extracted_data", {})
            profile["employment_details"]["employer"] = salary_data.get("employer")
            profile["employment_details"]["designation"] = salary_data.get("designation")
            profile["employment_details"]["employee_id"] = salary_data.get("employee_id")
            profile["financial_details"]["gross_salary"] = salary_data.get("gross_salary")
            profile["financial_details"]["net_salary"] = salary_data.get("net_salary")
            profile["financial_details"]["bank_account"] = salary_data.get("bank_account")
        
        return profile
    
    def _calculate_verification_score(self, analysis_results: Dict[str, Any], 
                                    validation_report: Dict[str, Any]) -> float:
        """Calculate overall document verification score"""
        total_score = 0
        max_score = 0
        
        # Individual document scores
        for doc_type, result in analysis_results.items():
            if result.get("status") == "verified":
                total_score += result.get("confidence", 0)
                max_score += 100
            elif result.get("status") == "needs_review":
                total_score += result.get("confidence", 0) * 0.5
                max_score += 100
        
        # Cross-validation bonuses
        name_consistency = validation_report.get("name_consistency", {})
        if name_consistency.get("status") == "consistent":
            total_score += 20
        
        dob_consistency = validation_report.get("dob_consistency", {})
        if dob_consistency.get("status") == "consistent":
            total_score += 15
        
        max_score += 35  # Max bonus from cross-validation
        
        return round((total_score / max_score * 100) if max_score > 0 else 0, 2)

# Global instance
document_analyzer = DocumentAnalyzer()
