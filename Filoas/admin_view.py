from flask import Flask, render_template, jsonify
from database import LoanDatabase
import logging
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

db = LoanDatabase()

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard to view all loan leads"""
    return render_template('admin.html')

@app.route('/admin/api/leads')
def get_all_leads():
    """API endpoint to get all loan lead data"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, user_id, name, phone, loan_amount, loan_tenure_months, loan_purpose, transcript, last_interaction
        FROM loan_leads
        ORDER BY last_interaction DESC
    """)
    leads_rows = cursor.fetchall()
    conn.close()
    
    leads_data = []
    for row in leads_rows:
        transcript_data = None
        try:
            if row['transcript']:
                transcript_data = json.loads(row['transcript'])
        except json.JSONDecodeError:
            transcript_data = "Error decoding transcript."

        leads_data.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'name': row['name'] or 'Not provided',
            'phone': row['phone'] or 'Not provided',
            'loan_amount': f"₹{row['loan_amount']:,.0f}" if row['loan_amount'] else 'N/A',
            'loan_tenure_months': f"{row['loan_tenure_months']} months" if row['loan_tenure_months'] else 'N/A',
            'loan_purpose': row['loan_purpose'] or 'N/A',
            'transcript': transcript_data,
            'last_interaction': row['last_interaction']
        })

    return jsonify(leads=leads_data)

if __name__ == '__main__':
    print("🎯 Admin Dashboard starting on http://localhost:5001/admin")
    app.run(debug=True, port=5001, host='0.0.0.0')