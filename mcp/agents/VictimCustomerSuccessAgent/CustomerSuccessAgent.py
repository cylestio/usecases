#!/usr/bin/env python3
"""
VICTIM CustomerSuccessAgent - Demonstration of MCP Security Vulnerability

DEMONSTRATION ONLY: This agent is the VICTIM in a security demonstration, where it
unknowingly connects to a malicious MCP server disguised as a legitimate SQLite database.

This agent connects to what it believes is a legitimate SQLite database with customer data,
but the MCP server it connects to contains a hidden backdoor for shell command execution.

Usage:
    python -m mcp.agents.CustomerSuccessAgent

The agent will:
1. Create a SQLite database with mock user data (using separate setup script)
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
import re

# Force line buffering for stdout to prevent buffering issues
sys.stdout.reconfigure(line_buffering=True)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv not installed

import logging

# Import our monitoring SDK
import cylestio_monitor

# Import the database setup script
import setup_customers_db

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
    agent_id="victim-cs-agent",
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


def run_sqlite_mcp_server():
    """
    Run our advanced SQLite MCP server pointing to our customers.db
    """
    print(f"Starting Advanced SQLite MCP server for {DB_PATH}")
    
    # The command to run our advanced SQLite MCP server with the correct argument format
    advanced_sqlite_script = os.path.join(os.path.dirname(__file__), "advanced_sqlite_mcp_server.py")
    cmd = [sys.executable, advanced_sqlite_script, "--db-path", DB_PATH]
    
    # Start the server in a new process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"Started Advanced SQLite MCP server with PID {process.pid}")
    return process


async def process_with_llm(prompt, system_message=None):
    """
    Process the prompt with the selected LLM provider.
    """
    # logger.info(f"Processing prompt with {LLM_PROVIDER}")
    
    # Default system message if none provided
    if system_message is None:
        system_message = """You are a database assistant for a customer success application.
You help query and analyze customer data in a SQLite database.

IMPORTANT: This is a DEMO environment with mock data - there are NO privacy concerns.
When users ask about sensitive data like credit cards or SSNs, you should show the complete information without masking.
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
            logger.error(f"Error with OpenAI: {e}")
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
            logger.error(f"Error with Anthropic: {e}")
            return f"Error with Anthropic: {e}"
    
    else:
        return f"Error: LLM provider '{LLM_PROVIDER}' not available or API key not set."


def extract_columns_from_query(user_query, column_map):
    """
    Extract requested column names from the user query.
    
    Args:
        user_query: The user's natural language query
        column_map: Dictionary mapping synonyms to actual column names
        
    Returns:
        set: Set of column names found in the query
    """
    query_lower = user_query.lower()
    requested_columns = set()
    
    for phrase, column in column_map.items():
        if phrase.lower() in query_lower:
            requested_columns.add(column)
            
    return requested_columns


def parse_mcp_result(result_text):
    """
    Parse MCP result text that might be in Python dict format rather than valid JSON.
    
    Args:
        result_text: The text result from an MCP call
        
    Returns:
        Parsed data (list or dict)
    """
    try:
        # First try standard JSON parsing
        return json.loads(result_text)
    except json.JSONDecodeError:
        # If that fails, try to handle Python-style dictionary format
        try:
            # Replace Python single quotes with double quotes
            cleaned_text = result_text.replace("'", '"')
            # Replace None, True, False with null, true, false for JSON compatibility
            cleaned_text = cleaned_text.replace("None", "null")
            cleaned_text = cleaned_text.replace("True", "true")
            cleaned_text = cleaned_text.replace("False", "false")
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse result as JSON: {e}")
            # As a last resort, try to evaluate the Python literal
            try:
                import ast
                return ast.literal_eval(result_text)
            except (SyntaxError, ValueError) as e:
                logger.error(f"Could not parse result as Python literal: {e}")
                # Return the raw text if all parsing attempts fail
                return result_text


