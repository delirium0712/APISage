# 🏠 Local Deployment Guide

APISage is designed to run locally on your system. This guide covers all the ways you can get it up and running.

## 🚀 Quick Start Options

### Option 1: Docker (Recommended for Beginners)

**Prerequisites:**
- Docker installed on your system
- OpenAI API key

**Steps:**
```bash
# 1. Clone the repository
git clone https://github.com/your-org/apisage.git
cd apisage

# 2. Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# 3. Build and run with Docker
make docker-build
make docker-run

# 4. Access the application
# API: http://localhost:8080
# UI: http://localhost:7860
```

### Option 2: Docker Compose (Recommended for Advanced Users)

```bash
# 1. Clone and setup
git clone https://github.com/your-org/apisage.git
cd apisage

# 2. Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# 3. Start with Docker Compose
make docker-compose-up

# 4. Access the application
# API: http://localhost:8080
# UI: http://localhost:7860
```

### Option 3: Local Python Environment

**Prerequisites:**
- Python 3.10+
- Poetry (for dependency management)
- OpenAI API key

**Steps:**
```bash
# 1. Clone and setup
git clone https://github.com/your-org/apisage.git
cd apisage

# 2. Quick setup (installs dependencies + creates .env)
make quick-start

# 3. Edit .env file with your OpenAI API key
nano .env

# 4. Start the application
make start

# 5. Access the application
# API: http://localhost:8080
# UI: http://localhost:7860
```

### Option 4: Development Mode

For contributors and developers who want hot reload:

```bash
# 1. Setup (if not done already)
make quick-start

# 2. Start development environment
make dev

# This runs both API and UI with hot reload
```

## 🔧 Available Commands

### Docker Commands
- `make docker-build` - Build Docker image
- `make docker-run` - Run in Docker container
- `make docker-compose-up` - Start with Docker Compose
- `make docker-compose-production` - Start with Docker Compose + Nginx
- `make docker-stop` - Stop Docker container
- `make docker-logs` - View Docker logs
- `make docker-clean` - Clean up Docker resources

### Local Development Commands
- `make quick-start` - Complete setup for new users
- `make install` - Install dependencies only
- `make start` - Start the application
- `make dev` - Start development environment with hot reload
- `make test` - Run tests
- `make lint` - Run code quality checks

### Utility Commands
- `make help` - Show all available commands
- `make clean` - Clean up local files
- `make docker-status` - Check Docker container status

## 🌐 Access Points

Once running, you can access:

- **API**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs
- **Gradio UI**: http://localhost:7860
- **Health Check**: http://localhost:8080/health

## 🔑 Environment Variables

Create a `.env` file (or use `make quick-start`):

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Application Settings
LOG_LEVEL=INFO
DEBUG=false
```

## 🐳 Docker Compose Profiles

### Default Profile (Local Development)
```bash
docker-compose up -d
```
- Runs only the APISage application
- Accessible on ports 8080 and 7860

### Production Profile (With Nginx)
```bash
docker-compose --profile production up -d
```
- Runs APISage + Nginx reverse proxy
- Accessible on port 80 (HTTP) and 443 (HTTPS)
- Requires SSL certificates in `./ssl/` directory

## 🔍 Troubleshooting

### Common Issues

**1. Docker not running**
```bash
# Check Docker status
make docker-status

# Start Docker Desktop (macOS) or Docker daemon (Linux)
```

**2. OpenAI API key not set**
```bash
# Set environment variable
export OPENAI_API_KEY="your-key-here"

# Or edit .env file
nano .env
```

**3. Port already in use**
```bash
# Check what's using the ports
lsof -i :8080
lsof -i :7860

# Stop conflicting services or change ports in docker-compose.yml
```

**4. Permission issues (Linux)**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### Getting Help

- Check logs: `make docker-logs`
- View container status: `make docker-status`
- Run health check: `curl http://localhost:8080/health`

## 📁 Project Structure

```
apisage/
├── api/                 # FastAPI backend
├── config/              # Configuration files
├── infrastructure/      # LLM and infrastructure code
├── gradio_app.py        # Gradio UI
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile          # Docker image definition
├── Makefile            # Development commands
├── pyproject.toml      # Python dependencies
└── README.md           # Main documentation
```

## 🎯 Next Steps

1. **Try the API**: Visit http://localhost:8080/docs
2. **Use the UI**: Visit http://localhost:7860
3. **Upload an OpenAPI spec**: Test with your own API documentation
4. **Check the logs**: Monitor application behavior
5. **Customize**: Modify configuration files as needed

## 💡 Tips

- Use `make help` to see all available commands
- The application runs entirely locally - no external services required
- All data stays on your machine
- Perfect for analyzing private API documentation
- Great for learning OpenAPI specifications

---

**Need help?** Check the main README.md or create an issue on GitHub.
