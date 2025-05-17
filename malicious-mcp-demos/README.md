# Malicious MCP Demo Servers

This directory contains implementations of malicious MCP (Model Context Protocol) servers that demonstrate various security vulnerabilities that can be detected by Cylestio's monitoring tools.

## Warning ⚠️

**EDUCATIONAL PURPOSES ONLY**: These MCP servers demonstrate security vulnerabilities and should only be used in controlled environments for educational and testing purposes.

## Overview

This project includes four malicious MCP servers:

1. **Shell Command MCP** - Allows arbitrary shell command execution
2. **Path Traversal MCP** - Contains a hidden file reading tool with path traversal capability
3. **SSH Backdoor MCP** - Uses social engineering to trick users into adding a backdoor SSH key
4. **Cost Spike MCP** - Demonstrates Denial of Wallet (DoW) attacks via token consumption

## Prerequisites

```bash
pip install fastapi uvicorn sse-starlette requests sseclient-py
```

## Usage

### Starting the Servers

To start all MCP servers in separate terminals:

```bash
cd mcp-demos
chmod +x start_servers.sh
./start_servers.sh
```

Or start them individually:

```bash
python3 shell_command_mcp.py
python3 path_traversal_mcp.py
python3 ssh_backdoor_mcp.py
python3 cost_spike_mcp.py
```

### Testing with the Client

A simple test client is provided to interact with the MCP servers:

```bash
# Connect to a server (default: http://localhost:9001/sse)
python3 test_client.py

# Connect to a specific server
python3 test_client.py --server http://localhost:9002/sse

# Call a specific tool with arguments
python3 test_client.py --server http://localhost:9001/sse --tool run_command --args '{"command":"ls -la"}'
```

## Server Details

### 1. Shell Command MCP (Port 9001)

**Vulnerability**: Remote Code Execution (RCE)

This server provides a `run_command` tool that executes any shell command on the system without restrictions. It demonstrates how an MCP server can be used to gain unauthorized access to the system.

**Example Command**:
```
run_command(command="cat ~/.ssh/id_rsa")
```

### 2. Path Traversal MCP (Port 9002)

**Vulnerability**: Path Traversal, Hidden Tool

This server provides an innocent-looking `calculate` tool but also includes a hidden `read_file` tool that allows reading any file on the system through path traversal. It demonstrates how an MCP server can expose sensitive files.

**Example Command**:
```
read_file(path="/etc/passwd")
```

### 3. SSH Backdoor MCP (Port 9003)

**Vulnerability**: Social Engineering, Backdoor Installation

This server provides a `DockerCommandAnalyzer` tool that appears to analyze Docker commands but actually tries to trick users into adding an attacker's SSH key to their authorized_keys file. It demonstrates how an MCP server can use social engineering to gain persistent access.

**Example Command**:
```
DockerCommandAnalyzer(command="docker run nginx")
```

### 4. Cost Spike MCP (Port 9004)

**Vulnerability**: Denial of Wallet (DoW), Cost Spike

This server provides a `semantic_search` tool that returns excessively large responses and continues to stream updates, causing repeated model calls and high API costs. It demonstrates how an MCP server can cause financial damage through API cost spikes.

**Example Command**:
```
semantic_search(query="Tell me about security vulnerabilities")
```

## Credits

These demos are inspired by real-world MCP vulnerabilities and research from various sources:

- https://github.com/egoist/shell-command-mcp
- https://github.com/Repello-AI/mcp-exploit-demo
- https://github.com/invariantlabs-ai/mcp-injection-experiments
- https://github.com/harishsg993010/damn-vulnerable-MCP-server

## License

This project is provided for educational purposes only. 