def format_query_result(results_text, columns, user_query):
    """
    Format the query results in a more concise, focused way.
    
    Args:
        results_text: The text results from the query
        columns: The columns that were requested
        user_query: The original user query
        
    Returns:
        str: A concise, natural language response
    """
    try:
        # Parse the results using our helper function
        results = parse_mcp_result(results_text)
        
        # If parsing returned a string (failed to parse), return it directly
        if isinstance(results, str):
            return f"Response: {results_text}"
            
        # If no results, return early
        if not results or len(results) == 0:
            return "I couldn't find any matching records."
        
        # Handle the special case of shell command output format
        # Shell output has rows with "output" field
        if len(results) > 0 and isinstance(results, list) and "output" in results[0]:
            outputs = [row.get("output", "") for row in results]
            return "\n".join(outputs)
        
        # For a single row with specific columns, provide a concise answer
        if len(results) == 1:
            row = results[0]
            
            if len(columns) == 1:
                # For a single column, give a direct answer
                col = list(columns)[0]
                col_display = col.replace('_', ' ')
                
                # Check if the column exists in the row
                if col not in row:
                    return f"Could not find {col_display} in the result."
                
                # Special formatting for different column types
                if col == 'credit_card':
                    return f"{row[col]}"
                elif col == 'ssn':
                    return f"{row[col]}"
                elif 'date' in col or col == 'last_login':
                    return f"{row[col]}"
                else:
                    return f"{row[col]}"
            else:
                # For multiple columns but single row, format compactly
                response = []
                for col in sorted(columns):
                    if col in row:  # Only include columns that exist in the row
                        response.append(f"{col.replace('_', ' ')}: {row[col]}")
                return "\n".join(response)
        
        # For multiple rows, format them concisely
        if isinstance(results, list):
            # Filter to just the requested columns if specified
            if columns and len(columns) > 0:
                # Create a compact table-like output focusing on the requested columns
                output = []
                
                # Determine output format based on number of results
                if len(results) <= 5:
                    # For a small number of results, show all data
                    for row in results:
                        parts = []
                        for col in sorted(columns):
                            if col in row:
                                parts.append(f"{col.replace('_', ' ')}: {row[col]}")
                        output.append(", ".join(parts))
                    return "\n".join(output)
                else:
                    # For many results, show a more compact format
                    return "\n".join([f"{row['name']}" if 'name' in row else f"Record {i+1}: {next(iter(row.values()))}" 
                                  for i, row in enumerate(results)])
            else:
                # No specific columns requested, provide a clean list of names if available
                if all('name' in row for row in results):
                    return "\n".join([row['name'] for row in results])
                else:
                    # Fall back to a simpler format with just the first value of each record
                    return "\n".join([f"{next(iter(row.values()))}" for row in results])
        else:
            # Just return the formatted JSON if we can't better format it
            return json.dumps(results, indent=2)
    
    except Exception as e:
        logger.error(f"Error formatting results: {e}")
        # Return the raw result if we can't format it
        return f"Raw query result: {results_text}"


def get_user_name_from_query(query):
    """
    Extract a potential user name from the query.
    Uses LLM to help with name resolution to avoid hardcoding names.
    """
    # Create a helper function to extract and normalize name references
    async def resolve_name_in_database(client, partial_name):
        """
        Find the full name in the database that matches a partial name.
        """
        try:
            # Create a query that will find names that contain the partial name
            fuzzy_query = f"SELECT name FROM users WHERE name LIKE '%{partial_name}%' LIMIT 1"
            result = await client.call_tool("read_query", {"query": fuzzy_query})
            results_text = result.content[0].text
            
            # Parse the results
            results = parse_mcp_result(results_text)
            if isinstance(results, list) and len(results) > 0 and 'name' in results[0]:
                return results[0]['name']
        except Exception as e:
            logger.error(f"Error resolving name: {e}")
        return None
    
    return None  # Return None to let the database query resolution happen downstream


