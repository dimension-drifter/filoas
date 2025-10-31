# app/services/report_generator.py
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from typing import Dict, Any
import logging
from datetime import datetime
import json
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate comprehensive PDF reports from transcript and document analysis"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Ensure reports directory exists
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.darkblue,
            spaceAfter=30
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.darkblue,
            spaceBefore=20,
            spaceAfter=10,
            borderWidth=1,
            borderColor=colors.lightgrey,
            borderPadding=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='HighlightBox',
            parent=self.styles['Normal'],
            backgroundColor=colors.lightblue,
            borderWidth=1,
            borderColor=colors.blue,
            borderPadding=10,
            spaceBefore=10,
            spaceAfter=10
        ))
    
    def generate_comprehensive_report(self, 
                                    session_id: str,
                                    transcript_data: Dict[str, Any],
                                    document_data: Dict[str, Any],
                                    additional_data: Dict[str, Any] = None) -> str:
        """Generate comprehensive PDF report"""
        try:
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"loan_report_{session_id}_{timestamp}.pdf"
            filepath = self.reports_dir / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build report content
            story = []
            
            # Header
            story.extend(self._create_header(session_id, timestamp))
            
            # Executive Summary
            story.extend(self._create_executive_summary(transcript_data, document_data))
            
            # Customer Profile
            story.extend(self._create_customer_profile(transcript_data, document_data))
            
            # Loan Analysis
            story.extend(self._create_loan_analysis(transcript_data))
            
            # Document Verification
            story.extend(self._create_document_verification(document_data))
            
            # Risk Assessment
            story.extend(self._create_risk_assessment(transcript_data, document_data))
            
            # Recommendations
            story.extend(self._create_recommendations(transcript_data, document_data))
            
            # Next Steps
            story.extend(self._create_next_steps(transcript_data, document_data))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Report generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise
    
    def _create_header(self, session_id: str, timestamp: str) -> list:
        """Create report header"""
        content = []
        
        # Title
        content.append(Paragraph("LoanGenie - Loan Application Report", self.styles['CustomTitle']))
        
        # Report info table
        report_info = [
            ['Session ID:', session_id],
            ['Generated:', datetime.now().strftime("%B %d, %Y at %I:%M %p")],
            ['Report Type:', 'Comprehensive Loan Analysis'],
            ['Status:', 'Preliminary Assessment']
        ]
        
        table = Table(report_info, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        content.append(Spacer(1, 20))
        
        return content
    
    def _create_executive_summary(self, transcript_data: Dict[str, Any], 
                                document_data: Dict[str, Any]) -> list:
        """Create executive summary section"""
        content = []
        content.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        # Extract key information
        customer_name = self._get_customer_name(transcript_data, document_data)
        loan_amount = transcript_data.get("extracted_data", {}).get("loan_details", {}).get("loan_amount", "Not specified")
        loan_purpose = transcript_data.get("extracted_data", {}).get("loan_details", {}).get("loan_purpose", "Not specified")
        
        summary_text = f"""
        This report presents a comprehensive analysis of the loan application from {customer_name}. 
        The customer has requested a loan amount of ₹{loan_amount:,} for {loan_purpose}. 
        
        Based on our conversation analysis and document verification, the preliminary assessment 
        indicates {"positive eligibility" if self._is_preliminarily_eligible(transcript_data, document_data) else "requires further review"}
        for loan approval.
        
        {transcript_data.get("summary", "Detailed conversation analysis and document verification have been completed.")}
        """
        
        content.append(Paragraph(summary_text, self.styles['Normal']))
        content.append(Spacer(1, 15))
        
        return content
    
    def _create_customer_profile(self, transcript_data: Dict[str, Any], 
                               document_data: Dict[str, Any]) -> list:
        """Create customer profile section"""
        content = []
        content.append(Paragraph("Customer Profile", self.styles['SectionHeader']))
        
        # Personal Information
        personal_info = transcript_data.get("extracted_data", {}).get("personal_info", {})
        doc_profile = document_data.get("consolidated_profile", {})
        
        profile_data = [
            ['Personal Details', ''],
            ['Name:', self._get_customer_name(transcript_data, document_data)],
            ['Date of Birth:', doc_profile.get("personal_details", {}).get("date_of_birth", "Not provided")],
            ['Gender:', doc_profile.get("personal_details", {}).get("gender", "Not provided")],
            ['Phone:', personal_info.get("phone", "Not provided")],
            ['Email:', personal_info.get("email", "Not provided")],
            ['', ''],
            ['Employment Details', ''],
            ['Employer:', doc_profile.get("employment_details", {}).get("employer", "Not provided")],
            ['Designation:', doc_profile.get("employment_details", {}).get("designation", "Not provided")],
            ['Monthly Income:', f"₹{doc_profile.get('financial_details', {}).get('net_salary', 'Not provided'):,}"],
            ['', ''],
            ['Identity Verification', ''],
            ['PAN Number:', doc_profile.get("identity_details", {}).get("pan_number", "Not provided")],
            ['Aadhar Number:', doc_profile.get("identity_details", {}).get("aadhar_number", "Not provided")],
        ]
        
        table = Table(profile_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.darkblue),
            ('BACKGROUND', (0, 7), (0, 7), colors.darkblue),
            ('BACKGROUND', (0, 12), (0, 12), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('TEXTCOLOR', (0, 7), (0, 7), colors.white),
            ('TEXTCOLOR', (0, 12), (0, 12), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
        ]))
        
        content.append(table)
        content.append(Spacer(1, 15))
        
        return content
    
    def _create_loan_analysis(self, transcript_data: Dict[str, Any]) -> list:
        """Create loan analysis section"""
        content = []
        content.append(Paragraph("Loan Request Analysis", self.styles['SectionHeader']))
        
        loan_details = transcript_data.get("extracted_data", {}).get("loan_details", {})
        employment_info = transcript_data.get("extracted_data", {}).get("employment_info", {})
        
        loan_amount = loan_details.get("loan_amount", 0)
        monthly_income = employment_info.get("monthly_income", 0)
        
        # Calculate ratios if data available
        if loan_amount and monthly_income:
            annual_income = monthly_income * 12
            loan_to_income_ratio = loan_amount / annual_income
            estimated_emi = self._calculate_emi(loan_amount, 10.5, 36)
            emi_to_income_ratio = (estimated_emi / monthly_income) * 100
        else:
            loan_to_income_ratio = 0
            estimated_emi = 0
            emi_to_income_ratio = 0
        
        analysis_data = [
            ['Loan Analysis', ''],
            ['Requested Amount:', f"₹{loan_amount:,}" if loan_amount else "Not specified"],
            ['Purpose:', loan_details.get("loan_purpose", "Not specified").title()],
            ['Urgency:', loan_details.get("urgency", "Not specified").title()],
            ['', ''],
            ['Financial Assessment', ''],
            ['Monthly Income:', f"₹{monthly_income:,}" if monthly_income else "Not provided"],
            ['Loan-to-Income Ratio:', f"{loan_to_income_ratio:.2f}x" if loan_to_income_ratio else "Cannot calculate"],
            ['Estimated EMI (10.5%, 36m):', f"₹{estimated_emi:,.0f}" if estimated_emi else "Cannot calculate"],
            ['EMI-to-Income Ratio:', f"{emi_to_income_ratio:.1f}%" if emi_to_income_ratio else "Cannot calculate"],
            ['', ''],
            ['Eligibility Indicators', ''],
            ['Income Adequacy:', "✓ Adequate" if loan_to_income_ratio <= 3 else "⚠ Review Required"],
            ['EMI Affordability:', "✓ Affordable" if emi_to_income_ratio <= 40 else "⚠ High EMI Ratio"],
        ]
        
        table = Table(analysis_data, colWidths=[2.5*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.darkgreen),
            ('BACKGROUND', (0, 5), (0, 5), colors.darkgreen),
            ('BACKGROUND', (0, 11), (0, 11), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('TEXTCOLOR', (0, 5), (0, 5), colors.white),
            ('TEXTCOLOR', (0, 11), (0, 11), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
        ]))
        
        content.append(table)
        content.append(Spacer(1, 15))
        
        return content
    
    def _create_document_verification(self, document_data: Dict[str, Any]) -> list:
        """Create document verification section"""
        content = []
        content.append(Paragraph("Document Verification Status", self.styles['SectionHeader']))
        
        analysis_results = document_data.get("analysis_results", {})
        verification_score = document_data.get("verification_score", 0)
        
        # Overall verification status
        status_text = f"""
        <b>Overall Verification Score: {verification_score}%</b><br/>
        Status: {"✓ Verified" if verification_score >= 80 else "⚠ Needs Review" if verification_score >= 60 else "❌ Incomplete"}
        """
        
        content.append(Paragraph(status_text, self.styles['HighlightBox']))
        
        # Document-wise verification
        doc_verification = [['Document Type', 'Status', 'Confidence', 'Issues']]
        
        for doc_type, result in analysis_results.items():
            status = result.get("status", "unknown")
            confidence = result.get("confidence", 0)
            issues = ", ".join(result.get("issues", [])) or "None"
            
            doc_verification.append([
                doc_type.replace("_", " ").title(),
                "✓ Verified" if status == "verified" else "⚠ Review" if status == "needs_review" else "❌ Error",
                f"{confidence}%",
                issues
            ])
        
        table = Table(doc_verification, colWidths=[1.5*inch, 1.2*inch, 1*inch, 2.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        content.append(Spacer(1, 15))
        
        return content
    
    def _create_risk_assessment(self, transcript_data: Dict[str, Any], 
                              document_data: Dict[str, Any]) -> list:
        """Create risk assessment section"""
        content = []
        content.append(Paragraph("Risk Assessment", self.styles['SectionHeader']))
        
        # Calculate risk factors
        risk_factors = self._calculate_risk_factors(transcript_data, document_data)
        
        risk_text = f"""
        <b>Risk Category: {risk_factors['category']}</b><br/>
        Overall Risk Score: {risk_factors['score']}/100<br/>
        Recommendation: {risk_factors['recommendation']}
        """
        
        content.append(Paragraph(risk_text, self.styles['HighlightBox']))
        
        # Risk breakdown
        risk_breakdown = [['Risk Factor', 'Score', 'Impact', 'Comments']]
        
        for factor in risk_factors['factors']:
            risk_breakdown.append([
                factor['name'],
                f"{factor['score']}/100",
                factor['impact'],
                factor['comment']
            ])
        
        table = Table(risk_breakdown, colWidths=[1.8*inch, 0.8*inch, 1*inch, 2.4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        content.append(Spacer(1, 15))
        
        return content
    
    def _create_recommendations(self, transcript_data: Dict[str, Any], 
                              document_data: Dict[str, Any]) -> list:
        """Create recommendations section"""
        content = []
        content.append(Paragraph("Recommendations", self.styles['SectionHeader']))
        
        recommendations = transcript_data.get("report_data", {}).get("recommendations", [])
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                content.append(Paragraph(f"{i}. {rec}", self.styles['Normal']))
        else:
            content.append(Paragraph("No specific recommendations generated.", self.styles['Normal']))
        
        content.append(Spacer(1, 15))
        return content
    
    def _create_next_steps(self, transcript_data: Dict[str, Any], 
                         document_data: Dict[str, Any]) -> list:
        """Create next steps section"""
        content = []
        content.append(Paragraph("Next Steps", self.styles['SectionHeader']))
        
        next_actions = transcript_data.get("report_data", {}).get("next_actions", [])
        
        if next_actions:
            for i, action in enumerate(next_actions, 1):
                content.append(Paragraph(f"{i}. {action}", self.styles['Normal']))
        else:
            default_actions = [
                "Complete document verification if pending",
                "Conduct credit assessment",
                "Generate loan offer",
                "Schedule customer meeting for final approval"
            ]
            for i, action in enumerate(default_actions, 1):
                content.append(Paragraph(f"{i}. {action}", self.styles['Normal']))
        
        return content
    
    def _get_customer_name(self, transcript_data: Dict[str, Any], 
                          document_data: Dict[str, Any]) -> str:
        """Extract customer name from available data"""
        # Try transcript first
        name = transcript_data.get("extracted_data", {}).get("personal_info", {}).get("name")
        if name:
            return name
        
        # Try document data
        name = document_data.get("consolidated_profile", {}).get("personal_details", {}).get("name")
        if name:
            return name
        
        return "Customer"
    
    def _is_preliminarily_eligible(self, transcript_data: Dict[str, Any], 
                                 document_data: Dict[str, Any]) -> bool:
        """Check preliminary eligibility"""
        verification_score = document_data.get("verification_score", 0)
        loan_amount = transcript_data.get("extracted_data", {}).get("loan_details", {}).get("loan_amount", 0)
        monthly_income = transcript_data.get("extracted_data", {}).get("employment_info", {}).get("monthly_income", 0)
        
        if verification_score < 70:
            return False
        
        if loan_amount and monthly_income:
            loan_to_income_ratio = loan_amount / (monthly_income * 12)
            return loan_to_income_ratio <= 3.5
        
        return True
    
    def _calculate_emi(self, principal: float, annual_rate: float, tenure_months: int) -> float:
        """Calculate EMI"""
        if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
            return 0
        
        monthly_rate = annual_rate / (12 * 100)
        emi = principal * monthly_rate * (1 + monthly_rate)**tenure_months / ((1 + monthly_rate)**tenure_months - 1)
        return emi
    
    def _calculate_risk_factors(self, transcript_data: Dict[str, Any], 
                              document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive risk assessment"""
        factors = []
        total_score = 0
        
        # Document verification risk
        doc_score = document_data.get("verification_score", 0)
        doc_risk_score = min(100, doc_score + 10)
        factors.append({
            "name": "Document Verification",
            "score": doc_risk_score,
            "impact": "High" if doc_score < 70 else "Medium" if doc_score < 85 else "Low",
            "comment": f"Verification score: {doc_score}%"
        })
        total_score += doc_risk_score * 0.3
        
        # Income stability risk
        monthly_income = transcript_data.get("extracted_data", {}).get("employment_info", {}).get("monthly_income", 0)
        income_risk_score = min(100, (monthly_income / 1000) if monthly_income > 25000 else 50)
        factors.append({
            "name": "Income Stability",
            "score": income_risk_score,
            "impact": "High" if monthly_income < 30000 else "Medium" if monthly_income < 60000 else "Low",
            "comment": f"Monthly income: ₹{monthly_income:,}" if monthly_income else "Income not verified"
        })
        total_score += income_risk_score * 0.4
        
        # Loan amount risk
        loan_amount = transcript_data.get("extracted_data", {}).get("loan_details", {}).get("loan_amount", 0)
        if loan_amount and monthly_income:
            ratio = loan_amount / (monthly_income * 12)
            amount_risk_score = max(20, 100 - (ratio * 30))
        else:
            amount_risk_score = 50
        
        factors.append({
            "name": "Loan Amount Risk",
            "score": amount_risk_score,
            "impact": "High" if amount_risk_score < 60 else "Medium" if amount_risk_score < 80 else "Low",
            "comment": f"Loan-to-income ratio: {ratio:.2f}x" if loan_amount and monthly_income else "Ratio not calculable"
        })
        total_score += amount_risk_score * 0.3
        
        # Determine overall risk category
        if total_score >= 80:
            category = "Low Risk"
            recommendation = "Approve with standard terms"
        elif total_score >= 60:
            category = "Medium Risk"
            recommendation = "Approve with enhanced monitoring"
        else:
            category = "High Risk"
            recommendation = "Require additional documentation"
        
        return {
            "score": round(total_score),
            "category": category,
            "recommendation": recommendation,
            "factors": factors
        }

# Global instance
report_generator = ReportGenerator()
