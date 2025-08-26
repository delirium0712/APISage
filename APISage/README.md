# 🚀 Enterprise RAG Documentation Assistant

A production-ready, multi-agent RAG system with intelligent document processing, auto-code generation, and comprehensive evaluation frameworks.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://docker.com/)

## ✨ Key Features

### 🤖 **Multi-Agent Orchestration**
- **LangGraph-based coordination** with 5 specialized agents
- **Intelligent task routing** and dependency management
- **Real-time health monitoring** with auto-recovery

### 🔍 **Advanced Search Architecture**
- **Hybrid Search**: Vector similarity + lexical search (BM25)
- **Intelligent Reranking** for optimal result relevance
- **Multiple Vector Stores**: Qdrant, Milvus, Chroma, Pinecone

### ⚡ **Auto Code Generation**
- **Documentation → Working Code** in seconds
- **Multi-language support**: Python, JavaScript, TypeScript
- **Production-ready clients** with error handling & auth

### 🏗️ **Enterprise-Grade Architecture**
- **Microservices design** with clear component boundaries
- **Multi-LLM provider support** with automatic failover
- **Comprehensive evaluation** using RAGAS & DeepEval

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker (optional)
- Redis & PostgreSQL (for full features)

### Installation
```bash
# Clone repository
git clone <repository-url>
cd rag_implementation

# Install dependencies
pip install -r requirements.txt

# Install browser for web scraping
playwright install

# Start the system
python main.py interactive
```

### Docker Deployment
```bash
# Start all services
docker-compose up -d

# The API will be available at http://localhost:8000
```

## 🎯 Usage Examples

### **API Server Mode**
```bash
# Start REST API server
python main.py api --host localhost --port 8000

# Check system health
curl http://localhost:8000/health

# View interactive documentation
open http://localhost:8000/docs
```

### **Interactive Mode**
```bash
# Start interactive CLI
python main.py interactive

# Add documents
RAG> add https://api.stripe.com/docs

# Query the system
RAG> query How do I create a payment?
```

### **Batch Processing**
```bash
# Process multiple documents
python main.py batch input_urls.txt -o results.json
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/documents/analyze-api` | POST | Analyze API documentation |
| `/code/generate` | POST | Generate client code |
| `/query` | POST | Query the knowledge base |
| `/evaluate` | POST | Run evaluation suite |

### **Example: API Analysis**
```bash
curl -X POST "http://localhost:8000/documents/analyze-api" \
-H "Content-Type: application/json" \
-d '{
  "content": "# API Docs\n## Endpoints\n- GET /users\n- POST /users",
  "source_url": "https://api.example.com"
}'
```

### **Example: Code Generation**
```bash
curl -X POST "http://localhost:8000/code/generate" \
-H "Content-Type: application/json" \
-d '{
  "api_doc": {"title": "My API", "endpoints": [...]},
  "language": "python",
  "template_name": "http_client"
}'
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Orchestrator  │    │   Agents        │
│   REST API      │◄──►│   (LangGraph)   │◄──►│   Specialized   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vector Store  │    │   LLM Manager   │    │   Evaluation    │
│   (Multi-type)  │    │   (Multi-LLM)   │    │   Framework     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Core Components**
- **`core/orchestrator.py`**: Main system coordinator
- **`agents/`**: Specialized AI agents (document, API, code, eval)
- **`infrastructure/`**: Backend management (vector stores, LLMs)
- **`api/`**: REST API implementation
- **`config/`**: Configuration management

## 📊 Demo Scripts

Ready-to-use demo scripts in `/demo/`:

```bash
# System health monitoring
./demo/demo_health.sh

# API analysis demonstration
./demo/demo_analysis.sh

# Code generation showcase
./demo/demo_codegen.sh
```

## 🛠️ Configuration

### **Environment Variables**
```bash
# LLM Providers
export PRIMARY_LLM_PROVIDER="ollama"
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"

# Vector Stores
export PRIMARY_VECTOR_STORE="qdrant"
export QDRANT_HOST="localhost"

# Databases
export REDIS_URL="redis://localhost:6379"
export POSTGRES_URL="postgresql://user:pass@localhost/db"
```

### **Multi-Provider Support**
- **LLMs**: Ollama, OpenAI, Claude, Gemini
- **Vector Stores**: Qdrant, Milvus, Chroma, Pinecone
- **Document Formats**: OpenAPI, Postman, Markdown, HTML

## 📈 Evaluation & Quality

Built-in evaluation framework with:
- **RAGAS metrics**: Faithfulness, answer relevancy, context precision
- **DeepEval integration**: Comprehensive quality assessment
- **Performance monitoring**: Response times, success rates
- **A/B testing support**: Compare different configurations

## 🧪 Development

### **Code Quality**
```bash
# Formatting
black .

# Linting
flake8 .

# Type checking
mypy .
```

### **Testing**
```bash
# Run evaluation suite
python -m pytest archive_files/

# Performance testing
python archive_files/test_performance_optimized.py
```

## 📚 Documentation

- **[Demo Presentation Plan](DEMO_PRESENTATION_PLAN.md)**: Complete demo guide
- **[Performance Optimization](docs/PERFORMANCE_OPTIMIZATION_SUMMARY.md)**: System optimization details
- **[SDK Documentation](docs/SDK_README.md)**: SDK usage guide

## 🚀 Production Deployment

### **Docker Compose**
```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379
      - POSTGRES_URL=postgresql://user:pass@postgres/db
  
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
  
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

### **Key Production Features**
- **Health monitoring** with auto-recovery
- **Graceful shutdown** handling
- **Comprehensive logging** with correlation IDs
- **Environment-specific configuration**
- **Resource monitoring** and alerting

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🎯 Why This Project Stands Out

### **Advanced ML Engineering**
- Production-grade architecture with monitoring and health checks
- Multi-agent orchestration beyond simple RAG implementations
- Comprehensive evaluation framework with industry-standard metrics

### **Innovation**
- Automatic code generation from API documentation
- Hybrid search with intelligent reranking
- Multi-provider LLM support with failover chains

### **Enterprise Ready**
- Microservices architecture with clear boundaries
- Environment-driven configuration management
- Docker containerization with full dependency management

**This showcases the full spectrum of modern ML engineering: from research concepts to production systems with real business value.**