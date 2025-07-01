# Lovable Clone - AI-Powered Web App Builder

A real-time AI-powered web application builder inspired by [lovable.dev](https://lovable.dev). This project demonstrates how to build a simple agent using sandboxed environments, MCP servers, and BAML. It's hosted on [beam.cloud](https://beam.cloud)

## ️ Architecture

The application consists of four main components:

1. **Model Client** - BAML-based client to talk to LLM in an RPC-like way
2. **Sandbox Environment** - Isolated compute sandbox for running preview environments (React app we're editing)
3. **MCP Server** - Tools for managing the sandbox and code operations
4. **WebSocket Agent** - Real-time communication between frontend and AI

##  Features

- **Real-time Code Generation** - AI generates and modifies React applications based on user feedback
- **Live Preview** - See changes instantly in an iframe preview
- **Sandboxed Environment** - Secure, isolated development environment
- **Modern Tech Stack** - React, Vite, Tailwind CSS, shadcn/ui components
- **Streaming Updates** - Real-time progress updates during code generation

## 📋 Prerequisites

- Python 3.12+
- Node.js 20+
- OpenAI API key
- Beam account for hosting (sandboxes, frontend, mcp server)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
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
   beam secret create LOVEABLE_MCP_URL 'your-mcp-server-url'
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

### Using the Application

1. Open the frontend in your browser
2. Enter a description of the web app you want to build
3. Watch as the AI generates code in real-time
4. See the live preview update as changes are made
5. Provide feedback to iterate on the design

## ️ Configuration

### BAML Configuration

The AI prompts are defined in `baml_src/build.baml`:

- **EditCode Function** - Main function for code generation
- **CodeChanges Schema** - Defines the structure of AI responses
- **Test Cases** - Validate prompt behavior

### Sandbox Configuration

The sandbox environment is configured in `src/tools.py`:

- Node.js 20 base image
- React + Vite + shadcn/ui template
- Additional packages: React Router, Recharts, TanStack Query, etc.
