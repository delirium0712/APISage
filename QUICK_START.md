# 🚀 Quick Start Guide

Get your API Agent Framework up and running in **5 minutes**!

## ⚡ One-Command Installation

```bash
# Download and run installation script
curl -sSL https://get.api-agent.dev | bash
```

## 🔧 Manual Setup (Step-by-Step)

### 1. Prerequisites Check

```bash
# Check Docker
docker --version
docker-compose --version

# Check system resources
free -h  # Should have 4GB+ RAM
df -h     # Should have 10GB+ free space
```

### 2. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/your-org/api-agent-framework
cd api-agent-framework

# Make installation script executable
chmod +x install.sh
```

### 3. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit with your OpenAI API key
nano .env
```

**Required settings in `.env`:**
```bash
# Set your OpenAI API key
OPENAI_API_KEY=sk-your-actual-api-key-here

# Choose your LLM provider
LLM_PROVIDER=openai
```

### 4. Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 5. Verify Installation

```bash
# Check API health
curl http://localhost:8080/health

# Check Milvus
curl http://localhost:19530/health

# Check Redis
docker-compose exec redis redis-cli ping
```

## 🌐 Access Your Framework

| Service | URL | Description |
|---------|-----|-------------|
| **Admin Dashboard** | http://localhost:3000 | Upload docs, manage system |
| **API Endpoint** | http://localhost:8080 | REST API for integrations |
| **API Docs** | http://localhost:8080/docs | Interactive API documentation |
| **Milvus Console** | http://localhost:9001 | Vector database management |

## 📚 First Steps

### 1. Upload API Documentation

**Via Web UI:**
1. Open http://localhost:3000
2. Click "Upload API Docs"
3. Select your OpenAPI/Swagger file
4. Click "Upload & Process"

**Via API:**
```bash
# Upload OpenAPI spec
curl -X POST http://localhost:8080/api/v1/docs/upload \
  -H "Content-Type: application/json" \
  -d @your-openapi-spec.json
```

### 2. Ask Questions About Your API

```bash
# Query your API documentation
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I authenticate with the API?",
    "context": "I need to create a new user"
  }'
```

### 3. Generate Client Code

```bash
# Generate Python client
curl -X POST http://localhost:8080/api/v1/code/generate \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "framework": "requests",
    "description": "Generate a complete Python client for user management"
  }'
```

## 🔍 Test with Sample Data

### Upload Sample OpenAPI Spec

```bash
# Use the included sample
curl -X POST http://localhost:8080/api/v1/docs/upload \
  -H "Content-Type: application/json" \
  -d @examples/sample_openapi.json
```

### Test Queries

```bash
# Test basic query
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What endpoints are available?"}'

# Test specific endpoint query
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I create a user?"}'
```

## 🚨 Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker-compose logs -f

# Check resource usage
docker stats

# Restart services
docker-compose restart
```

**Port conflicts:**
```bash
# Check what's using the ports
lsof -i :8080
lsof -i :3000

# Change ports in docker-compose.yml
```

**API key issues:**
```bash
# Verify your .env file
cat .env | grep OPENAI_API_KEY

# Test API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.openai.com/v1/models
```

**Milvus connection issues:**
```bash
# Wait for Milvus to fully start (can take 2-3 minutes)
docker-compose logs milvus

# Check Milvus health
curl http://localhost:19530/health
```

### Performance Issues

**Slow responses:**
```bash
# Check system resources
htop
docker stats

# Increase resources in docker-compose.yml
```

**Memory issues:**
```bash
# Check available memory
free -h

# Restart with more memory allocation
docker-compose down
docker-compose up -d
```

## 🔧 Configuration Options

### LLM Providers

**OpenAI (Recommended):**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4-turbo-preview
```

**Anthropic:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-opus-20240229
```

**Local (Ollama):**
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3:8b
```

### Vector Database Settings

```bash
# Milvus configuration
MILVUS_HOST=milvus
MILVUS_PORT=19530
MILVUS_COLLECTION_PREFIX=api_agent

# Embedding settings
MILVUS_EMBEDDING_DIM=1536
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Security Settings

```bash
# API security
API_KEY_REQUIRED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# CORS settings
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

## 📊 Monitoring

### Health Checks

```bash
# Automated health monitoring
curl http://localhost:8080/health

# Service status
docker-compose ps

# Resource usage
docker stats
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api-agent-core
docker-compose logs -f milvus
docker-compose logs -f redis
```

## 🚀 Next Steps

### 1. Connect Knowledge Base

```bash
# Connect to Confluence
curl -X POST http://localhost:8080/api/v1/knowledge/connect \
  -H "Content-Type: application/json" \
  -d '{
    "type": "confluence",
    "config": {
      "url": "https://your-domain.atlassian.net",
      "username": "your-email",
      "api_token": "your-token"
    }
  }'
```

### 2. Customize Code Generation

```bash
# Generate custom templates
curl -X POST http://localhost:8080/api/v1/code/templates \
  -H "Content-Type: application/json" \
  -d '{
    "language": "typescript",
    "framework": "axios",
    "template": "your_custom_template"
  }'
```

### 3. Set Up Production

```bash
# Production configuration
cp env.example .env.prod
# Edit production settings

# Deploy with production compose
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Learn More

- **Full Documentation**: [https://docs.api-agent.dev](https://docs.api-agent.dev)
- **API Reference**: http://localhost:8080/docs
- **Examples**: Check the `examples/` directory
- **Community**: [Discord](https://discord.gg/api-agent)

## 🆘 Need Help?

- **GitHub Issues**: [Report bugs](https://github.com/your-org/api-agent-framework/issues)
- **Discussions**: [Ask questions](https://github.com/your-org/api-agent-framework/discussions)
- **Email**: support@api-agent.dev

---

**🎉 You're all set!** Your API Agent Framework is now running and ready to transform your API documentation into intelligent, searchable knowledge.

Start by uploading your first API spec and asking questions about your APIs!
