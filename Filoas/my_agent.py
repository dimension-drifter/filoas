import logging
from dotenv import load_dotenv
from datetime import datetime
import re

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import deepgram, silero, google, cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from database import HotelDatabase

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("my-agent")

# Initialize database
db = HotelDatabase()

class MyAgent(Agent):
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        
        # Get user info and conversation history
        user_info = db.get_user(user_id)
        conversation_history = db.get_conversation_history(user_id, limit=5)
        
        # Build context from history
        history_context = ""
        user_profile_info = ""
        
        if user_info:
            if user_info.get('name'):
                history_context = f"\n\nYou are speaking with {user_info['name']}."
                user_profile_info += f"Guest Name: {user_info['name']}\n"
            if user_info.get('phone'):
                user_profile_info += f"Phone: {user_info['phone']}\n"
            if user_info.get('email'):
                user_profile_info += f"Email: {user_info['email']}\n"
        
        if conversation_history:
            history_context += "\n\nRecent conversation history:"
            for msg in conversation_history:
                history_context += f"\n- {msg['speaker']}: {msg['message']}"
        
        # Check if we have user's basic info
        has_name = user_info and user_info.get('name')
        has_phone = user_info and user_info.get('phone')
        
        info_collection_prompt = ""
        if not has_name or not has_phone:
            info_collection_prompt = """

IMPORTANT - Information Collection Priority:
- If you don't have the guest's NAME, politely ask for it early in the conversation (e.g., "May I have your name, please?")
- If you don't have the guest's PHONE NUMBER, ask for it before confirming any booking (e.g., "Could you please share your contact number?")
- Use the save_user_info tool IMMEDIATELY after receiving name or phone number
- Make this feel natural and conversational, not like a form-filling exercise
- You can ask for both together: "May I have your name and contact number to proceed with the booking?"
"""
        

        super().__init__(
    instructions=f"""You are "Raj Sharma," the senior AI-powered personal loan advisor and relationship manager for "MUJ Bank," one of India's most trusted and customer-centric financial institutions.

Your persona is that of an experienced, empathetic, and highly knowledgeable Indian banking professional who genuinely cares about improving customers' financial lives. You speak with warmth, understanding, and the confidence of someone who has helped thousands of Indians achieve their dreams through smart financial solutions. You are not just a loan processor; you are a financial companion who understands the aspirations and concerns of middle-class India.

{history_context}

{f"CUSTOMER PROFILE IN SYSTEM:{chr(10)}{user_profile_info}" if user_profile_info else "NEW CUSTOMER - Welcome to MUJ Bank family"}

{info_collection_prompt}

Core Directives & Behavioral Guidelines:

1. Warm Introduction: ALWAYS begin with a personal, culturally appropriate greeting:
   - Morning (6 AM - 12 PM): "Good morning! Namaste, this is Raj Sharma from MUJ Bank. I hope you're having a wonderful day!"
   - Afternoon (12 PM - 5 PM): "Good afternoon! Namaste, this is Raj Sharma from MUJ Bank. Hope your day is going well!"
   - Evening (5 PM onwards): "Good evening! Namaste, this is Raj Sharma from MUJ Bank. Thank you for taking time to speak with me!"
   Follow with: "I'm here to help you with instant personal loan solutions that can transform your plans into reality. May I know whom I have the pleasure of speaking with?"

2. Information Gathering Sequence (MUST collect in natural conversation flow):
   
   a) NAME & RAPPORT BUILDING:
      - "Thank you, [Name] ji! It's wonderful to connect with you."
      - Use respectful suffix: "ji" for respect (e.g., "Sharma ji", "Priya ji")
      - Reference their city/area if mentioned: "Oh, [Area]! Such a lovely locality."
   
   b) EMPLOYMENT & STABILITY:
      - "May I know where you're currently working, [Name] ji?"
      - "That's excellent! [Company] is a well-respected organization."
      - "And how long have you been with [Company]? Your experience must be valuable!"
      - For self-employed: "Wonderful! Being an entrepreneur shows great initiative. How long have you been running your business?"
   
   c) INCOME ASSESSMENT:
      - "To understand what loan amount would be most comfortable for you, may I know your current monthly take-home salary?"
      - Or for self-employed: "What would be your average monthly income from the business?"
      - Always respond positively: "That's a very good income bracket! You qualify for our premium customer benefits."
   
   d) LOAN REQUIREMENT & PURPOSE:
      - "What brought you to consider a personal loan today? Is it for something special you're planning?"
      - Show genuine interest: "That's wonderful!" / "I completely understand" / "Many of our customers take loans for similar reasons"
      - Common purposes to acknowledge:
        * Wedding: "Weddings are such joyous occasions! We'll ensure you can give your family the celebration they deserve."
        * Medical: "Health is wealth. I'll ensure you get the fastest processing possible."
        * Education: "Investing in education is the best decision! Let me help you secure your family's future."
        * Home renovation: "Making your home more beautiful - excellent choice!"
        * Debt consolidation: "Smart financial move! Let's reduce your overall EMI burden."
   
   e) URGENCY ASSESSMENT:
      - "When would you need the funds, [Name] ji? Is there a specific timeline you're working with?"
      - If urgent: "I understand the urgency. Good news - MUJ Bank can disburse loans within 2 hours of approval!"
      - If not urgent: "Perfect! That gives us time to structure the best possible deal for you."
   
   f) LOAN AMOUNT:
      - "Based on your income of ₹[amount], you're pre-qualified for up to ₹[calculate 20x monthly income]"
      - "How much were you thinking of borrowing?"
      - If hesitant: "Most customers in your income bracket typically go for ₹[suggest appropriate amount]. This keeps EMIs comfortable."
   
   g) TENURE PREFERENCE:
      - "Would you prefer smaller EMIs over a longer period, or would you like to close the loan faster with slightly higher EMIs?"
      - "We offer flexible tenures from 12 to 60 months. What works best for your monthly budget?"

3. Persuasion & Value Proposition Techniques:

   a) SOCIAL PROOF:
      - "Just this month, we've helped over 2,300 customers from your profession get instant loans"
      - "In fact, many employees from [their company] bank with us"
   
   b) EXCLUSIVE BENEFITS POSITIONING:
      - "As a salaried professional with [X] years of experience, you qualify for our Platinum category with preferential rates"
      - "Because of your excellent profile, I can offer you our festive season special rate of just 10.99% - that's 2% lower than market rates"
   
   c) URGENCY CREATION (without being pushy):
      - "This preferential rate is valid till month-end, after which it goes back to standard rates"
      - "I can lock this rate for you right now if you'd like"
   
   d) COMPETITIVE POSITIONING:
      - "Unlike other banks that take 7-10 days, we disburse within hours"
      - "No hidden charges - what I quote is what you pay"
      - "You can prepay anytime without any penalties - that's MUJ Bank's promise"
   
   e) OBJECTION HANDLING:
      - High interest: "Actually, when you calculate the total cost, our processing fee is lowest in industry, saving you ₹15,000-20,000"
      - Need to think: "Of course! Should I send you a personalized quote on WhatsApp that you can review?"
      - Checking with spouse: "Absolutely! Would you like me to explain the benefits to them as well? I'm happy to do a quick conference call"
      - Already have loan: "We offer balance transfer at lower rates. You could save significantly on your existing EMI"

4. Emotional Intelligence & Cultural Sensitivity:
   - Recognize festivals/occasions: "With Diwali coming up, this loan can help with your shopping and preparations"
   - Acknowledge family values: "I understand, family comes first. This loan ensures you never have to compromise on their needs"
   - Show empathy: "These are challenging times, but I'm here to make the financial part easy for you"

5. MUJ Bank Unique Selling Points (MUST highlight):
   - "2-hour disbursal for pre-approved customers"
   - "Lowest processing fee in industry - just 0.5%"
   - "No foreclosure charges after 6 months"
   - "Free insurance coverage up to loan amount"
   - "Dedicated relationship manager (that's me!) for entire loan tenure"
   - "Top-up loans available after 6 EMIs"
   - "Special 0.5% rate discount for women borrowers"

6. Tools to Use (IN ORDER):
   - save_customer_info: Save name, phone, employment details (USE IMMEDIATELY after collecting)
   - check_eligibility: Verify loan eligibility based on income
   - calculate_emi: Show exact EMI calculations
   - generate_sanction_letter: Create instant pre-approval letter
   - send_whatsapp: Send details to customer's WhatsApp
   - schedule_callback: Book follow-up calls if needed

7. Closing Techniques:
   
   SOFT CLOSE (if interested):
   "[Name] ji, based on everything we've discussed, I can get ₹[amount] credited to your account by tomorrow morning. Should I start processing your pre-approved sanction letter?"
   
   ASSUMPTIVE CLOSE (if very interested):
   "Perfect! I'm generating your sanction letter right now. You'll receive it on WhatsApp in 30 seconds. The only thing remaining would be a quick KYC verification."
   
   REFERENCE CLOSE (if hesitant):
   "I completely understand you need time. Meanwhile, many customers find it helpful to have a pre-approved sanction letter handy - it's valid for 30 days and involves no commitment. Should I create one for you?"

8. Voice Modulation Instructions:
   - Speak with enthusiasm when discussing benefits
   - Show empathy when customer mentions problems
   - Use slight pause after stating interest rates for impact
   - Speed up slightly when listing features (shows confidence)
   - Slow down when explaining important terms

9. Must-Ask Compliance Questions:
   - "Are you above 21 years of age?"
   - "Do you have a PAN card available?"
   - "Is your Aadhaar linked to your mobile number?"

10. NEVER DO:
    - Don't sound robotic or scripted
    - Don't interrupt when customer is speaking
    - Don't be pushy if customer says no
    - Don't make false promises
    - Don't share other customers' personal details
    - Don't criticize other banks aggressively

11. Regional Touch Points:
    - Use regional festivals: "Durga Puja", "Onam", "Pongal", "Baisakhi"
    - Reference local context: "Mumbai's housing prices", "Bangalore traffic", "Delhi's winter"
    - Use appropriate language mixing: "Sir, aapka documents ready hai?" (if customer uses Hindi)

12. Success Metrics Focus:
    - Always aim to at least generate a sanction letter (even if not immediate conversion)
    - Collect complete information for follow-up
    - Create urgency without pressure
    - Make customer feel valued regardless of decision

Remember: You are not just offering a loan; you are providing a solution to achieve dreams, solve problems, and improve lives. Every customer should end the call feeling better about their financial situation, whether they take the loan or not. Your success is measured not just by conversion, but by customer happiness and trust in MUJ Bank.

Special Ongoing Offer: Diwali Festival Season - Extra 0.5% discount on interest rates
Your Employee ID: RJ2024MUJ (share if asked for credibility)"""

        )
        

    @function_tool
    async def save_user_info(self, name: str = None, phone: str = None, email: str = None) -> str:
        """Save customer information like name, phone number, or email. Call this immediately when you receive any of this information."""
        try:
            # Validate and format phone number if provided
            if phone:
                # Remove any spaces, dashes, or special characters
                phone = re.sub(r'[^\d+]', '', phone)
                # Ensure it's a valid format
                if not re.match(r'^\+?\d{10,15}$', phone):
                    return "I couldn't save that phone number. Could you please provide a valid 10-digit mobile number?"
            
            db.create_or_update_user(self.user_id, name=name, phone=phone, email=email)
            logger.info(f"Saved user info for {self.user_id}: name={name}, phone={phone}, email={email}")
            
            # Create a friendly response
            response_parts = []
            if name:
                response_parts.append(f"your name as {name}")
            if phone:
                response_parts.append(f"your contact number")
            if email:
                response_parts.append(f"your email")
            
            if response_parts:
                return f"Perfect! I've saved {' and '.join(response_parts)} in our system."
            else:
                return "Information saved successfully."
                
        except Exception as e:
            logger.error(f"Error saving user info: {e}")
            return "I apologize, but I encountered an error saving your information. Could you please repeat that?"

    @function_tool
    async def create_room_booking(
        self, 
        room_type: str,
        check_in_date: str,
        check_out_date: str,
        num_adults: int,
        num_children: int = 0,
        special_requests: str = ""
    ) -> str:
        """
        Create a hotel room booking. Only use this after you have confirmed the guest's name and phone number.
        
        Args:
            room_type: Type of room (Standard, Deluxe, or Presidential Suite)
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format
            num_adults: Number of adults
            num_children: Number of children (default 0)
            special_requests: Any special requests
        """
        try:
            # Verify we have guest information before booking
            user_info = db.get_user(self.user_id)
            if not user_info or not user_info.get('name') or not user_info.get('phone'):
                return "Before I can confirm your booking, I need to collect some information. May I have your name and contact number, please?"
            
            booking_id = db.create_room_booking(
                user_id=self.user_id,
                room_type=room_type,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                num_adults=num_adults,
                num_children=num_children,
                special_requests=special_requests
            )
            
            logger.info(f"Created room booking {booking_id} for user {self.user_id}")
            
            guest_name = user_info.get('name', 'Guest')
            return f"Wonderful, {guest_name}! Your {room_type} room has been confirmed. Your booking ID is {booking_id}. Check-in is on {check_in_date} and check-out is on {check_out_date}. We'll send a confirmation to your registered number. Looking forward to welcoming you!"
            
        except Exception as e:
            logger.error(f"Error creating room booking: {e}")
            return "I apologize, but I encountered an error while processing your booking. Please try again."

    @function_tool
    async def create_restaurant_booking(
        self,
        restaurant_name: str,
        booking_date: str,
        booking_time: str,
        num_guests: int,
        special_requests: str = ""
    ) -> str:
        """
        Create a restaurant table booking. Only use this after you have confirmed the guest's name and phone number.
        
        Args:
            restaurant_name: Name of restaurant (Surahi, Oasis, or The Rooftop Lounge)
            booking_date: Date in YYYY-MM-DD format
            booking_time: Time in HH:MM format (24-hour)
            num_guests: Number of guests
            special_requests: Special requests or dietary restrictions
        """
        try:
            # Verify we have guest information before booking
            user_info = db.get_user(self.user_id)
            if not user_info or not user_info.get('name') or not user_info.get('phone'):
                return "Before I can reserve your table, I need to collect some information. May I have your name and contact number, please?"
            
            booking_id = db.create_restaurant_booking(
                user_id=self.user_id,
                restaurant_name=restaurant_name,
                booking_date=booking_date,
                booking_time=booking_time,
                num_guests=num_guests,
                special_requests=special_requests
            )
            
            logger.info(f"Created restaurant booking {booking_id} for user {self.user_id}")
            
            guest_name = user_info.get('name', 'Guest')
            return f"Perfect, {guest_name}! Your table for {num_guests} at {restaurant_name} is confirmed for {booking_date} at {booking_time}. Your booking ID is {booking_id}. We'll send you a confirmation message. We look forward to serving you!"
            
        except Exception as e:
            logger.error(f"Error creating restaurant booking: {e}")
            return "I apologize, but I encountered an error while making your restaurant reservation. Please try again."

    @function_tool
    async def get_my_bookings(self) -> str:
        """Get all bookings for the current user."""
        try:
            user_info = db.get_user(self.user_id)
            room_bookings = db.get_user_room_bookings(self.user_id)
            restaurant_bookings = db.get_user_restaurant_bookings(self.user_id)
            
            guest_name = user_info.get('name', 'Guest') if user_info else 'Guest'
            result = f"Here are your bookings, {guest_name}:\n\n"
            
            if room_bookings:
                result += "Room Bookings:\n"
                for booking in room_bookings:
                    if booking['status'] == 'confirmed':
                        result += f"- {booking['room_type']} room, {booking['check_in_date']} to {booking['check_out_date']}, Booking ID: {booking['booking_id']}\n"
            
            if restaurant_bookings:
                result += "\nRestaurant Bookings:\n"
                for booking in restaurant_bookings:
                    if booking['status'] == 'confirmed':
                        result += f"- {booking['restaurant_name']}, {booking['booking_date']} at {booking['booking_time']}, {booking['num_guests']} guests, Booking ID: {booking['booking_id']}\n"
            
            if not room_bookings and not restaurant_bookings:
                result = f"{guest_name}, you don't have any bookings with us yet. Would you like to make a reservation?"
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching bookings: {e}")
            return "I apologize, but I encountered an error retrieving your bookings."

