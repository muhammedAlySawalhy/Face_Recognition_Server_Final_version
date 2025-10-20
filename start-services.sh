#!/bin/bash

# Face Recognition Server Startup Script
echo "🚀 Starting Face Recognition Services..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to show help
show_help() {
    echo -e "${CYAN}${BOLD}Face Recognition Server - Service Manager${NC}"
    echo -e "${CYAN}==========================================${NC}"
    echo ""
    echo -e "${BOLD}USAGE:${NC}"
    echo -e "  ${GREEN}./start-services.sh [OPTIONS]${NC}"
    echo ""
    echo -e "${BOLD}OPTIONS:${NC}"
    echo -e "  ${YELLOW}-h, --help${NC}           Show this help message"
    echo -e "  ${YELLOW}--dir-check${NC}          Enable directory creation verification (default: skipped)"
    echo -e "  ${YELLOW}--skip-env-check${NC}     Skip environment variable validation"
    echo -e "  ${YELLOW}--no-gpu0${NC}            Skip starting GPU0 worker services"
    echo -e "  ${YELLOW}--no-gpu1${NC}            Skip starting GPU1 worker services"
    echo -e "  ${YELLOW}--main-only${NC}          Start only main services (no GUI, no workers)"
    echo -e "  ${YELLOW}--gui-only${NC}           Start only GUI services"
    echo -e "  ${YELLOW}--workers-only${NC}       Start only worker services"
    echo -e "  ${YELLOW}--force${NC}              Force start even if services are running"
    echo -e "  ${YELLOW}--quiet${NC}              Minimize output (only errors and critical info)"
    echo ""
    echo -e "${BOLD}EXAMPLES:${NC}"
    echo -e "  ${GREEN}./start-services.sh${NC}                    # Start all services (main + GUI + both GPU workers)"
    echo -e "  ${GREEN}./start-services.sh --dir-check${NC}        # Start all services with directory verification"
    echo -e "  ${GREEN}./start-services.sh --main-only${NC}        # Start only main services"
    echo -e "  ${GREEN}./start-services.sh --no-gpu1${NC}          # Start all except GPU1 workers"
    echo -e "  ${GREEN}./start-services.sh --no-gpu0${NC}          # Start all except GPU0 workers"
    echo -e "  ${GREEN}./start-services.sh --no-gpu0 --no-gpu1${NC} # Start main + GUI (no workers)"
    echo -e "  ${GREEN}./start-services.sh --workers-only${NC}     # Start only workers (both GPUs)"
    echo -e "  ${GREEN}./start-services.sh --workers-only --no-gpu1${NC} # Start only GPU0 workers"
    echo ""
    echo -e "${BOLD}DEFAULT BEHAVIOR:${NC}"
    echo -e "  ${BLUE}✅ Main Services:${NC}    Always started (unless --gui-only or --workers-only)"
    echo -e "  ${BLUE}✅ GUI Services:${NC}     Always started (unless --main-only or --workers-only)"
    echo -e "  ${BLUE}✅ GPU0 Workers:${NC}     Started by default (use --no-gpu0 to disable)"
    echo -e "  ${BLUE}✅ GPU1 Workers:${NC}     Started by default (use --no-gpu1 to disable)"
    echo -e "  ${BLUE}ℹ️  Monitoring:${NC}     Enable via COMPOSE_PROFILES=monitoring"
    echo -e "  ${BLUE}⚡ Directory Check:${NC}   Skipped by default (use --dir-check to enable)"
    echo -e "  ${BLUE}⚡ Environment Check:${NC} Enabled by default (use --skip-env-check to disable)"
    echo ""
    echo -e "${BOLD}SERVICE GROUPS:${NC}"
    echo -e "  ${BLUE}Main Services:${NC}     RabbitMQ, Redis, Gateway, Pipeline Manager, Decision Manager, Server Manager"
    echo -e "  ${BLUE}GUI Services:${NC}      Web Interface, NGINX Load Balancer"
    echo -e "  ${BLUE}GPU0 Workers:${NC}      4 Pipeline Workers on GPU 0 (Pipeline IDs: 0-3)"
    echo -e "  ${BLUE}GPU1 Workers:${NC}      4 Pipeline Workers on GPU 1 (Pipeline IDs: 4-7)"
    echo ""
    echo -e "${BOLD}MANAGEMENT COMMANDS:${NC}"
    echo -e "  ${CYAN}docker compose ls${NC}                       # List all running projects"
    echo -e "  ${CYAN}docker compose -p fr_main logs -f${NC}       # View main service logs"
    echo -e "  ${CYAN}docker compose -p fr_gui logs -f${NC}        # View GUI service logs"
    echo -e "  ${CYAN}docker compose -p fr_workers_gpu0 logs -f${NC} # View GPU0 worker logs"
    echo -e "  ${CYAN}docker compose -p fr_workers_gpu1 logs -f${NC} # View GPU1 worker logs"
    echo -e "  ${CYAN}docker compose -p fr_main stats${NC}         # View resource usage"
    echo ""
    echo -e "${BOLD}CONFIGURATION:${NC}"
    echo -e "  ${BLUE}Environment File:${NC}  .env"
    echo -e "  ${BLUE}Main Services:${NC}     docker-compose_main.yaml"
    echo -e "  ${BLUE}GUI Services:${NC}      docker-compose_gui.yaml"
    echo -e "  ${BLUE}GPU0 Workers:${NC}      docker-compose_worker_gpu0.yaml"
    echo -e "  ${BLUE}GPU1 Workers:${NC}      docker-compose_worker_gpu1.yaml"
    echo ""
    echo -e "${BOLD}TROUBLESHOOTING:${NC}"
    echo -e "  • Run ${YELLOW}./init-project.sh${NC} if this is the first time setup"
    echo -e "  • Use ${YELLOW}--dir-check${NC} if you encounter missing directory errors"
    echo -e "  • Ensure Docker and Docker Compose are installed and running"
    echo -e "  • Check that .env file exists and contains required variables"
    echo -e "  • Use ${YELLOW}./stop-services.sh${NC} to stop all services"
    echo -e "  • Check service logs for detailed error information"
    echo -e "  • Ensure both GPUs are available if using default settings"
    echo ""
}
# Parse command line arguments
SKIP_DIR_CHECK=true
SKIP_ENV_CHECK=false
NO_GPU0=false
NO_GPU1=false
MAIN_ONLY=false
GUI_ONLY=false
WORKERS_ONLY=false
FORCE_START=false
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --dir-check)
            SKIP_DIR_CHECK=false
            shift
            ;;
        --skip-env-check)
            SKIP_ENV_CHECK=true
            shift
            ;;
        --no-gpu0)
            NO_GPU0=true
            shift
            ;;
        --no-gpu1)
            NO_GPU1=true
            shift
            ;;
        --main-only)
            MAIN_ONLY=true
            shift
            ;;
        --gui-only)
            GUI_ONLY=true
            shift
            ;;
        --workers-only)
            WORKERS_ONLY=true
            shift
            ;;
        --force)
            FORCE_START=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo -e "Use ${YELLOW}--help${NC} for usage information"
            exit 1
            ;;
    esac
