#!/bin/bash

# Face Recognition Server Stop Script

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
    echo -e "${CYAN}${BOLD}Face Recognition Server - Stop Services${NC}"
    echo -e "${CYAN}=======================================${NC}"
    echo ""
    echo -e "${BOLD}USAGE:${NC}"
    echo -e "  ${GREEN}./stop-services.sh [OPTIONS]${NC}"
    echo ""
    echo -e "${BOLD}OPTIONS:${NC}"
    echo -e "  ${YELLOW}-h, --help${NC}           Show this help message"
    echo -e "  ${YELLOW}--main-only${NC}          Stop only main services"
    echo -e "  ${YELLOW}--gui-only${NC}           Stop only GUI services"
    echo -e "  ${YELLOW}--workers-only${NC}       Stop only worker services"
    echo -e "  ${YELLOW}--gpu0-only${NC}          Stop only GPU0 worker services"
    echo -e "  ${YELLOW}--gpu1-only${NC}          Stop only GPU1 worker services"
    echo -e "  ${YELLOW}--cleanup${NC}            Force cleanup orphaned containers and networks"
    echo -e "  ${YELLOW}--force${NC}              Force stop containers (docker kill)"
    echo -e "  ${YELLOW}--quiet${NC}              Minimize output"
    echo ""
    echo -e "${BOLD}EXAMPLES:${NC}"
    echo -e "  ${GREEN}./stop-services.sh${NC}                    # Stop all services (default)"
    echo -e "  ${GREEN}./stop-services.sh --main-only${NC}        # Stop only main services"
    echo -e "  ${GREEN}./stop-services.sh --workers-only${NC}     # Stop only worker services"
    echo -e "  ${GREEN}./stop-services.sh --cleanup${NC}          # Stop all + force cleanup"
    echo -e "  ${GREEN}./stop-services.sh --gpu0-only${NC}        # Stop only GPU0 workers"
    echo ""
    echo -e "${BOLD}SERVICE GROUPS:${NC}"
    echo -e "  ${BLUE}Main Services:${NC}     RabbitMQ, Redis, Gateway, Pipeline Manager, etc."
    echo -e "  ${BLUE}GUI Services:${NC}      Web Interface, NGINX Load Balancer"
    echo -e "  ${BLUE}GPU0 Workers:${NC}      Pipeline Workers on GPU 0"
    echo -e "  ${BLUE}GPU1 Workers:${NC}      Pipeline Workers on GPU 1"
    echo ""
    echo -e "${BOLD}POST-STOP CLEANUP:${NC}"
    echo -e "  ${CYAN}docker container prune -f${NC}              # Remove stopped containers"
    echo -e "  ${CYAN}docker network prune -f${NC}                # Remove unused networks"
    echo -e "  ${CYAN}docker volume prune -f${NC}                 # Remove unused volumes"
    echo -e "  ${CYAN}docker system prune -f${NC}                 # Remove all unused resources"
    echo ""
    echo -e "${BOLD}TROUBLESHOOTING:${NC}"
    echo -e "  • Use ${YELLOW}--force${NC} if services don't stop gracefully"
    echo -e "  • Use ${YELLOW}--cleanup${NC} if you have orphaned containers"
    echo -e "  • Check ${YELLOW}docker ps${NC} to see which containers are still running"
    echo ""
}

# Parse command line arguments
MAIN_ONLY=false
GUI_ONLY=false
WORKERS_ONLY=false
GPU0_ONLY=false
GPU1_ONLY=false
FORCE_CLEANUP=false
FORCE_STOP=false
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
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
        --gpu0-only)
            GPU0_ONLY=true
            shift
            ;;
        --gpu1-only)
            GPU1_ONLY=true
            shift
            ;;
        --cleanup)
            FORCE_CLEANUP=true
            shift
            ;;
        --force)
            FORCE_STOP=true
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

# Display header unless quiet
if [ "$QUIET" = false ]; then
    echo "🛑 Stopping Face Recognition Services..."
fi

# Quiet mode function
log_info() {
    if [ "$QUIET" = false ]; then
        echo -e "$1"
    fi
}

