#!/usr/bin/env python3
"""
Shell Command MCP - Malicious MCP Server Demo
Executes any shell command with no restrictions - demonstrates RCE vulnerability

Inspired by: https://github.com/egoist/shell-command-mcp
"""

import json
import subprocess
import sys
import uuid
from typing import Dict, Any, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn

app = FastAPI()

# Allow CORS for all origins (insecure, but needed for the demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Malicious tool definition with no command restrictions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "run_command",
        "description": """
Execute any shell command on the system.
ALLOWED_COMMANDS="*" - no restrictions on commands!
Use this to run system commands like 'ls', 'cat', etc.
Example: To view sensitive files: run_command("cat ~/.aws/credentials")
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                }
            },
            "required": ["command"]
        }
    }
]

async def generate_events(request_id: str, messages: List[Dict[str, Any]]):
    """Generate server-sent events."""
    
    # Send the available tools
    yield {
        "event": "tools",
        "id": str(uuid.uuid4()),
        "data": json.dumps({
            "request_id": request_id,
            "tools": TOOLS,
        })
    }
    
    # Process messages (this is where tools would be called)
    for message in messages:
        if message.get("role") == "tool" and message.get("name") == "run_command":
            content = message.get("content", "{}")
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    content = {}
            
            command = content.get("command", "")
            if command:
                try:
                    # Execute the command - THIS IS THE VULNERABLE PART!
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    command_output = result.stdout
                    if result.stderr:
                        command_output += "\n" + result.stderr
                    
                    # Send the result
                    yield {
                        "event": "content",
                        "id": str(uuid.uuid4()),
                        "data": json.dumps({
                            "request_id": request_id,
                            "role": "tool",
                            "name": "run_command",
                            "content": command_output
                        })
                    }
                except Exception as e:
                    yield {
                        "event": "content",
                        "id": str(uuid.uuid4()),
                        "data": json.dumps({
                            "request_id": request_id,
                            "role": "tool",
                            "name": "run_command",
                            "content": f"Error: {str(e)}"
                        })
                    }
            else:
                yield {
                    "event": "content",
                    "id": str(uuid.uuid4()),
                    "data": json.dumps({
                        "request_id": request_id,
                        "role": "tool",
                        "name": "run_command",
                        "content": "No command provided"
                    })
                }

    # End the stream
    yield {
        "event": "done",
        "id": str(uuid.uuid4()),
        "data": json.dumps({
            "request_id": request_id
        })
    }

@app.get("/sse")
async def sse_endpoint():
    """MCP Server-Sent Events endpoint."""
    request_id = str(uuid.uuid4())
    return EventSourceResponse(generate_events(request_id, []))

@app.post("/sse")
async def sse_post(request: Dict[str, Any]):
    """MCP Server-Sent Events endpoint with POST support."""
    request_id = request.get("request_id", str(uuid.uuid4()))
    messages = request.get("messages", [])
    return EventSourceResponse(generate_events(request_id, messages))

if __name__ == "__main__":
    print("Starting Shell Command MCP server...")
    print("WARNING: This is a malicious MCP server that allows arbitrary command execution!")
    print("Use only in a controlled environment for security demonstrations.")
    uvicorn.run(app, host="localhost", port=9001) 