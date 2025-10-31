# app/agents/credit_agent.py
from .base_agent import BaseAgent
from typing import Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CreditAgent(BaseAgent):
    """Credit Assessment Agent for loan approval decisions"""
    
    def __init__(self):
        super().__init__(
            name="CreditAgent", 
            description="Performs credit assessment and loan approval decisions"
        )
        
        # Credit scoring parameters
        self.income_weight = 0.35
        self.employment_weight = 0.25
        self.existing_loans_weight = 0.20
        self.credit_history_weight = 0.20
        
        # Risk categories
        self.risk_categories = {
            "LOW": {"min_score": 750, "max_ltv": 0.80, "interest_rate": 10.5},
            "MEDIUM": {"min_score": 650, "max_ltv": 0.70, "interest_rate": 12.5},
            "HIGH": {"min_score": 600, "max_ltv": 0.60, "interest_rate": 15.5}
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process credit assessment request"""
        self.log_processing("credit_assessment_start", input_data)
        
        try:
            customer_data = input_data.get("customer_data", {})
            loan_amount = input_data.get("loan_amount", 0)
            loan_purpose = input_data.get("loan_purpose", "personal")
            kyc_data = input_data.get("kyc_data", {})
            
            # Calculate credit score
            credit_score = self._calculate_credit_score(customer_data, kyc_data)
            
            # Assess risk category
            risk_category = self._assess_risk_category(credit_score, customer_data)
            
            # Make loan decision
            loan_decision = self._make_loan_decision(
                credit_score, risk_category, loan_amount, customer_data
            )
            
            # Generate loan offer if approved
            loan_offer = self._generate_loan_offer(
                loan_decision, risk_category, loan_amount, loan_purpose
            ) if loan_decision["approved"] else None
            
            # Generate response message
            response_text = await self._generate_credit_response(loan_decision, loan_offer)
            
            result = {
                "agent": self.name,
                "credit_score": credit_score,
                "risk_category": risk_category,
                "loan_decision": loan_decision,
                "loan_offer": loan_offer,
                "response_text": response_text,
                "assessment_details": self._get_assessment_details(customer_data, credit_score),
                "recommendations": self._get_recommendations(loan_decision, credit_score),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.log_processing("credit_assessment_complete", result)
            return result
            
        except Exception as e:
            logger.error(f"Credit assessment failed: {e}")
            return {
                "agent": self.name,
                "error": str(e),
                "loan_decision": {"approved": False, "reason": "Assessment error"},
                "response_text": "Unable to complete credit assessment. Please try again."
            }
    
    def _calculate_credit_score(self, customer_data: Dict[str, Any], kyc_data: Dict[str, Any]) -> int:
        """Calculate customer credit score (300-850)"""
        base_score = 650  # Starting baseline
        
        # Income factor
        monthly_income = customer_data.get("monthly_income", 0)
        if monthly_income >= 100000:
            base_score += 100
        elif monthly_income >= 75000:
            base_score += 75
        elif monthly_income >= 50000:
            base_score += 50
        elif monthly_income >= 30000:
            base_score += 25
        
        # Employment stability
        employer = kyc_data.get("employer", "").lower()
        if any(company in employer for company in ["infosys", "tcs", "wipro", "accenture", "google", "microsoft"]):
            base_score += 50  # Top tier companies
        elif "pvt ltd" in employer or "limited" in employer:
            base_score += 25  # Corporate employment
        
        # Age factor (younger professionals might have lower scores initially)
        # Mock calculation based on typical patterns
        base_score += 20  # Assume good payment history
        
        # Cap the score
        return min(850, max(300, base_score))
    
    def _assess_risk_category(self, credit_score: int, customer_data: Dict[str, Any]) -> str:
        """Assess customer risk category"""
        monthly_income = customer_data.get("monthly_income", 0)
        
        if credit_score >= 750 and monthly_income >= 50000:
            return "LOW"
        elif credit_score >= 650 and monthly_income >= 30000:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def _make_loan_decision(self, credit_score: int, risk_category: str, 
                          loan_amount: int, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make final loan approval decision"""
        monthly_income = customer_data.get("monthly_income", 0)
        
        # Calculate debt-to-income ratio
        annual_income = monthly_income * 12
        max_loan_amount = annual_income * 3  # 3x annual income max
        
        # Decision logic
        if credit_score < 600:
            return {
                "approved": False,
                "reason": "Credit score below minimum threshold",
                "min_credit_score_required": 600
            }
        
        if loan_amount > max_loan_amount:
            return {
                "approved": False,
                "reason": "Loan amount exceeds income limit",
                "max_eligible_amount": max_loan_amount
            }
        
        if monthly_income < 25000:
            return {
                "approved": False,
                "reason": "Minimum income requirement not met",
                "min_income_required": 25000
            }
        
        # Approved!
        return {
            "approved": True,
            "reason": "Customer meets all eligibility criteria",
            "confidence": min(95, credit_score / 10)
        }
    
    def _generate_loan_offer(self, loan_decision: Dict[str, Any], risk_category: str,
                           loan_amount: int, loan_purpose: str) -> Dict[str, Any]:
        """Generate detailed loan offer"""
        if not loan_decision["approved"]:
            return None
        
        risk_params = self.risk_categories[risk_category]
        
        # Calculate EMI (simple calculation)
        interest_rate = risk_params["interest_rate"]
        tenure_months = 36  # 3 years default
        
        monthly_rate = interest_rate / (12 * 100)
        emi = loan_amount * monthly_rate * (1 + monthly_rate)**tenure_months / ((1 + monthly_rate)**tenure_months - 1)
        
        return {
            "loan_amount": loan_amount,
            "interest_rate": interest_rate,
            "tenure_months": tenure_months,
            "monthly_emi": round(emi, 2),
            "total_payable": round(emi * tenure_months, 2),
            "processing_fee": loan_amount * 0.02,  # 2% processing fee
            "loan_purpose": loan_purpose,
            "risk_category": risk_category,
            "offer_valid_till": "7 days",
            "special_benefits": self._get_special_benefits(risk_category)
        }
    
    def _get_special_benefits(self, risk_category: str) -> List[str]:
        """Get special benefits based on risk category"""
        if risk_category == "LOW":
            return [
                "Zero processing fee for IT professionals",
                "Flexible EMI options",
                "Pre-approved top-up facility",
                "Priority customer service"
            ]
        elif risk_category == "MEDIUM":
            return [
                "Reduced processing fee",
                "EMI holiday option",
                "Easy documentation"
            ]
        else:
            return [
                "Quick approval",
                "Minimal documentation"
            ]
    
    async def _generate_credit_response(self, loan_decision: Dict[str, Any], 
                                      loan_offer: Dict[str, Any]) -> str:
        """Generate human-readable credit response"""
        if loan_decision["approved"]:
            emi = loan_offer["monthly_emi"]
            rate = loan_offer["interest_rate"]
            return f"Great news! Your loan is approved! 🎉 You qualify for ₹{loan_offer['loan_amount']:,} at {rate}% interest rate. Your EMI will be just ₹{emi:,.0f} per month. This is a fantastic deal for you!"
        else:
            reason = loan_decision["reason"]
            return f"Thank you for your interest! Currently, we cannot approve your loan due to: {reason}. Don't worry - our team can help you improve your eligibility. Would you like to speak with our advisor?"
    
    def _get_assessment_details(self, customer_data: Dict[str, Any], credit_score: int) -> Dict[str, Any]:
        """Get detailed assessment breakdown"""
        return {
            "income_assessment": "Strong" if customer_data.get("monthly_income", 0) >= 50000 else "Moderate",
            "employment_stability": "Excellent" if "infosys" in customer_data.get("employer", "").lower() else "Good",
            "credit_score_category": "Excellent" if credit_score >= 750 else "Good" if credit_score >= 650 else "Fair",
            "overall_assessment": "Strong candidate for loan approval"
        }
    
    def _get_recommendations(self, loan_decision: Dict[str, Any], credit_score: int) -> List[str]:
        """Get recommendations for customer"""
        if loan_decision["approved"]:
            return [
                "Consider setting up auto-pay for EMIs",
                "Build emergency fund equivalent to 6 months EMI",
                "Monitor your credit score regularly",
                "Consider insurance for loan protection"
            ]
        else:
            return [
                "Work on improving credit score",
                "Increase income through skill development",
                "Reduce existing debt obligations",
                "Consider applying for a smaller amount"
            ]

# Global instance
credit_agent = CreditAgent()
