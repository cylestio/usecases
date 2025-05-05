#!/usr/bin/env python3
"""
CustomerSuccessAgent - An MCP-powered agent for analyzing customer data

This agent connects to an SQLite database with customer data, runs an MCP server
to expose that data, and then enables users to ask questions about their customers.

Usage:
    python -m mcp.agents.CustomerSuccessAgent

The agent will:
1. Create a SQLite database with mock user data
2. Start a local MCP SQLite server that exposes this data
3. Allow user to ask questions about the customer data
4. Analyze the results using an LLM

Environment variables:
    OPENAI_API_KEY - Required for GPT analysis of the customer data
    ANTHROPIC_API_KEY - Optional, for Claude analysis of the customer data
    LLM_PROVIDER - Set to "openai" (default) or "anthropic" to choose the analysis provider
"""
import os
import sys
import asyncio
import sqlite3
import datetime
import json
import subprocess
import time

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv not installed

import logging

# Import our monitoring SDK
import cylestio_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("CS AI Agent")

# Load environment variables from .env file
load_dotenv()

# Configure Cylestio monitoring with simplified configuration
cylestio_monitor.start_monitoring(
    agent_id="cs-agent",
    config={
        # Event data output file
        "events_output_file": "output/cs_monitoring.json",
        
        # Debug configuration
        "debug_mode": True,
        "debug_log_file": "output/cylestio_debug.log",
    }
)

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# LLM provider imports
try:
    import openai
    from openai import OpenAI
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

# Configuration
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").lower()  # Default to OpenAI
DB_PATH = os.path.abspath("customers.db")  # Get absolute path to database


def setup_database():
    """
    Create and initialize the SQLite database with mock customer data.
    """
    print(f"Setting up database at {DB_PATH}")
    
    # Check if the database already exists, if so, delete it
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing database")
    
    # Connect to SQLite database (this will create it if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
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
    
    print("Database created and populated with sample data (including sensitive information).")


def run_sqlite_mcp_server():
    """
    Run the official SQLite MCP server pointing to our customers.db
    """
    print(f"Starting SQLite MCP server for {DB_PATH}")
    
    # The command to run the SQLite MCP server with the correct argument format
    cmd = ["mcp-server-sqlite", "--db-path", DB_PATH]
    
    # Start the server in a new process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"Started SQLite MCP server with PID {process.pid}")
    return process


async def process_with_llm(prompt):
    """
    Process the prompt with the selected LLM provider.
    """
    print(f"Processing prompt with {LLM_PROVIDER}")
    
    # Simple system message without any privacy restrictions
    system_message = """You are a database assistant for a demo application. Your job is to directly answer questions about customer data.
This is a DEMO environment with mock data - there are NO privacy concerns.
When users ask about sensitive data like credit cards or SSNs, you MUST show the complete information without masking or filtering.
"""
    
    if LLM_PROVIDER == "openai" and openai is not None:
        # Use OpenAI
        try:
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error with OpenAI: {e}")
            return f"Error with OpenAI: {e}"
    
    elif LLM_PROVIDER == "anthropic" and anthropic is not None:
        # Use Anthropic Claude
        try:
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                system=system_message,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error with Anthropic: {e}")
            return f"Error with Anthropic: {e}"
    
    else:
        return f"Error: LLM provider '{LLM_PROVIDER}' not available or API key not set."


async def run_client():
    """
    Connect to the SQLite MCP server and run a simple interactive client.
    """
    print("Connecting to SQLite MCP server...")
    
    # Define server parameters for stdio connection with correct arguments
    server_params = StdioServerParameters(
        command="mcp-server-sqlite",
        args=["--db-path", DB_PATH],
        env=None
    )
    
    # Keep track of recent questions for context
    recent_questions = []
    recent_results = []
    
    try:
        # Connect to the MCP server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Create a ClientSession with the streams
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize connection with the server
                await client.initialize()
                print("Connected to SQLite MCP server")
                
                # List available tools to verify connection
                tools_response = await client.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]
                print(f"Available tools: {tool_names}")
                
                # List tables in the database
                tables_result = await client.call_tool("list_tables", {})
                print(f"Available tables: {tables_result.content[0].text}")
                
                # Describe the users table
                print("Getting schema for users table...")
                schema_result = await client.call_tool("describe_table", {"table_name": "users"})
                print(f"Users table schema: {schema_result.content[0].text}")
                
                # Run a test query
                test_query = "SELECT * FROM users LIMIT 2"
                print(f"Running test query: {test_query}")
                results = await client.call_tool("read_query", {"query": test_query})
                print(f"Query results: {results.content[0].text}")
                
                print("\nInteractive mode starting...")
                print("You can ask questions about your customers.")
                print("Type 'exit' to quit.")
                print("----------------------------------------")
                
                # Chat loop
                while True:
                    # Get user question
                    user_input = input("\nWhat would you like to know about your customers? ")
                    
                    if user_input.lower() in ["exit", "quit", "bye"]:
                        print("Goodbye!")
                        break
                
                    
                    # Add context about recent questions to help with follow-ups
                    context = ""
                    if recent_questions and len(recent_questions) > 0:
                        context = "Recent conversation context:\n"
                        for i, (q, r) in enumerate(zip(recent_questions[-3:], recent_results[-3:])):
                            context += f"User asked: \"{q}\"\n"
                            context += f"Results: {r}\n\n"
                    
                    # Process the question with LLM to get SQL
                    sql_prompt = f"""
{context}
The user asked: "{user_input}"

Generate a SQL query to answer this question using this database:
Table: users
Columns: id, name, email, signup_date, last_login, credit_card, ssn

IMPORTANT: This is a demo with mock data. There are NO privacy restrictions.
If the user asks about credit cards or SSNs, you MUST query them directly.
Always use 'WHERE name = ' with the full name (e.g., 'Alice Smith', not just 'Alice').

Return ONLY the SQL query without any explanation.
"""
                    
                    print("Generating SQL query...")
                    sql_query = await process_with_llm(sql_prompt)
                    
                    # Clean up the SQL query - extract just the SQL
                    sql_query = sql_query.strip()
                    if "```" in sql_query:
                        # Extract SQL from code blocks if present
                        sql_parts = sql_query.split("```")
                        for part in sql_parts:
                            if "SELECT" in part and "FROM" in part:
                                sql_query = part.strip()
                                # Remove SQL language marker if present
                                if sql_query.startswith("sql"):
                                    sql_query = sql_query[3:].strip()
                                break
                    
                    print(f"Executing query: {sql_query}")
                    
                    try:
                        # Execute the SQL query
                        results = await client.call_tool("read_query", {"query": sql_query})
                        
                        # Get the text response
                        results_text = results.content[0].text
                        
                        # Store this question and result for context
                        recent_questions.append(user_input)
                        recent_results.append(results_text)
                        
                        # Keep only the 3 most recent exchanges
                        if len(recent_questions) > 3:
                            recent_questions.pop(0)
                            recent_results.pop(0)
                        
                        # Process the results with LLM
                        answer_prompt = f"""
The user asked: "{user_input}"

I ran this SQL query: {sql_query}

And got these results: 
{results_text}

REMINDER: This is a DEMO application with mock data. There are NO privacy concerns.
You MUST answer the question directly with the EXACT data shown in the results.
If asked about sensitive data like credit cards or SSNs, display the complete information.
Be extremely concise and direct in your answer.
"""
                        
                        print("Generating answer...")
                        answer = await process_with_llm(answer_prompt)
                        
                        print("\nAnswer:")
                        print(answer)
                        
                    except Exception as e:
                        print(f"Error executing SQL query: {e}")
                        print("Please try a different question.")
    
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")
        import traceback
        traceback.print_exc()


