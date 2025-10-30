import sqlite3
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LoanDatabase:
    def __init__(self, db_name='loan_assistant.db'):
        self.db_name = db_name
        self.create_tables()

    def get_connection(self):
        """Creates a database connection."""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self):
        """Create the necessary tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create a table for loan leads
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                name TEXT,
                phone TEXT,
                loan_amount REAL,
                loan_tenure_months INTEGER,
                loan_purpose TEXT,
                transcript TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_interaction DATETIME
            )
        """)
        
        # Create a table for conversation history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                speaker TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES loan_leads (user_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logging.info("Database tables 'loan_leads' and 'conversations' are ready.")

    def get_lead(self, user_id: str):
        """Get lead information for a given user_id."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM loan_leads WHERE user_id = ?", (user_id,))
        lead = cursor.fetchone()
        conn.close()
        return dict(lead) if lead else None

    def create_or_update_lead(self, user_id: str, name: str = None, phone: str = None, loan_amount: float = None, loan_tenure: int = None, loan_purpose: str = None):
        """Create a new lead or update an existing one."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        
        cursor.execute("SELECT id FROM loan_leads WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing lead
            query = "UPDATE loan_leads SET last_interaction = ?"
            params = [now]
            if name:
                query += ", name = ?"
                params.append(name)
            if phone:
                query += ", phone = ?"
                params.append(phone)
            if loan_amount:
                query += ", loan_amount = ?"
                params.append(loan_amount)
            if loan_tenure:
                query += ", loan_tenure_months = ?"
                params.append(loan_tenure)
            if loan_purpose:
                query += ", loan_purpose = ?"
                params.append(loan_purpose)
            
            query += " WHERE user_id = ?"
            params.append(user_id)
            
            cursor.execute(query, tuple(params))
            logging.info(f"Updated lead for user_id: {user_id}")
        else:
            # Create new lead
            cursor.execute(
                "INSERT INTO loan_leads (user_id, name, phone, loan_amount, loan_tenure_months, loan_purpose, last_interaction) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, name, phone, loan_amount, loan_tenure, loan_purpose, now)
            )
            logging.info(f"Created new lead for user_id: {user_id}")
            
        conn.commit()
        conn.close()

    def add_conversation(self, user_id: str, message: str, speaker: str):
        """Add a message to the conversation history."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (user_id, message, speaker) VALUES (?, ?, ?)",
            (user_id, message, speaker)
        )
        conn.commit()
        conn.close()

    def get_conversation_history(self, user_id: str, limit: int = 10):
        """Retrieve the recent conversation history for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT speaker, message FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        history = cursor.fetchall()
        conn.close()
        # Return in chronological order
        return [dict(row) for row in reversed(history)]

    def save_final_transcript(self, user_id: str):
        """Fetches all conversation for a user and saves it as a JSON object in the transcript column."""
        history = self.get_conversation_history(user_id, limit=1000) # Get full history
        if not history:
            return

        # Standardize speaker names for the final transcript
        formatted_history = []
        for line in history:
            speaker = "Loan assistant" if line['speaker'].lower() == 'agent' else 'User'
            formatted_history.append({'speaker': speaker, 'message': line['message']})

        transcript_json = json.dumps(formatted_history, indent=2)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE loan_leads SET transcript = ? WHERE user_id = ?",
            (transcript_json, user_id)
        )
        conn.commit()
        conn.close()
        logging.info(f"Saved final transcript for user_id: {user_id}")