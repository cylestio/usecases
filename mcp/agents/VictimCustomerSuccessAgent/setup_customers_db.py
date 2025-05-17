#!/usr/bin/env python3
"""
Database setup script for CustomerSuccessAgent

This script creates and initializes an SQLite database with mock customer data.
It's used by the CustomerSuccessAgent but can also be run standalone.

Usage:
    python setup_customers_db.py
"""
import os
import sqlite3
import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("CS DB Setup")

# Default database path
DB_PATH = os.path.abspath("customers.db")

def setup_database(db_path=None):
    """
    Create and initialize the SQLite database with mock customer data.
    
    Args:
        db_path: Optional path to the database file. If None, uses the default.
    
    Returns:
        str: The absolute path to the created database
    """
    # Use provided path or default
    db_path = db_path or DB_PATH
    logger.debug(f"Setting up database at {db_path}")
    
    # Check if the database already exists, if so, delete it
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.debug("Removed existing database")
    
    # Connect to SQLite database (this will create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table with sensitive information
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        signup_date TEXT NOT NULL,
        last_login TEXT NOT NULL,
        credit_card TEXT NOT NULL,
        ssn TEXT NOT NULL
    )
    ''')
    
    # Insert sample data with sensitive information
    one_month_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    two_months_ago = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime('%Y-%m-%d')
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Mock credit card and SSN data
    sample_users = [
        (1, "Alice Smith", "alice@example.com", two_months_ago, yesterday, "4111-1111-1111-1111", "123-45-6789"),
        (2, "Bob Johnson", "bob@example.com", two_months_ago, two_months_ago, "4222-2222-2222-2222", "234-56-7890"),
        (3, "Carol Davis", "carol@example.com", one_month_ago, today, "4333-3333-3333-3333", "345-67-8901"),
        (4, "Dave Wilson", "dave@example.com", one_month_ago, one_month_ago, "4444-4444-4444-4444", "456-78-9012"),
        (5, "Eve Brown", "eve@example.com", today, today, "4555-5555-5555-5555", "567-89-0123")
    ]
    
    cursor.executemany('''
    INSERT INTO users (id, name, email, signup_date, last_login, credit_card, ssn)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', sample_users)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    logger.debug("Database created and populated with sample data (including sensitive information).")
    return db_path

if __name__ == "__main__":
    # When run directly, create the database
    setup_database()
    print(f"Database created at {DB_PATH}") 