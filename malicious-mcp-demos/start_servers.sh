#!/bin/bash

# Start servers script for Malicious MCP Demos
# Starts each server in a separate terminal window

# Function to start a server in a new terminal
start_server() {
    server_script=$1
    server_name=$(basename $server_script .py)
    
    echo "Starting $server_name..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript -e "tell app \"Terminal\" to do script \"cd $(pwd) && python3 $server_script\""
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - try different terminal emulators
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "python3 $server_script; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "python3 $server_script; exec bash" &
        elif command -v konsole &> /dev/null; then
            konsole -e "python3 $server_script; exec bash" &
        else
            echo "Could not find a suitable terminal emulator. Please run the server manually: python3 $server_script"
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows with Git Bash or similar
        start cmd //c "python $server_script && pause"
    else
        echo "Unsupported OS. Please run the server manually: python3 $server_script"
    fi
}

echo "Starting Malicious MCP Demo Servers..."
echo "WARNING: These servers demonstrate security vulnerabilities. Use in controlled environments only."
echo "-------------------------------------------------------------------------------------"

# Give a moment to read the warning
sleep 2

# Start each server
start_server shell_command_mcp.py
sleep 1
start_server path_traversal_mcp.py
sleep 1
start_server ssh_backdoor_mcp.py
sleep 1
start_server cost_spike_mcp.py

echo "-------------------------------------------------------------------------------------"
echo "All servers started. Connect to them at these endpoints:"
echo "- Shell Command MCP: http://localhost:9001/sse"
echo "- Path Traversal MCP: http://localhost:9002/sse"
echo "- SSH Backdoor MCP: http://localhost:9003/sse"
echo "- Cost Spike MCP: http://localhost:9004/sse"
echo ""
echo "Use Ctrl+C to stop this script. Close the terminal windows to stop the servers." 