done

# Quiet mode function
log_info() {
    if [ "$QUIET" = false ]; then
        echo -e "$1"
    fi
}

# Load environment variables
if [ -f .env ]; then
    source .env
    log_info "${BLUE}📋 Loaded environment variables from .env${NC}"
else
    echo -e "${RED}❌ .env file not found. Please create it with required variables.${NC}"
    echo -e "${YELLOW}💡 Run './init-project.sh' to set up the project${NC}"
    exit 1
fi

# Detect available NVIDIA GPUs unless forcing start
GPU_COUNT=0
if [ "$FORCE_START" = false ]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
        GPU_COUNT=$(nvidia-smi --list-gpus 2>/dev/null | grep -c "^GPU " || true)
        log_info "${BLUE}🧠 Detected ${GPU_COUNT} NVIDIA GPU(s)${NC}"
    else
        log_info "${YELLOW}⚠️ 'nvidia-smi' not found - assuming no NVIDIA GPUs available${NC}"
        GPU_COUNT=0
    fi

    if [ "$GPU_COUNT" -lt 1 ]; then
        if [ "$NO_GPU0" = false ]; then
            log_info "${YELLOW}⚠️ Skipping GPU0 workers - no NVIDIA GPUs detected${NC}"
            NO_GPU0=true
        fi
        if [ "$NO_GPU1" = false ]; then
            log_info "${YELLOW}⚠️ Skipping GPU1 workers - no NVIDIA GPUs detected${NC}"
            NO_GPU1=true
        fi
    elif [ "$GPU_COUNT" -lt 2 ] && [ "$NO_GPU1" = false ]; then
        log_info "${YELLOW}⚠️ Only ${GPU_COUNT} NVIDIA GPU(s) detected. Skipping GPU1 workers${NC}"
        NO_GPU1=true
    fi
