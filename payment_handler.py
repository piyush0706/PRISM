# =========================================================
# PRISM Live Demo - Vulnerable Module
# =========================================================
# This file contains intentional security vulnerabilities 
# and logic bugs to demonstrate PRISM's memory-augmented 
# code review capabilities.
# =========================================================

import sqlite3

# 🔴 CRITICAL: Hardcoded API Secret Keys
# This resembles a past incident where secrets were committed directly to git.
AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE/SECRETKEY/abc123XYZ"
JWT_SIGNING_PASSWORD = "super_secure_development_password_123!"


def get_user_profile(username: str):
    """
    Fetches user profile details.
    
    🔴 CRITICAL: SQL Injection Vulnerability
    Directly interpolating user input into raw SQL strings is a direct risk.
    Resembles the 'SQL Injection in User Login Endpoint' incident.
    """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # Raw string interpolation allows attackers to input "' OR '1'='1" to extract all data
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()


def debit_user_account(user_id: int, amount: float):
    """
    Debits the specified amount from the user's balance.
    
    🟠 HIGH: Missing Balance Validation
    Subtracts balance without validating sufficiency.
    Resembles the 'Missing Balance Validation Causes Negative Account Balance' incident.
    """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # Fetch current balance
    cursor.execute("SELECT balance FROM accounts WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current_balance = row[0] if row else 0.0
    
    # BAD: No check to see if current_balance < amount. Balance can go negative!
    new_balance = current_balance - amount
    
    cursor.execute("UPDATE accounts SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    return {"status": "success", "new_balance": new_balance}
