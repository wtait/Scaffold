# Lovable Clone - AI-Powered Web App Builder

A real-time AI-powered web application builder inspired by [lovable.dev](https://lovable.dev). This project demonstrates how to build a simple agent using sandboxed environments, MCP servers, and [BAML](https://github.com/BoundaryML/baml). It's hosted on [beam.cloud](https://beam.cloud).

![Lovable Clone Demo](assets/lovable-demo.gif)

> To learn about the architecture in detail, read the full post [on our blog](https://www.beam.cloud/blog/agentic-apps).

## ️ Architecture

The application consists of four main components:

1. **Model Client** - BAML-based client to talk to LLM in an RPC-like way
2. **Sandbox Environment** - Isolated compute sandbox for running preview environments (React app we're editing)
3. **MCP Server** - Tools for managing the sandbox and code operations
4. **WS-Based Agent** - Real-time server for communication between client and agent

![Architecture Diagram](assets/arch.png)

## 📋 Prerequisites

- Python 3.12+
- Node.js 20+
- OpenAI API key
- [Beam](https://beam.cloud) account for hosting ([sandboxes](https://docs.beam.cloud/v2/sandbox/overview), frontend, mcp server)

## 🛠️ Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/beam-cloud/lovable-clone
   cd lovable-clone
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   # or using uv
   uv sync
   ```

3. **Install frontend dependencies**

   ```bash
   cd frontend
   npm install
   ```

4. **Set up secrets**
   ```bash
   beam secret create OPENAI_API_KEY 'your-openai-api-key'
   beam secret create LOVABLE_MCP_URL 'your-mcp-server-url'
   ```

## 🎯 Usage

### Starting the MCP Server

The MCP server provides tools for managing sandboxed environments:

```bash
beam serve src/tools.py:s
```

This starts the FastMCP server with tools for:

- `create_app_environment` - Spins up a new React sandbox
- `load_code` - Retrieves code from the sandbox
- `edit_code` - Updates code in the sandbox

### Starting the Agent

The agent handles real-time communication with the client/frontend:

```bash
beam serve src/agent.py:handler
```

### Running the Frontend

```bash
cd frontend
npm run dev
```

### End to end flow for iterating on the app:

1. Start the frontend: `cd frontend && npm run dev`
2. In a new terminal, start the MCP server: `beam serve src/tools.py:s` -> copy URL displayed in terminal
3. In a new terminal window, start the agent: `beam serve src/agent.py:agent` -> modify the URL in src/agent.py to point to the above MCP server URL
4. In the `frontend` directory, copy `.env.template` to `.env`, and replace the token with your `Beam` [token](https://platform.beam.cloud/settings/api-keys), and the URL with the websocket URL printed in the shell
5. Start interacting with the app in your browser!
6. If you want to change the prompt, edit `baml_src/build.baml` and run `make generate` to regenerate the BAML clients

### BAML / Prompts

Prompts are defined in `baml_src/build.baml`:

- **EditCode Function** - Main function for code generation
- **CodeChanges Schema** - Defines the structure of AI responses
- **Test Cases** - Validate prompt behavior

### Sandbox/MCP server config

The sandbox environment is configured in `src/tools.py`:

- Node.js 20 base image
- React + Vite + shadcn/ui template
- Additional packages: React Router, Recharts, TanStack Query, etc.
