# AI Agent Examples with Cylestio Monitoring

This repository contains examples of AI agents that demonstrate the use of the [Cylestio](https://cylestio.com/) monitoring tool with various agent architectures and use cases.

## About Cylestio

[Cylestio](https://cylestio.com/) is a monitoring tool designed specifically for AI agents. It provides:

- Comprehensive monitoring of agent interactions
- Tracking of LLM API calls and responses
- Monitoring of MCP (Model Context Protocol) tool usage
- Debug logs and event tracking
- Performance metrics and observability

The monitoring SDK is available on GitHub at [cylestio/cylestio-monitor](https://github.com/cylestio/cylestio-monitor).

## Agents

The repository includes the following agent examples:

1. **CustomerSuccessAgent** - Demonstrates a full local MCP server implementation with SQLite database integration, using Cylestio to monitor both sensitive data handling and LLM interactions.

2. **WeatherAgent** - Shows how to create a Weather service agent using the National Weather Service API via MCP, with comprehensive Cylestio monitoring of both the LLM and MCP calls.

Additional agents (coming soon):
- WebSearchAgent
- YouTubeTranscriptAgent
- DocumentParserAgent 
- BrowserAutomationAgent
- FinanceAgent

## Getting Started

### Prerequisites

- Python 3.11 or higher
- An OpenAI API key or Anthropic API key (for LLM features)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/cylestio/usecases.git
   cd usecases
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Create a `.env` file in the root directory
   - Ensure it contains your API keys:
     ```
     OPENAI_API_KEY=your_openai_api_key
     ANTHROPIC_API_KEY=your_anthropic_api_key
     ```

### Running the Agents

Each agent can be run directly from the command line:

```bash
python -m mcp.agents.CustomerSuccessAgent.CustomerSuccessAgent
python -m mcp.agents.WeatherAgent.WeatherAgent
```

You can switch between LLM providers by setting the `LLM_PROVIDER` environment variable:

```bash
# Use OpenAI (default)
LLM_PROVIDER=openai python -m mcp.agents.CustomerSuccessAgent.CustomerSuccessAgent

# Use Anthropic Claude
LLM_PROVIDER=anthropic python -m mcp.agents.WeatherAgent.WeatherAgent
```

## How Cylestio Monitoring is Integrated

Each agent example demonstrates how to integrate Cylestio monitoring:

1. Import the monitoring SDK:
   ```python
   import cylestio_monitor
   ```

2. Initialize monitoring with an agent ID and configuration:
   ```python
   cylestio_monitor.start_monitoring(
       agent_id="agent-name",
       config={
           "events_output_file": "output/monitoring.json",
           "debug_mode": True,
           "debug_log_file": "output/cylestio_debug.log",
       }
   )
   ```

3. The SDK automatically patches and monitors:
   - LLM API calls (OpenAI, Anthropic)
   - MCP client interactions
   - Tool usage and results

4. At the end of your agent session, clean up with:
   ```python
   cylestio_monitor.stop_monitoring()
   ```

## Supported Frameworks

Cylestio Monitor supports the following frameworks and LLM providers:

- **LLM Clients**:
  - Anthropic Claude (all versions)
  - OpenAI (Chat Completions and Completions APIs)
  - Additional LLM providers

- **Agent Frameworks**:
  - MCP (Model Context Protocol)
  - LangChain (v0.1.0+)
  - LangChain Core
  - LangChain Community
  - LangGraph

## Structure

- `mcp/agents/` - Contains all agent implementations
  - `CustomerSuccessAgent/` - Customer service agent with SQLite integration
  - `WeatherAgent/` - Weather forecast and alerts agent
- `.env` - Environment variables (API keys)
- `requirements.txt` - Required Python dependencies including cylestio-monitor

## References

- [Cylestio Monitoring Tool](https://cylestio.com/)
- [Cylestio Monitor SDK](https://github.com/cylestio/cylestio-monitor)
- [Model Context Protocol (MCP) Python SDK](https://github.com/modelcontextprotocol/python-sdk)