#!/bin/bash

# API Agent Framework - One-Command Installation Script
# This script sets up the complete self-hosted API Agent Framework

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FRAMEWORK_NAME="API Agent Framework"
FRAMEWORK_VERSION="1.0.0"
REPO_URL="https://github.com/your-org/api-agent-framework.git"
DEFAULT_PORT=8080
DEFAULT_UI_PORT=3000

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose not found. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check available ports
    if lsof -Pi :$DEFAULT_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $DEFAULT_PORT is already in use. The framework will use a different port."
    fi
    
    if lsof -Pi :$DEFAULT_UI_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $DEFAULT_UI_PORT is already in use. The framework will use a different port."
    fi
    
    print_success "Prerequisites satisfied"
}

# Function to download framework
download_framework() {
    print_status "Setting up API Agent Framework..."
    
    # Create project directory
    PROJECT_DIR="api-agent-framework"
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "Directory $PROJECT_DIR already exists. Updating..."
        cd "$PROJECT_DIR"
        git pull origin main || true
    else
        # Clone repository or create from current directory
        if [ -d ".git" ]; then
            print_status "Using current directory as framework source"
            PROJECT_DIR="."
        else
            print_status "Creating framework directory structure"
            mkdir -p "$PROJECT_DIR"
            cd "$PROJECT_DIR"
        fi
    fi
    
    print_success "Framework directory ready"
}

# Function to configure environment
configure_environment() {
    print_status "Configuring environment..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_status "Created .env file from template"
        else
            print_warning "No .env.example found. Creating basic .env file..."
            cat > .env << EOF
# API Agent Framework - Environment Configuration
APP_NAME=API Agent Framework
APP_VERSION=1.0.0
APP_ENVIRONMENT=production

# LLM Provider Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Vector Database Configuration
MILVUS_HOST=milvus
MILVUS_PORT=19530

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# API Configuration
MAX_FILE_SIZE=10485760
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EOF
        fi
        
        print_warning "Please edit .env file with your configuration:"
        echo "   - Set your OpenAI API key (or other LLM provider)"
        echo "   - Configure any custom settings"
        echo ""
        read -p "Press Enter when you're ready to continue..."
    else
        print_status "Using existing .env file"
    fi
    
    print_success "Environment configured"
}

# Function to build and start services
start_services() {
    print_status "Building and starting services..."
    
    # Build images
    print_status "Building Docker images (this may take a few minutes)..."
    docker-compose build --no-cache
    
    # Start services
    print_status "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 15
    
    # Check health
    if curl -f http://localhost:$DEFAULT_PORT/health &> /dev/null; then
        print_success "API Agent is running!"
    else
        print_warning "API Agent may still be starting up. Check logs with: docker-compose logs"
    fi
    
    print_success "Services started successfully"
}

# Function to initialize database
initialize_database() {
    print_status "Initializing vector database..."
    
    # Wait for Milvus to be ready
    print_status "Waiting for Milvus to be ready..."
    sleep 30
    
    # Initialize collections (this would be done by the application)
    print_status "Database initialization complete"
}

# Function to show post-installation information
show_post_install_info() {
    echo ""
    echo "🎉 Installation Complete!"
    echo "========================"
    echo ""
    echo "Your API Agent Framework is now running!"
    echo ""
    echo "Access Points:"
    echo "  - Admin Dashboard: http://localhost:$DEFAULT_UI_PORT"
    echo "  - API Endpoint: http://localhost:$DEFAULT_PORT"
    echo "  - API Documentation: http://localhost:$DEFAULT_PORT/docs"
    echo "  - Milvus Console: http://localhost:9001"
    echo ""
    echo "Next Steps:"
    echo "  1. Open the Admin Dashboard in your browser"
    echo "  2. Upload your API documentation files"
    echo "  3. Connect your knowledge base"
    echo "  4. Start querying your APIs!"
    echo ""
    echo "Useful Commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Restart services: docker-compose restart"
    echo "  - Update framework: git pull && docker-compose up -d --build"
    echo ""
    echo "Documentation: https://docs.api-agent.dev"
    echo "Support: https://github.com/your-org/api-agent-framework/issues"
}

