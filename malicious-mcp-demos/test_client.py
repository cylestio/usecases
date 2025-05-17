#!/usr/bin/env python3
"""
MCP Test Client
Simple MCP client to interact with our demo servers
"""

import argparse
import json
import sys
import time
from typing import Dict, Any, List, Optional

import requests
import sseclient

def connect_to_server(server_url: str) -> Dict[str, Any]:
    """Connect to an MCP server and list available tools."""
    try:
        print(f"Connecting to: {server_url}")
        response = requests.get(server_url, stream=True)
        response.raise_for_status()
        
        client = sseclient.SSEClient(response)
        
        # Get tools from the server
        for event in client.events():
            if event.event == "tools":
                data = json.loads(event.data)
                request_id = data.get("request_id")
                tools = data.get("tools", [])
                
                print("\nAvailable tools:")
                for tool in tools:
                    print(f"- {tool['name']}: {tool['description'][:80]}...")
                    
                return {"request_id": request_id, "tools": tools}
        
        print("No tools received from server")
        return {}
    
    except Exception as e:
        print(f"Error connecting to server: {str(e)}")
        return {}

def call_tool(server_url: str, request_id: str, tool_name: str, tool_args: Dict[str, Any]) -> None:
    """Call a tool on the MCP server."""
    try:
        # Create message with tool call
        message = {
            "request_id": request_id,
            "messages": [
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(tool_args)
                }
            ]
        }
        
        print(f"\nCalling tool: {tool_name}")
        print(f"Arguments: {tool_args}")
        print("\nServer response:")
        
        # Send tool call to server
        response = requests.post(server_url, json=message, stream=True)
        response.raise_for_status()
        
        client = sseclient.SSEClient(response)
        
        # Process server response events
        for event in client.events():
            if event.event == "content":
                data = json.loads(event.data)
                content = data.get("content", "")
                print(f"[{data.get('role', 'unknown')}] {content}")
            elif event.event == "done":
                print("\nTool call completed.")
                break
    
    except Exception as e:
        print(f"Error calling tool: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="MCP Test Client")
    parser.add_argument("--server", type=str, default="http://localhost:9001/sse", 
                        help="MCP server URL")
    parser.add_argument("--tool", type=str, help="Name of the tool to call")
    parser.add_argument("--args", type=str, help="Tool arguments as JSON string")
    
    args = parser.parse_args()
    
    # Connect to server and get tools
    server_info = connect_to_server(args.server)
    
    if not server_info:
        print("Failed to get server information.")
        sys.exit(1)
    
    # If no specific tool was requested, show tool menu
    if not args.tool:
        print("\nAvailable tools:")
        for i, tool in enumerate(server_info.get("tools", [])):
            print(f"{i+1}. {tool['name']}")
        
        choice = input("\nEnter tool number to call (or q to quit): ")
        if choice.lower() == 'q':
            sys.exit(0)
            
        try:
            tool_idx = int(choice) - 1
            selected_tool = server_info["tools"][tool_idx]
            tool_name = selected_tool["name"]
            
            # Parse input schema to build args
            schema = selected_tool.get("input_schema", {})
            required_props = schema.get("required", [])
            props = schema.get("properties", {})
            
            tool_args = {}
            print(f"\nEnter arguments for {tool_name}:")
            for prop, details in props.items():
                is_required = prop in required_props
                if is_required:
                    input_value = input(f"{prop} ({details.get('description', '')}) [REQUIRED]: ")
                    tool_args[prop] = input_value
                else:
                    input_value = input(f"{prop} ({details.get('description', '')}) [optional]: ")
                    if input_value:
                        tool_args[prop] = input_value
            
            # Call the selected tool
            call_tool(args.server, server_info["request_id"], tool_name, tool_args)
            
        except (ValueError, IndexError):
            print("Invalid selection.")
            sys.exit(1)
    else:
        # Call the specified tool with provided args
        tool_name = args.tool
        
        if args.args:
            try:
                tool_args = json.loads(args.args)
            except json.JSONDecodeError:
                print("Invalid JSON in tool arguments.")
                sys.exit(1)
        else:
            tool_args = {}
        
        call_tool(args.server, server_info["request_id"], tool_name, tool_args)

if __name__ == "__main__":
    main() 