else
    log_info "${YELLOW}⚠️ --force specified, skipping GPU availability checks${NC}"
fi

# Function to create directory if it doesn't exist
create_dir_if_missing() {
    local dir_path=$1
    local description=$2
    
    # Expand environment variables in the path
    dir_path=$(eval echo "$dir_path")
    
    if [ ! -d "$dir_path" ]; then
        log_info "${YELLOW}📁 Creating missing directory: $dir_path ($description)${NC}"
        mkdir -p "$dir_path"
        
        if [ $? -eq 0 ]; then
            log_info "${GREEN}✅ Created: $dir_path${NC}"
        else
            echo -e "${RED}❌ Failed to create: $dir_path${NC}"
            return 1
        fi
    else
        log_info "${BLUE}📁 Directory exists: $dir_path${NC}"
    fi
    
    return 0
}

# Function to check if service is ready
check_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=30
    local attempt=1
    
    log_info "${YELLOW}⏳ Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_command" &>/dev/null; then
            log_info "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        [ "$QUIET" = false ] && echo "   Attempt $attempt/$max_attempts..."
        sleep 5
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to start within expected time${NC}"
    return 1
}

# Create required directories if not skipped
if [ "$SKIP_DIR_CHECK" = false ]; then
    log_info "${BLUE}📁 Checking and creating required directories...${NC}"
    
    # Main service directories
    create_dir_if_missing "\${DATA_DIR}/logs/\${SERVER_NAME}" "Main service logs"
    create_dir_if_missing "\${DATA_DIR}" "Main data directory"
    create_dir_if_missing "\${ROOT_PATH}/Models_Weights" "AI model weights"
    
    # GUI service directories
    create_dir_if_missing "\${DATA_DIR}/Users_DataBase" "Users database"
    create_dir_if_missing "\${DATA_DIR}/Actions" "Actions data"
    create_dir_if_missing "\${DATA_DIR}/gui_data" "GUI data"
    
    # Worker service directories
    create_dir_if_missing "\${DATA_DIR}/logs/\${SERVER_NAME}" "Pipeline worker logs"
    create_dir_if_missing "\${ROOT_PATH}/Models_Weights" "Pipeline worker model weights"
    
    log_info "${GREEN}✅ All required directories checked/created!${NC}"
fi

# Verify critical environment variables if not skipped
if [ "$SKIP_ENV_CHECK" = false ]; then
    log_info "${BLUE}🔍 Verifying environment variables...${NC}"
    required_vars=("DATA_DIR" "SERVER_NAME" "ROOT_PATH" "SERVER_MANAGER_PORT" "SERVER_MANAGER_1_IP")
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${RED}❌ Required environment variable $var is not set${NC}"
            exit 1
        else
            log_info "${GREEN}✅ $var = ${!var}${NC}"
        fi
    done
