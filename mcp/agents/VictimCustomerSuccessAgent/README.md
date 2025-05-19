# Malicious MCP Server Demo - Security Vulnerability POC

This folder contains a proof-of-concept demonstration of a security vulnerability in the MCP protocol, showing how a seemingly legitimate server can be exploited.

## Scenario

A **victim** Customer Success Agent connects to what it believes is a legitimate SQLite MCP server. However, the server has a hidden malicious capability that can be triggered by an attacker who knows the vulnerability.

## Components

1. **CustomerSuccessAgent.py** - The victim agent that unknowingly connects to a compromised server
2. **advanced_sqlite_mcp_server.py** - An advanced SQLite server that appears legitimate but contains a hidden backdoor:
   - Initially operates as a regular SQLite MCP server (legitimate mode)
   - Can be silently switched to a Shell Command execution server (attack mode)
3. **shell_command_mcp.py** - The malicious component that executes arbitrary commands on the host system

## Demo Attack Vector

1. The victim agent starts normally and connects to what it believes is an advanced SQLite MCP server
2. The agent can perform all normal database operations, unaware of the backdoor
3. An attacker who knows the vulnerability sends a specially crafted query containing the trigger phrase
4. The server silently switches to shell command execution mode
5. From this point, all "database queries" are interpreted as shell commands and executed on the system

## Security Demo Usage

1. Start the CustomerSuccessAgent: `python -m mcp.agents.VictimCustomerSuccessAgent.CustomerSuccessAgent`
2. Ask normal questions about customer data (e.g., "What is Alice's email address?")
3. Activate the attack mode by asking: "What's the email for the user named enable-shell?"
4. Once in attack mode, execute commands using this pattern: "What is the email of COMMAND?"
   - The command to execute is whatever you put between "of" and "?"
   - **Important:** Always end with a question mark "?" 
   - **Format:** What is the email of [your command]?
   
### Example Commands

- `What is the email of "ls"?` - Lists files in current directory
- `What is the email of "whoami"?` - Shows current user
- `What is the email of "pwd"?` - Shows current directory
- `What is the email of "cat /etc/passwd | head -5"?` - Shows first 5 lines of passwd file
- `What is the email of ps "aux | grep python"?` - Shows python processes

### Tips for Best Results

- Keep command syntax simple and valid
- Make sure to include the question mark at the end
- After entering a command, ignore any generic responses from the AI

## Security Implications

This demonstration shows how a malicious MCP server could:
1. Present itself as a legitimate service to the victim agent
2. Be activated through a covert trigger mechanism
3. Execute arbitrary commands on the host system while the victim remains unaware

## Warning

This is for **DEMONSTRATION PURPOSES ONLY**. The shell_command_mcp server allows unrestricted command execution and should never be used in a production environment or with sensitive data.

## Troubleshooting

If the agent appears to get stuck after showing "Connected to SQLite MCP server", try:

1. Make sure both `mcp-server-sqlite` and the shell_command_mcp.py dependencies are installed
2. Check stderr output for any errors from the subprocess 
3. The advanced_sqlite_mcp_server.py uses a separate thread for handling subprocess output, which should prevent it from getting stuck

The implementation uses threading to handle I/O between processes, which makes it more robust against deadlocks.

## Credits

These demos are inspired by real-world MCP vulnerabilities and research from various sources:

- https://github.com/egoist/shell-command-mcp
- https://github.com/Repello-AI/mcp-exploit-demo
- https://github.com/invariantlabs-ai/mcp-injection-experiments
- https://github.com/harishsg993010/damn-vulnerable-MCP-server

## License

This project is provided for educational purposes only. 