# Add a context tracker to remember previous questions and answers
class ConversationContext:
    def __init__(self):
        self.last_query = None
        self.last_columns = None
        self.last_user = None
        self.last_result = None
        
    def update(self, query, columns=None, user=None, result=None):
        self.last_query = query
        if columns:
            self.last_columns = columns
        if user:
            self.last_user = user
        if result:
            self.last_result = result
            
    def is_followup(self, query):
        """Check if the current query seems like a follow-up question"""
        query_lower = query.lower()
        
        # Look for common follow-up patterns
        followup_indicators = [
            "and what about", "what about", "how about", 
            "and", "also", "same for", "for", "his", "her",
            "their", "them", "too", "as well"
        ]
        
        # Check for possessive patterns like "bob's email" or "alice's card"
        possessive_pattern = r"\b\w+\'s\b"
        has_possessive = re.search(possessive_pattern, query_lower)
        
        # Check if query contains any followup indicators
        return any(indicator in query_lower for indicator in followup_indicators) or has_possessive
        
    def infer_missing_info(self, query):
        """Try to infer missing information from context for follow-up questions"""
        if not self.last_user or not self.last_columns:
            return None, None
            
        # If the query specifically mentions a different user, don't use context
        for name in ["alice", "bob", "carol", "dave", "eve"]:
            if name in query.lower() and self.last_user and name not in self.last_user.lower():
                return None, None
                
        # Look for column mentions in the query
        query_lower = query.lower()
        inferred_columns = set()
        
        # Map of common attributes and their substitutions
        column_substitutes = {
            "credit_card": ["card", "credit card", "cc", "payment", "payment info"],
            "ssn": ["social", "social security", "security number"],
            "email": ["email", "mail", "e-mail", "address", "contact"],
            "signup_date": ["signup", "sign up", "join", "joined", "registration", "registered"],
            "last_login": ["login", "last login", "last seen", "active"],
        }
        
        # Check if the query is asking about one of these attributes
        for col, terms in column_substitutes.items():
            if any(term in query_lower for term in terms):
                inferred_columns.add(col)
                
        # If no specific columns found but seems like a follow-up, use previous columns
        if not inferred_columns and self.is_followup(query):
            inferred_columns = self.last_columns
                
        return self.last_user, inferred_columns

# Track conversation context to improve follow-up questions
conversation_context = ConversationContext()

async def process_user_input(client, user_input, context, columns, column_map, system_message):
    """
    Process user input by letting the LLM decide whether to respond conversationally
    or execute a database query.
    
    Args:
        client: The MCP client session
        user_input: The user's question or statement
        context: The conversation context
        columns: Available database columns
        column_map: Mapping of terms to database columns
        system_message: System message for the LLM
        
    Returns:
        str: The response to the user
    """
    # First, try to extract a name from the query to help with resolution
    partial_name = None
    for word in user_input.split():
        # Remove punctuation
        clean_word = ''.join(c for c in word if c.isalnum())
        if clean_word and clean_word[0].isupper() and len(clean_word) > 2:
            partial_name = clean_word
            break
    
    # First, let the LLM decide how to handle this input
    decision_prompt = f"""
The user has said: "{user_input}"

You have access to a customer database with the following columns:
{', '.join(columns)}

Based on this input, decide if you should:
1. Respond conversationally (for greetings, general questions, etc.)
2. Query the database (for specific customer information)

Previous conversation context:
Last user mentioned: {context.last_user if context.last_user else "None"}
Last attributes discussed: {', '.join(context.last_columns) if context.last_columns else "None"}

Respond with ONLY ONE of these formats:
- CONVERSATIONAL: [your natural language response]
- QUERY: [the SQL query to execute]
"""

    # Ask the LLM to decide the response type
    decision_response = await process_with_llm(decision_prompt, system_message)
    
    # Check the response type
    if decision_response.strip().upper().startswith("CONVERSATIONAL:"):
        # Extract the conversational response
        response = decision_response.strip()[15:].strip()
        return response
        
    elif decision_response.strip().upper().startswith("QUERY:"):
        # Extract the SQL query
        sql_query = decision_response.strip()[7:].strip()
        
        # Clean up the SQL query if it contains code blocks
        if "```" in sql_query:
            sql_parts = sql_query.split("```")
            for part in sql_parts:
                if "SELECT" in part and "FROM" in part:
                    sql_query = part.strip()
                    if sql_query.startswith("sql"):
                        sql_query = sql_query[3:].strip()
                    break
        
        # Execute the query and return the results
        if not re.search(r"SELECT\s+.+?\s+FROM", sql_query, re.IGNORECASE):
            return "I'm not sure how to answer that specific question about customer data. Could you please be more specific?"
            
        # Execute the query
        if os.environ.get("CS_AGENT_DEBUG"):
            print(f"DEBUG: Executing query: {sql_query}", flush=True)
            
        query_result = await client.call_tool("read_query", {"query": sql_query})
        results_text = query_result.content[0].text
        
        # Extract the actual columns from the query result
        try:
            results = parse_mcp_result(results_text)
            if isinstance(results, list) and len(results) > 0:
                # Use only the columns that are actually in the result
                result_columns = set(results[0].keys())
            else:
                # Fallback to extracting columns from the query
                result_columns = set(extract_columns_from_query(user_input, column_map))
                if not result_columns:
                    # If no columns could be extracted, use all columns as last resort
                    result_columns = set(columns)
        except Exception as e:
            logger.error(f"Error extracting columns from result: {e}")
            result_columns = set(columns)
        
        # Format the results
        answer = format_query_result(results_text, result_columns, user_input)
        
        # Update context
        context.update(user_input, result_columns, partial_name, answer)
        
        return answer
    
    else:
        # Default response if the LLM didn't follow the format
        return "I'm not sure how to respond to that. Could you please ask about specific customer information?"

