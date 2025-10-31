# app/services/communication_service.py (EMAIL-FREE VERSION)
import uuid
import json
import qrcode
from io import BytesIO
import base64
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings

logger = logging.getLogger(__name__)

class CommunicationService:
    """Email-free client communication - QR codes, direct links, and messaging templates"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"  # Update with your domain
        self.form_links = {}  # Store generated form links
        self.report_links = {}  # Store report download links
        self.communication_log = []  # Track all communications
    
    def generate_loan_application_link(self, session_id: str, customer_data: Dict[str, Any]) -> str:
        """Generate personalized loan application form link"""
        try:
            # Create unique form token
            form_token = str(uuid.uuid4())
            
            # Store form data temporarily
            self.form_links[form_token] = {
                "session_id": session_id,
                "customer_data": customer_data,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=24),
                "status": "active",
                "clicks": 0
            }
            
            # Generate form URL
            form_url = f"{self.base_url}/form/loan-application/{form_token}"
            
            logger.info(f"Generated form link for session {session_id}: {form_url}")
            return form_url
            
        except Exception as e:
            logger.error(f"Failed to generate form link: {e}")
            return f"{self.base_url}/form/generic-loan-application"
    
    def generate_report_download_link(self, session_id: str, report_path: str) -> str:
        """Generate secure link for report download"""
        try:
            # Create unique download token
            download_token = str(uuid.uuid4())
            
            # Store download link
            self.report_links[download_token] = {
                "session_id": session_id,
                "report_path": report_path,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=7),
                "download_count": 0,
                "max_downloads": 5,
                "file_size": self._get_file_size(report_path)
            }
            
            # Generate download URL
            download_url = f"{self.base_url}/download/report/{download_token}"
            
            logger.info(f"Generated report download link for session {session_id}: {download_url}")
            return download_url
            
        except Exception as e:
            logger.error(f"Failed to generate report link: {e}")
            return None
    
    def generate_qr_code(self, url: str, label: str = "Scan to Access") -> str:
        """Generate QR code for URL as base64 image"""
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")
            return None
    
    def create_shareable_message(self, customer_name: str, form_link: str, 
                               report_link: str = None, include_qr: bool = True) -> Dict[str, Any]:
        """Create shareable message with multiple formats"""
        try:
            # Generate QR codes if requested
            form_qr = self.generate_qr_code(form_link, "Loan Application") if include_qr else None
            report_qr = self.generate_qr_code(report_link, "Download Report") if include_qr and report_link else None
            
            # Create different message formats
            messages = {
                "whatsapp_message": self._create_whatsapp_message(customer_name, form_link, report_link),
                "sms_message": self._create_sms_message(customer_name, form_link),
                "telegram_message": self._create_telegram_message(customer_name, form_link, report_link),
                "email_template": self._create_email_template(customer_name, form_link, report_link),
                "social_share_text": self._create_social_share_text(customer_name, form_link),
                "qr_codes": {
                    "application_form": form_qr,
                    "report_download": report_qr
                },
                "links": {
                    "application_form": form_link,
                    "report_download": report_link,
                    "short_form_link": self._create_short_link(form_link)
                }
            }
            
            # Log communication
            self._log_communication(customer_name, form_link, "shareable_message_created")
            
            return {
                "status": "success",
                "customer_name": customer_name,
                "messages": messages,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create shareable message: {e}")
            return {"status": "error", "message": str(e)}
    
    def _create_whatsapp_message(self, customer_name: str, form_link: str, report_link: str = None) -> str:
        """Create WhatsApp message template"""
        message = f"""🏦 *Tezloan - Your Loan Application Ready!*

Hello {customer_name}! 👋

Thanks for choosing Tezloan for your loan needs. Your personalized application is ready:

📝 *Complete Your Application:*
{form_link}

