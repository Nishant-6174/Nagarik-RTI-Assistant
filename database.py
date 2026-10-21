import sqlite3
import uuid
from datetime import datetime

DB_NAME = "rti_database.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                stable_id TEXT PRIMARY KEY,
                info_needed TEXT,
                department TEXT,
                state TEXT,
                
                llm_category TEXT,       
                mapped_authority TEXT,
                drafted_text TEXT,
                decision_reason TEXT,    
                
                target_url TEXT,
                status TEXT,             
                
                actual_registration_number TEXT,
                response_deadline TEXT,
                execution_timestamp TEXT
            )
        """)

def save_initial_input(info: str, dept: str, state: str) -> str:
    stable_id = f"RTI-{uuid.uuid4().hex[:6].upper()}"
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO requests (stable_id, info_needed, department, state, status)
            VALUES (?, ?, ?, ?, ?)
        """, (stable_id, info, dept, state, "Input_Collected"))
    return stable_id

def update_decision(stable_id: str, category: str, authority: str, draft: str, reason: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            UPDATE requests 
            SET llm_category = ?, mapped_authority = ?, drafted_text = ?, decision_reason = ?, status = 'Pending_Approval'
            WHERE stable_id = ?
        """, (category, authority, draft, reason, stable_id))

def get_request(stable_id: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        return dict(conn.execute("SELECT * FROM requests WHERE stable_id = ?", (stable_id,)).fetchone())

def update_final_result(stable_id: str, reg_number: str, deadline: str, target_url: str):
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            UPDATE requests 
            SET actual_registration_number = ?, response_deadline = ?, execution_timestamp = ?, target_url = ?, status = 'Filed'
            WHERE stable_id = ?
        """, (reg_number, deadline, timestamp, target_url, stable_id))