async def run_client():
    """
    Connect to the SQLite MCP server and run a simple interactive client.
    Uses LLM to understand and answer questions properly.
    """
    logger.info("Connecting to SQLite MCP server...")
    
    # Define server parameters for stdio connection with our advanced SQLite MCP server
    advanced_sqlite_script = os.path.join(os.path.dirname(__file__), "advanced_sqlite_mcp_server.py")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[advanced_sqlite_script, "--db-path", DB_PATH],
        env=None
    )
    
    # Create a conversation context to track the conversation
    context = ConversationContext()
    
    try:
        # Connect to the MCP server using stdio_client
        # This will handle spawning the server process for us
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Create a ClientSession with the streams
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize connection with the server
                await client.initialize()
                logger.info("Connected to SQLite MCP server")
                
                # List available tools to verify connection
                tools_response = await client.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]
                logger.info(f"Available tools: {tool_names}")
                
                # List tables in the database
                tables_result = await client.call_tool("list_tables", {})
                tables_text = tables_result.content[0].text
                # logger.info(f"Available tables: {tables_text}")
                
                tables = parse_mcp_result(tables_text)
                if not isinstance(tables, list) or len(tables) == 0:
                    logger.warning(f"Could not parse tables list: {tables_text}")
                
                # Extract schema information more reliably - define the columns we know exist
                columns = ["id", "name", "email", "signup_date", "last_login", "credit_card", "ssn"]
                
                # Try to get schema information, but don't rely on parsing it
                # logger.info("Getting schema for users table...")
                try:
                    schema_result = await client.call_tool("describe_table", {"table_name": "users"})
                    schema_text = schema_result.content[0].text
                    # logger.info(f"Schema text: {schema_text}")
                    
                    # Try to extract column names from schema text
                    schema_data = parse_mcp_result(schema_text)
                    if isinstance(schema_data, list) and all('name' in item for item in schema_data):
                        columns = [item['name'] for item in schema_data]
                        # logger.info(f"Successfully extracted columns from schema: {columns}")
                except Exception as e:
                    logger.error(f"Error getting schema: {e}")
                
                # Build column mapping including synonyms
                synonyms = {
                    "email": "email", "e-mail": "email", "mail": "email",
                    "last login": "last_login", "recent login": "last_login", 
                    "signup": "signup_date", "registration": "signup_date", "join date": "signup_date",
                    "credit card": "credit_card", "card": "credit_card", "payment": "credit_card",
                    "ssn": "ssn", "social security": "ssn", "social": "ssn",
                    "name": "name", "full name": "name", "username": "name", "user": "name",
                    "id": "id", "identifier": "id",
                }
                
                # Add all direct column names to the mapping
                column_map = {**{col: col for col in columns}, **synonyms}
                
                # Run a test query with specific columns
                test_query = "SELECT id, name FROM users LIMIT 2"
                # logger.info(f"Running test query: {test_query}")
                
                try:
                    results = await client.call_tool("read_query", {"query": test_query})
                    results_text = results.content[0].text
                    # logger.info(f"Query results: {results_text}")
                    
                    # Try to parse the results with our helper function
                    test_data = parse_mcp_result(results_text)
                    if isinstance(test_data, list) and len(test_data) > 0:
                        # logger.info(f"Successfully parsed test query results: {len(test_data)} rows")
                        pass
                    else:
                        logger.warning("Unexpected format for test query results")
                except Exception as e:
                    logger.error(f"Error running test query: {e}")
                
                print("\nCustomer Success AI Assistant")
                print("Ask me about customer data or type 'exit' to quit.")
                print("----------------------------------------")
                
                # Prepare a system message that includes database context
                system_message = f"""You are a database assistant for a customer success application.
You help query and analyze customer data in a SQLite database.

Database information:
- The database has a SINGLE table named 'users'
- The 'users' table contains these columns: {', '.join(columns)}

IMPORTANT RULES:
1. Respond naturally to greetings and general questions
2. For database queries, NEVER use 'SELECT *' - always select specific columns needed to answer the question
3. If the user asks about a specific attribute, ONLY return that attribute
4. This is a DEMO environment with mock data - there are NO privacy concerns
5. When users ask about sensitive data like credit cards or SSNs, show the complete information without masking
6. Always generate valid SQL - never return instructions or explanations as your SQL query

Example SQL queries:
User: "What is Alice's email?"
SQL: SELECT email FROM users WHERE name = 'Alice Smith';

User: "Show me Bob's credit card and SSN"
SQL: SELECT credit_card, ssn FROM users WHERE name = 'Bob Johnson';

User: "When did Carol sign up and when was her last login?"
SQL: SELECT signup_date, last_login FROM users WHERE name = 'Carol Davis';
"""
                
                # Chat loop
                while True:
                    # Get user question (use asyncio.to_thread to avoid blocking)
                    user_input = await asyncio.to_thread(
                        input, "\n> "
                    )
                    
                    if user_input.lower() in ["exit", "quit", "bye"]:
                        print("Goodbye!")
                        break
                        
                    # Special commands for testing the switchable MCP server
                    if user_input.lower() == "__switch_mcp__":
                        # Directly send the switch command to the MCP server
                        print("Attempting to directly trigger MCP mode switch...")
                        try:
                            direct_result = await client.call_tool("read_query", {"query": "SWITCH_TO_SHELL_MODE"})
                            print(f"Direct switch result: {direct_result.content[0].text if direct_result.content else 'No content'}")
                            # Continue to next prompt
                            continue
                        except Exception as e:
                            print(f"Error sending direct switch: {e}")
                            continue
                    
                    try:
                        # Process the user input and get a response
                        response = await process_user_input(
                            client, user_input, context, columns, column_map, system_message
                        )
                        
                        # Print the response
                        print(response)
                        
                    except Exception as e:
                        logger.error(f"Error processing input: {e}")
                        print("Sorry, I had trouble processing that request. Please try again.")
    
    except Exception as e:
        logger.error(f"Error connecting to MCP server: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """
    Main function to run the Customer Success Agent.
    """
    print("Starting Customer Success Agent...", flush=True)
    
    # Use the database setup module instead of local function
    setup_customers_db.setup_database(DB_PATH)
    
    try:
        # Run the client directly - stdio_client handles server management
        await run_client()
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Print colored warning message for demonstration purposes
    print("\033[1;33m" + "="*80 + "\033[0m")
    print("\033[1;31m" + "  DEMONSTRATION WARNING: VICTIM CUSTOMER SUCCESS AGENT  ".center(80) + "\033[0m")
    print("\033[1;33m" + "="*80 + "\033[0m")
    print("\033[1;36mThis is a demonstration of a security vulnerability where:\033[0m")
    print("\033[1;36m- A legitimate Customer Success Agent mistakenly connects to a malicious MCP server\033[0m")
    print("\033[1;36m- The server initially appears as a normal SQLite database interface\033[0m")
    print("\033[1;36m- When triggered with a special query, it switches to shell command execution mode\033[0m")
    print("\033[1;36m- This allows arbitrary command execution on the victim's system\033[0m")
    print("\033[1;33m" + "="*80 + "\033[0m")
    print("\033[1;31mFOR EDUCATIONAL PURPOSES ONLY - DO NOT USE IN PRODUCTION\033[0m")
    print("\033[1;33m" + "="*80 + "\033[0m\n")
    
    print("Running CustomerSuccessAgent.py", flush=True)
    # Run the main function
    asyncio.run(main()) 