def prewarm(proc: JobProcess):
    """Pre-warm models into memory"""
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    """Main entrypoint for the agent"""
    
    # Get user ID from room participant
    await ctx.connect()
    user_id = ctx.room.local_participant.identity
    
    logger.info(f"Starting session for user: {user_id}")
    
    # Create or update user record
    db.create_or_update_user(user_id)
    
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=cartesia.TTS(language="hi", voice="faf0731e-dfb9-4cfc-8119-259a79b27e12"),
        turn_detection=MultilingualModel(),
    )

    # Start the agent session
    agent = MyAgent(user_id=user_id)
    
    # Hook to save conversations - MUST be synchronous functions
    @session.on("agent_speech")
    def on_agent_speech(text: str):
        db.add_conversation(user_id, text, "Agent")
    
    @session.on("user_speech")
    def on_user_speech(text: str):
        db.add_conversation(user_id, text, "User")
    
    await session.start(agent=agent, room=ctx.room)
    
    # Get user info for personalized greeting
    user_info = db.get_user(user_id)
    now = datetime.now()
    current_hour = now.hour

    time_based_greeting = ""
    if 6 <= current_hour < 12:
        time_based_greeting = "Good morning! Namaste, this is Raj Sharma from MUJ Bank. I hope you're having a wonderful day!"
    elif 12 <= current_hour < 17:
        time_based_greeting = "Good afternoon! Namaste, this is Raj Sharma from MUJ Bank. Hope your day is going well!"
    else:
        time_based_greeting = "Good evening! Namaste, this is Raj Sharma from MUJ Bank. Thank you for taking time to speak with me!"

    greeting = ""
    if user_info and user_info.get('name'):
        name = user_info['name']
        greeting = f"{time_based_greeting} It's wonderful to speak with you again, {name} ji. How can I assist you with your financial needs today?"
    else:
        greeting = (f"{time_based_greeting} I'm here to help you with instant personal loan solutions that can "
                    "transform your plans into reality. May I know whom I have the pleasure of speaking with?")
    
    logger.info("🎤 Sending greeting to user...")
    await session.say(greeting, allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            initialize_process_timeout=60.0,
            load_threshold=0.9
        )
    )