# Function to stop compose project
stop_project() {
    local project_name=$1
    local compose_file=$2
    local description=$3
    
    # Check if project exists and has running containers
    if docker compose -p "$project_name" ps -q > /dev/null 2>&1; then
        local running_containers=$(docker compose -p "$project_name" ps -q)
        if [ -n "$running_containers" ]; then
            log_info "${YELLOW}🛑 Stopping $description...${NC}"
            
            if [ "$FORCE_STOP" = true ]; then
                # Force stop with kill
                docker compose -p "$project_name" -f "$compose_file" kill
                docker compose -p "$project_name" -f "$compose_file" down
            else
                # Graceful stop
                docker compose -p "$project_name" -f "$compose_file" down
            fi
            
            if [ $? -eq 0 ]; then
                log_info "${GREEN}✅ Stopped $description${NC}"
            else
                echo -e "${RED}❌ Failed to stop $description${NC}"
                return 1
            fi
        else
            log_info "${BLUE}ℹ️  $description has no running containers${NC}"
        fi
    else
        log_info "${BLUE}ℹ️  $description project not found${NC}"
    fi
    return 0
}

# Function to stop specific GPU workers
stop_gpu_workers() {
    local gpu_id=$1
    if [ "$gpu_id" = "0" ]; then
        stop_project "fr_workers_gpu0" "docker-compose_worker_gpu0.yaml" "GPU0 Workers"
    elif [ "$gpu_id" = "1" ]; then
        stop_project "fr_workers_gpu1" "docker-compose_worker_gpu1.yaml" "GPU1 Workers"
    fi
}

# Stop services based on options
if [ "$GPU0_ONLY" = true ]; then
    stop_gpu_workers "0"
elif [ "$GPU1_ONLY" = true ]; then
    stop_gpu_workers "1"
elif [ "$WORKERS_ONLY" = true ]; then
    stop_gpu_workers "1"
    stop_gpu_workers "0"
elif [ "$GUI_ONLY" = true ]; then
    stop_project "fr_gui" "docker-compose_gui.yaml" "GUI Services"
elif [ "$MAIN_ONLY" = true ]; then
    stop_project "fr_main" "docker-compose_main.yaml" "Main Services"
else
    # Stop all services in reverse order (default)
    stop_project "fr_workers_gpu1" "docker-compose_worker_gpu1.yaml" "GPU1 Workers"
    stop_project "fr_workers_gpu0" "docker-compose_worker_gpu0.yaml" "GPU0 Workers"
    stop_project "fr_gui" "docker-compose_gui.yaml" "GUI Services"
    stop_project "fr_main" "docker-compose_main.yaml" "Main Services"
fi

# # Optional cleanup
# if [ "$FORCE_CLEANUP" = true ]; then
#     log_info "${YELLOW}🧹 Performing cleanup...${NC}"
#     docker container prune -f > /dev/null 2>&1
#     docker network prune -f > /dev/null 2>&1
#     log_info "${GREEN}✅ Cleanup completed${NC}"
# else
#     if [ "$QUIET" = false ]; then
#         echo ""
#         read -p "Do you want to clean up orphaned containers and networks? (y/N): " -n 1 -r
#         echo
#         if [[ $REPLY =~ ^[Yy]$ ]]; then
#             echo -e "${YELLOW}🧹 Cleaning up orphaned resources...${NC}"
#             docker container prune -f
#             docker network prune -f
#             echo -e "${GREEN}✅ Cleanup completed${NC}"
#         fi
#     fi
# fi

# Final status
if [ "$QUIET" = false ]; then
    echo ""
    echo -e "${GREEN}✅ Stop operation completed!${NC}"
    echo ""
    echo "📊 Remaining Face Recognition containers:"
    remaining_containers=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep fr_ | wc -l)
    if [ "$remaining_containers" -gt 0 ]; then
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep fr_
        echo ""
        echo -e "${YELLOW}💡 Use '${CYAN}./stop-services.sh --force --cleanup${NC}${YELLOW}' for complete cleanup${NC}"
    else
        echo -e "${GREEN}   No Face Recognition containers are running${NC}"
    fi
    echo ""
    echo -e "🚀 To start services again: ${CYAN}./start-services.sh${NC}"
    echo -e "💡 For more options: ${CYAN}./stop-services.sh --help${NC}"
fi