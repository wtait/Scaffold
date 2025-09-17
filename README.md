# Platform-Agnostic AI App Builder

A real-time AI-powered web application builder that can run on any cloud provider or on-premises infrastructure. This project has been migrated from the original Beam-dependent version to be completely platform-agnostic.

![Demo](assets/lovable-demo.gif)

## 🎯 Key Features

- **Platform Agnostic**: Run on AWS, GCP, Azure, or on-premises
- **Multiple LLM Support**: OpenAI, Anthropic Claude, Google Gemini
- **Docker-based Sandboxes**: Secure isolated environments for code execution
- **Real-time Collaboration**: WebSocket-based streaming updates
- **Full-stack Previews**: Support for both frontend and backend applications
- **Persistent Storage**: File versioning with S3-compatible storage
- **No Vendor Lock-in**: Swap components (database, storage, LLM providers)

## 🏗️ Architecture

The application consists of four main components:

1. **FastAPI Backend** - WebSocket server with agent orchestration
2. **React Frontend** - Real-time UI with code preview
3. **Docker Sandboxes** - Isolated execution environments  
4. **Database & Storage** - PostgreSQL + S3-compatible object storage

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker and Docker Compose
- At least one LLM API key (OpenAI, Anthropic, or Google)

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd lovable-clone

# Copy environment templates
cp .env.example .env
cp frontend/.env.example frontend/.env

# Edit .env files with your configuration
# At minimum, add one LLM API key:
echo "OPENAI_API_KEY=your_openai_api_key" >> .env
```

### 2. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (admin/admin123)
- **Database**: localhost:5432

## 🛠️ Development Setup

### Backend Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from src.database import init_database; init_database()"

# Start development server
python -m uvicorn src.websocket_server:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### BAML Prompt Development

```bash
# Generate BAML client after editing baml_src/build.baml
make generate

# Or manually:
baml-cli generate
```

## 🔧 Configuration

### Environment Variables

**Backend (.env)**:
```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/lovable_clone

# Storage (local or S3)
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=./projects

# LLM API Keys (provide at least one)
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key

# Sandbox
SANDBOX_TYPE=docker
```

**Frontend (frontend/.env)**:
```env
VITE_BACKEND_WS_URL=ws://localhost:8000/ws
VITE_BACKEND_API_URL=http://localhost:8000
```

### Storage Options

#### Local Storage (Default)
```env
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=./projects
```

#### S3-Compatible Storage
```env
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_ENDPOINT_URL=http://localhost:9000  # For MinIO
S3_BUCKET_NAME=lovable-clone-projects
```

## 🚢 Deployment

### Docker Compose (Production)

```bash
# Use production profile with Nginx
docker-compose --profile production up -d
```

### Kubernetes

```bash
# Apply Kubernetes manifests (coming soon)
kubectl apply -f k8s/
```

### Manual Deployment

1. **Database**: Set up PostgreSQL
2. **Storage**: Configure S3 or MinIO
3. **Backend**: Deploy FastAPI app with WebSocket support
4. **Frontend**: Build and serve React app
5. **Reverse Proxy**: Configure Nginx for WebSocket support

## 🔒 Security Notes

- Sandboxes run with resource limits (CPU, memory, timeout)
- Network access is restricted in sandbox environments
- User code is isolated per session
- API keys are not logged or stored in database
- All WebSocket connections require valid session IDs

## 🛠️ API Reference

### WebSocket Endpoints

- `GET /ws/{session_id}` - Main WebSocket connection for real-time communication

### HTTP Endpoints

- `GET /health` - Health check
- `GET /sessions/{session_id}/status` - Session status
- `DELETE /sessions/{session_id}` - Cleanup session

### Message Types

- `INIT` - Initialize session
- `USER` - User input/feedback
- `AGENT_PARTIAL` - Streaming response
- `AGENT_FINAL` - Complete response
- `UPDATE_IN_PROGRESS` - Code update status
- `UPDATE_COMPLETED` - Code update finished

## 🧪 Testing

```bash
# Backend tests
python -m pytest tests/

# Frontend tests
cd frontend && npm test

# Integration tests
python -m pytest tests/integration/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

[Add your license here]

## 🆘 Troubleshooting

### Common Issues

**WebSocket Connection Failed**
- Check that backend is running on port 8000
- Verify WebSocket URL in frontend/.env
- Ensure no firewall blocking connections

**Sandbox Creation Failed**
- Verify Docker is running and accessible
- Check Docker socket permissions
- Review container resource limits

**Database Connection Error**
- Ensure PostgreSQL is running
- Verify DATABASE_URL format
- Check database credentials

**LLM API Errors**
- Verify API keys are set correctly
- Check API key permissions and quotas
- Ensure internet connectivity

### Getting Help

- Check the [Issues](link-to-issues) page
- Review container logs: `docker-compose logs`
- Enable debug logging: `LOG_LEVEL=debug`

---

## 📈 Migration from Beam

This version has been migrated from the original Beam-dependent implementation. Key changes:

- **WebSocket Server**: Replaced `@realtime` decorator with FastAPI WebSockets
- **Sandboxes**: Replaced Beam Sandboxes with Docker containers
- **Storage**: Added S3-compatible storage with local fallback
- **Database**: Added PostgreSQL for session and file persistence
- **LLM Support**: Added multi-provider support beyond OpenAI
- **Configuration**: Environment-based configuration instead of Beam secrets

The migration maintains API compatibility where possible, allowing gradual transition for existing integrations.