{f"📊 *Download Your Analysis Report:*\n{report_link}\n" if report_link else ""}🎯 *Why Tezloan?*
✅ Approval in 20 minutes
✅ Rates starting from 10.5%
✅ Zero hidden charges  
✅ 100% digital process
✅ Instant decisions

⏰ *Complete within 24 hours* for priority processing

Need help? Call us at 1800-LOAN-123

*Best regards,*
*Team Tezloan* 🚀

_Powered by AI • Secured by Trust_"""
        
        return message
    
    def _create_sms_message(self, customer_name: str, form_link: str) -> str:
        """Create SMS message template"""
        short_link = self._create_short_link(form_link)
        
        message = f"""Hi {customer_name}!

Your Tezloan loan application is ready:
{short_link}

✅ Instant approval in 20 mins
✅ Best rates from 10.5%  
✅ Zero processing fee*

Complete within 24hrs for priority.

Support: 1800-LOAN-123
*T&C apply"""
        
        return message
    
    def _create_telegram_message(self, customer_name: str, form_link: str, report_link: str = None) -> str:
        """Create Telegram message template"""
        message = f"""🏦 **Tezloan - Loan Application Ready**

Hello {customer_name}! 

Your personalized loan application is prepared and ready for completion.

🔗 **Complete Application:** [Click Here]({form_link})

{f"📊 **Download Report:** [Analysis Report]({report_link})" if report_link else ""}

**Key Benefits:**
• ⚡ 20-minute approval
• 💰 Competitive rates from 10.5%
• 🚫 Zero hidden charges
• 📱 100% digital process

**⏰ Time Sensitive:** Complete within 24 hours for priority processing.

**Need Assistance?** 
📞 Call: 1800-LOAN-123
💬 Chat: Available 24/7

*Team Tezloan* 🚀"""
        
        return message
    
    def _create_email_template(self, customer_name: str, form_link: str, report_link: str = None) -> str:
        """Create email template (for manual sending)"""
        template = f"""Subject: Your Tezloan Application is Ready - Complete in 5 Minutes!

Hello {customer_name},

Your personalized loan application has been prepared based on our conversation.

COMPLETE YOUR APPLICATION:
{form_link}

{f"DOWNLOAD YOUR ANALYSIS REPORT:\n{report_link}\n\n" if report_link else ""}WHY Tezloan?
✓ Instant approval in 15-20 minutes
✓ Competitive rates starting from 10.5%
✓ Zero processing fee for qualified applicants
✓ Flexible EMI options
✓ 100% secure digital process

IMPORTANT: Please complete your application within 24 hours to maintain your priority status.

Questions? Call us at 1800-LOAN-123 or reply to this message.

Best regards,
The Tezloan Team

---
This is an automated message from Tezloan AI Loan Assistant.
© 2025 Tezloan. All rights reserved."""
        
        return template
    
    def _create_social_share_text(self, customer_name: str, form_link: str) -> str:
        """Create social media share text"""
        return f"""🏦 Just got my personalized loan application from Tezloan! 

Fast approval ✅
Great rates ✅ 
Zero hassle ✅