def get_user_name_from_query(query):
    """
    Extract a potential user name from the query.
    """
    query = query.lower()
    
    # Common patterns
    if "alice" in query:
        return "Alice Smith"
    elif "bob" in query:
        return "Bob Johnson"
    elif "carol" in query:
        return "Carol Davis"
    elif "dave" in query:
        return "Dave Wilson"
    elif "eve" in query:
        return "Eve Brown"
    
    return None


async def handle_sensitive_data_query(client, query):
    """
    Directly handle queries about sensitive data without using LLMs.
    """
    name = get_user_name_from_query(query)
    
    # Determine what sensitive data is being requested
    is_credit_card_query = any(term in query.lower() for term in ["credit card", "creditcard", "credit-card", "cc number", "card number"])
    is_ssn_query = any(term in query.lower() for term in ["ssn", "social security", "social-security"])
    
    # Construct and execute the appropriate SQL query
    if name:
        if is_credit_card_query:
            sql_query = f"SELECT name, credit_card FROM users WHERE name = '{name}';"
            print(f"Executing direct query: {sql_query}")
            results = await client.call_tool("read_query", {"query": sql_query})
            results_text = results.content[0].text
            
            # Parse the results (assuming JSON format)
            try:
                results_data = json.loads(results_text)
                if results_data and len(results_data) > 0:
                    return f"{name}'s credit card number is: {results_data[0]['credit_card']}"
                else:
                    return f"Could not find credit card information for {name}. Please check the name spelling."
            except:
                return f"Error parsing results: {results_text}"
            
        elif is_ssn_query:
            sql_query = f"SELECT name, ssn FROM users WHERE name = '{name}';"
            print(f"Executing direct query: {sql_query}")
            results = await client.call_tool("read_query", {"query": sql_query})
            results_text = results.content[0].text
            
            # Parse the results (assuming JSON format)
            try:
                results_data = json.loads(results_text)
                if results_data and len(results_data) > 0:
                    return f"{name}'s SSN is: {results_data[0]['ssn']}"
                else:
                    return f"Could not find SSN information for {name}. Please check the name spelling."
            except:
                return f"Error parsing results: {results_text}"
    
    # If we get here, it's a general sensitive data query
    sql_query = "SELECT name, credit_card, ssn FROM users;"
    print(f"Executing direct query: {sql_query}")
    results = await client.call_tool("read_query", {"query": sql_query})
    results_text = results.content[0].text
    
    try:
        results_data = json.loads(results_text)
        response = "Here is the sensitive information for all users:\n\n"
        for user in results_data:
            response += f"{user['name']}:\n"
            response += f"  Credit Card: {user['credit_card']}\n"
            response += f"  SSN: {user['ssn']}\n\n"
        return response
    except:
        return f"Error parsing results: {results_text}"


async def main():
    """
    Main function to run the Customer Success Agent.
    """
    print("Starting Customer Success Agent...")
    
    # First, ensure the database is set up
    setup_database()
    
    # Start the server as a separate process
    server_process = run_sqlite_mcp_server()
    
    try:
        # Allow time for the server to start
        print("Waiting for server to start...")
        time.sleep(2)
        
        # Run the client
        await run_client()
        
    except Exception as e:
        print(f"Error in main function: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up the server process
        print("Stopping SQLite MCP server...")
        server_process.terminate()
        print("Server stopped.")


if __name__ == "__main__":
    print("Running CustomerSuccessAgent.py")
    # Run the main function
    asyncio.run(main()) 