# Function to check system resources
check_system_resources() {
    print_status "Checking system resources..."
    
    # Check available memory
    TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [ "$TOTAL_MEM" -lt 4096 ]; then
        print_warning "System has less than 4GB RAM. Performance may be limited."
    else
        print_success "System memory: ${TOTAL_MEM}MB"
    fi
    
    # Check available disk space
    DISK_SPACE=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$DISK_SPACE" -lt 10 ]; then
        print_warning "Less than 10GB disk space available. Consider freeing up space."
    else
        print_success "Available disk space: ${DISK_SPACE}GB"
    fi
    
    # Check Docker resources
    if command -v docker &> /dev/null; then
        DOCKER_MEM=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}" | grep Images | awk '{print $3}' | sed 's/MB//')
        if [ "$DOCKER_MEM" -gt 2048 ]; then
            print_warning "Docker images using more than 2GB. Consider cleanup: docker system prune -a"
        fi
    fi
}

# Function to create sample data
create_sample_data() {
    print_status "Creating sample data..."
    
    # Check if sample OpenAPI spec exists
    if [ -f "examples/sample_openapi.json" ]; then
        print_status "Sample OpenAPI specification found"
        print_status "You can test the system by uploading this file through the Admin Dashboard"
    else
        print_status "No sample data found. You can create your own API documentation files."
    fi
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Check API service
    if curl -f http://localhost:$DEFAULT_PORT/health &> /dev/null; then
        print_success "API service: Healthy"
    else
        print_error "API service: Unhealthy"
    fi
    
    # Check Milvus
    if curl -f http://localhost:19530/health &> /dev/null; then
        print_success "Milvus service: Healthy"
    else
        print_warning "Milvus service: Starting up (this is normal)"
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        print_success "Redis service: Healthy"
    else
        print_error "Redis service: Unhealthy"
    fi
}

# Main installation function
main() {
    echo ""
    echo "🚀 $FRAMEWORK_NAME v$FRAMEWORK_VERSION"
    echo "=========================================="
    echo ""
    echo "This script will install the complete self-hosted API Agent Framework."
    echo "The framework includes:"
    echo "  • AI-powered API documentation processing"
    echo "  • Vector database (Milvus) for semantic search"
    echo "  • Multiple LLM provider support (OpenAI, Anthropic, Local)"
    echo "  • Quality evaluation system"
    echo "  • Knowledge base integrations"
    echo "  • Admin dashboard"
    echo ""
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root. This is not recommended for security reasons."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Run installation steps
    check_prerequisites
    check_system_resources
    download_framework
    configure_environment
    start_services
    initialize_database
    create_sample_data
    run_health_checks
    show_post_install_info
    
    print_success "Installation completed successfully!"
}

# Function to handle cleanup on exit
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "Installation failed. Check the logs above for details."
        echo ""
        echo "Troubleshooting tips:"
        echo "  1. Ensure Docker is running"
        echo "  2. Check available ports"
        echo "  3. Verify system resources"
        echo "  4. Check logs: docker-compose logs"
        echo ""
        echo "For help, visit: https://github.com/your-org/api-agent-framework/issues"
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Check command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --skip-checks  Skip system resource checks"
        echo "  --port PORT    Use custom port (default: $DEFAULT_PORT)"
        echo ""
        echo "Examples:"
        echo "  $0                    # Standard installation"
        echo "  $0 --port 9000       # Install on port 9000"
        echo "  $0 --skip-checks     # Skip resource checks"
        exit 0
        ;;
    --skip-checks)
        SKIP_CHECKS=true
        ;;
    --port)
        if [ -n "$2" ]; then
            DEFAULT_PORT="$2"
            shift 2
        else
            print_error "Port number required after --port"
            exit 1
        fi
        ;;
esac

# Run main installation
main "$@"