Check out Tezloan for your loan needs! #Tezloan #PersonalLoan #QuickApproval"""
    
    def _create_short_link(self, long_url: str) -> str:
        """Create shortened URL (mock implementation)"""
        # In production, use services like bit.ly, tinyurl, or your own URL shortener
        url_hash = hash(long_url)
        return f"https://lgn.ie/{abs(url_hash) % 100000}"
    
    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except:
            return 0
    
    def _log_communication(self, customer_name: str, link: str, action: str):
        """Log communication for tracking"""
        self.communication_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "customer_name": customer_name,
            "action": action,
            "link": link[:50] + "..." if len(link) > 50 else link
        })
    
    def create_customer_portal_page(self, session_id: str, customer_data: Dict[str, Any]) -> str:
        """Create temporary customer portal page"""
        try:
            portal_token = str(uuid.uuid4())
            
            # Store portal data
            self.form_links[f"portal_{portal_token}"] = {
                "session_id": session_id,
                "customer_data": customer_data,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=48),
                "type": "customer_portal"
            }
            
            portal_url = f"{self.base_url}/portal/{portal_token}"
            return portal_url
            
        except Exception as e:
            logger.error(f"Failed to create customer portal: {e}")
            return None
    
    def generate_multi_channel_response(self, session_id: str, customer_data: Dict[str, Any], 
                                     report_path: str = None) -> Dict[str, Any]:
        """Generate complete multi-channel communication package"""
        try:
            customer_name = customer_data.get("personal_info", {}).get("name", "Valued Customer")
            
            # Generate links
            form_link = self.generate_loan_application_link(session_id, customer_data)
            report_link = self.generate_report_download_link(session_id, report_path) if report_path else None
            portal_link = self.create_customer_portal_page(session_id, customer_data)
            
            # Create shareable messages
            messages = self.create_shareable_message(customer_name, form_link, report_link)
            
            # Create copy-paste templates
            templates = {
                "manual_email": {
                    "subject": f"Tezloan - Your Loan Application Ready ({datetime.now().strftime('%Y-%m-%d')})",
                    "body": messages["messages"]["email_template"]
                },
                "manual_whatsapp": {
                    "text": messages["messages"]["whatsapp_message"],
                    "instructions": "Copy this text and paste in WhatsApp chat"
                },
                "manual_sms": {
                    "text": messages["messages"]["sms_message"], 
                    "instructions": "Send this text via SMS"
                },
                "phone_script": self._create_phone_script(customer_name, form_link),
                "meeting_agenda": self._create_meeting_agenda(customer_name, customer_data)
            }
            
            return {
                "status": "success",
                "session_id": session_id,
                "customer_name": customer_name,
                "links": {
                    "application_form": form_link,
                    "report_download": report_link,
                    "customer_portal": portal_link
                },
                "qr_codes": messages["messages"]["qr_codes"],
                "communication_templates": templates,
                "sharing_options": {
                    "whatsapp_direct": f"https://wa.me/?text={messages['messages']['whatsapp_message'].replace(' ', '%20')}",
                    "telegram_direct": f"https://t.me/share/url?url={form_link}&text={customer_name}%20your%20loan%20application%20is%20ready",
                    "linkedin_message": templates["manual_email"]["body"].replace('\n', '%0A'),
                    "copy_to_clipboard": messages["messages"]["sms_message"]
                },
                "instructions": {
                    "priority_method": "WhatsApp or direct phone call",
                    "backup_method": "SMS or email template",
                    "follow_up_timing": "After 2-3 hours if no response",
                    "expire_reminder": "Send reminder 2 hours before 24-hour expiry"
                }
            }
            
        except Exception as e:
            logger.error(f"Multi-channel response generation failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def _create_phone_script(self, customer_name: str, form_link: str) -> str:
        """Create phone conversation script"""
        return f"""📞 PHONE SCRIPT for {customer_name}:

"Hello {customer_name}, this is [Your Name] from Tezloan calling regarding your loan application.

Great news! Based on our conversation analysis, your personalized loan application has been prepared and you pre-qualify for our best rates.

I'm sending you a secure link right now where you can complete your application in just 5 minutes. The link is:
{form_link}

You'll also receive a detailed analysis report of your loan eligibility.

The application is pre-filled with your details, so you just need to verify the information and upload your documents.

Do you have any questions about the process? Would you prefer me to stay on the line while you complete it, or would you like me to call you back in 30 minutes?"

📝 FOLLOW-UP NOTES:
- Link expires in 24 hours
- Priority processing if completed today
- Instant approval in 15-20 minutes
- Best rates from 10.5%"""
    
    def _create_meeting_agenda(self, customer_name: str, customer_data: Dict[str, Any]) -> str:
        """Create meeting agenda if face-to-face meeting needed"""
        loan_amount = customer_data.get("loan_details", {}).get("loan_amount", "TBD")
        loan_purpose = customer_data.get("loan_details", {}).get("loan_purpose", "personal")
        
        return f"""📅 MEETING AGENDA with {customer_name}

MEETING OBJECTIVE: Finalize loan application and documentation

AGENDA:
1. Welcome & Relationship Building (5 mins)
2. Review Loan Requirements (10 mins)
   - Amount: ₹{loan_amount:,} for {loan_purpose}
   - Discuss terms and rates
3. Document Verification (15 mins)
   - Review uploaded documents
   - Address any discrepancies
4. Application Completion (10 mins)
   - Complete remaining form fields
   - Digital signature
5. Next Steps & Timeline (5 mins)
   - Explain approval process
   - Set expectations
6. Q&A Session (10 mins)

MATERIALS TO BRING:
- Customer analysis report (printed)
- Loan offer letter
- Terms & conditions document
- Calculator for EMI demonstrations

EXPECTED OUTCOME:
- Complete application submitted
- All documents verified
- Customer satisfaction confirmed"""
    
    def validate_form_token(self, form_token: str) -> Dict[str, Any]:
        """Validate form token and return associated data"""
        try:
            if form_token not in self.form_links:
                return {"valid": False, "error": "Invalid token"}
            
            form_data = self.form_links[form_token]
            
            # Check expiration
            if datetime.utcnow() > form_data["expires_at"]:
                return {"valid": False, "error": "Link expired"}
            
            # Check status
            if form_data.get("status") != "active":
                return {"valid": False, "error": "Link no longer active"}
            
            # Increment click count
            form_data["clicks"] = form_data.get("clicks", 0) + 1
            
            return {
                "valid": True,
                "session_id": form_data["session_id"],
                "customer_data": form_data["customer_data"],
                "created_at": form_data["created_at"],
                "click_count": form_data["clicks"]
            }
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return {"valid": False, "error": "Validation error"}
    
    def validate_download_token(self, download_token: str) -> Dict[str, Any]:
        """Validate download token and return report info"""
        try:
            if download_token not in self.report_links:
                return {"valid": False, "error": "Invalid download link"}
            
            report_data = self.report_links[download_token]
            
            # Check expiration
            if datetime.utcnow() > report_data["expires_at"]:
                return {"valid": False, "error": "Download link expired"}
            
            # Check download limit
            if report_data["download_count"] >= report_data["max_downloads"]:
                return {"valid": False, "error": "Download limit exceeded"}
            
            # Increment download count
            report_data["download_count"] += 1
            
            return {
                "valid": True,
                "report_path": report_data["report_path"],
                "session_id": report_data["session_id"],
                "downloads_remaining": report_data["max_downloads"] - report_data["download_count"],
                "file_size": report_data.get("file_size", 0)
            }
            
        except Exception as e:
            logger.error(f"Download token validation failed: {e}")
            return {"valid": False, "error": "Validation error"}
    
    def get_communication_analytics(self) -> Dict[str, Any]:
        """Get detailed communication analytics"""
        return {
            "summary": {
                "total_links_generated": len(self.form_links),
                "total_reports_generated": len(self.report_links),
                "total_communications": len(self.communication_log),
                "active_links": len([link for link in self.form_links.values() if link.get("status") == "active"]),
            },
            "link_performance": {
                "total_clicks": sum(link.get("clicks", 0) for link in self.form_links.values()),
                "total_downloads": sum(link["download_count"] for link in self.report_links.values()),
                "average_clicks_per_link": sum(link.get("clicks", 0) for link in self.form_links.values()) / len(self.form_links) if self.form_links else 0
            },
            "recent_activity": self.communication_log[-10:],  # Last 10 activities
            "link_expiration_status": {
                "active": len([link for link in self.form_links.values() if datetime.utcnow() < link["expires_at"]]),
                "expired": len([link for link in self.form_links.values() if datetime.utcnow() >= link["expires_at"]])
            }
        }

# Global instance
communication_service = CommunicationService()