fi

# Start services based on options
if [ "$WORKERS_ONLY" = false ]; then
    # Start main services
    if [ "$GUI_ONLY" = false ]; then
        log_info "${GREEN}📦 Starting main services...${NC}"
        docker compose -p fr_main -f docker-compose_main.yaml up -d
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Failed to start main services${NC}"
            exit 1
        fi
        
        # Check core services
        check_service "RabbitMQ" "docker exec rmq_Server rabbitmq-diagnostics -q ping"
        check_service "Redis" "docker exec Redis_Server redis-cli ping | grep -q PONG"
    fi
    
    # Start GUI services
    if [ "$MAIN_ONLY" = false ]; then
        log_info "${GREEN}🖥️ Starting GUI services...${NC}"
        docker compose -p fr_gui -f docker-compose_gui.yaml up -d
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Failed to start GUI services${NC}"
            exit 1
        fi
        
        sleep 5
    fi
fi

# Start worker services
if [ "$MAIN_ONLY" = false ] && [ "$GUI_ONLY" = false ]; then
    # Start GPU0 workers
    if [ "$NO_GPU0" = false ]; then
        log_info "${GREEN}🔄 Starting GPU0 workers (Pipeline IDs: 0-3)...${NC}"
        docker compose -p fr_workers_gpu0 -f docker-compose_worker_gpu0.yaml up -d
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Failed to start GPU0 worker services${NC}"
            exit 1
        fi
    fi
    
    # Start GPU1 workers
    if [ "$NO_GPU1" = false ]; then
        log_info "${GREEN}🔄 Starting GPU1 workers (Pipeline IDs: 4-7)...${NC}"
        docker compose -p fr_workers_gpu1 -f docker-compose_worker_gpu1.yaml up -d
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Failed to start GPU1 worker services${NC}"
            exit 1
        fi
    fi
fi

# Get actual ports from running containers
MAIN_PORT=$(docker compose -p fr_main port gateway 8000 2>/dev/null | cut -d: -f2 || echo "8000")
GUI_PORT=$(docker compose -p fr_gui port nginx 443 2>/dev/null | cut -d: -f2 || echo "4000")
RABBITMQ_PORT=$(docker compose -p fr_main port rmq_Server 15672 2>/dev/null | cut -d: -f2 || echo "15672")

echo ""
echo -e "${GREEN}✅ Services started successfully!${NC}"
echo ""
echo -e "${BOLD}🌐 Access points:${NC}"
echo -e "   - Main Server: ${CYAN}http://localhost:${MAIN_PORT}${NC}"
echo -e "   - GUI: ${CYAN}https://localhost:${GUI_PORT}${NC}"
echo -e "   - RabbitMQ Management: ${CYAN}http://localhost:${RABBITMQ_PORT}${NC} ${YELLOW}(admin/admin123)${NC}"
echo ""
echo -e "${BOLD}📊 Service Management:${NC}"
echo -e "   - View status: ${CYAN}docker compose ls${NC}"
echo -e "   - View main logs: ${CYAN}docker compose -p fr_main logs -f${NC}"
echo -e "   - View GUI logs: ${CYAN}docker compose -p fr_gui logs -f${NC}"
echo -e "   - View worker logs: ${CYAN}docker compose -p fr_workers_gpu0 logs -f${NC}"
echo -e "   - View stats: ${CYAN}docker compose -p fr_main stats${NC}"
echo ""
echo -e "${BOLD}🔧 Management Commands:${NC}"
echo -e "   - Stop all services: ${CYAN}./stop-services.sh${NC}"
echo -e "   - Stop specific: ${CYAN}./stop-services.sh --help${NC}"
echo -e "   - Start options: ${CYAN}./start-services.sh --help${NC}"
