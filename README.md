Filoas: Conversational Loan Sales Assistant
An Agentic AI-powered conversational sales assistant built for the EY Problem Statement (#5). This solution simulates a human sales agent to guide customers through the personal loan application process, from initial conversation to instant sanction.

Challenge
To address inefficient and impersonal lead generation for a major NBFC, this project creates an intelligent chatbot that engages customers, verifies KYC, evaluates creditworthiness, and issues instant loan sanction letters, ultimately increasing personal loan conversions.

Features
Conversational Master Agent: Uses natural language to engage customers in human-like sales discussions.

Automated Processing Agents: A team of specialized agents handles:

KYC Verification

Creditworthiness Evaluation (using mock credit score APIs)

Underwriting and eligibility checks

Instant Sanction Generation: Automatically creates and delivers a PDF loan sanction letter upon approval.

Voice & Emotion AI (Bonus): Integrates services like Twilio, Hume AI, Speechify, and LMNT to provide realistic voice interaction and emotion-based persuasion for higher conversion rates.

Web Interface: Includes a web server and admin view for monitoring and interaction.

Tech Stack
Backend: Python

Agent Framework: Custom agent logic (my_agent.py)

Communication: Twilio (twilio_service.py)

Web Server: web_server.py (likely Flask/FastAPI)

Database: database.py

AI/Voice APIs: Hume AI, Speechify, Spitch, LMNT

Getting Started
Clone the repository:

Bash

git clone [your-repo-url]
cd dimension-drifter-filoas/Filoas
Install dependencies:

Bash

pip install -r requirements.txt
Set up environment variables:

Create a .env file and add your API keys (Twilio, Hume, Speechify, etc.).

Run the application:

Bash

python web_server.py
