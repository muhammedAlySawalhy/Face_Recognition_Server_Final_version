#!/bin/bash

# =============================================================================
# Face Recognition Server Project Initialization Script
# =============================================================================

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Project info
PROJECT_NAME="Face Recognition Server"
PROJECT_VERSION="v2.0"

# Clear screen and show header
clear
echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    Face Recognition Server Initialization                  ║"
echo "║                                   $PROJECT_VERSION                         ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}$(printf '=%.0s' {1..80})${NC}"
}

# Function to create directory if it doesn't exist
create_directory() {
    local dir_path="$1"
    local description="$2"
    
    if [ ! -d "$dir_path" ]; then
        echo -e "${YELLOW}📁 Creating: $dir_path${NC}"
        mkdir -p "$dir_path"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Created: $description${NC}"
        else
            echo -e "${RED}❌ Failed to create: $dir_path${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✅ Exists: $description${NC}"
    fi
    return 0
}

# Function to get user input with default value
get_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        echo -e "${CYAN}$prompt${NC} ${YELLOW}(default: $default)${NC}: "
    else
        echo -e "${CYAN}$prompt${NC}: "
    fi
    
    read -r input
    if [ -z "$input" ] && [ -n "$default" ]; then
        input="$default"
    fi
    
    eval "$var_name='$input'"
}

# Function to validate IP address
validate_ip() {
    local ip="$1"
    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        IFS='.' read -ra ADDR <<< "$ip"
        for i in "${ADDR[@]}"; do
            if [[ $i -gt 255 ]]; then
                return 1
            fi
        done
        return 0
    fi
    return 1
}

# Function to validate port number
validate_port() {
    local port="$1"
    if [[ $port =~ ^[0-9]+$ ]] && [ "$port" -ge 1 ] && [ "$port" -le 65535 ]; then
        return 0
    fi
    return 1
}

# Function to substitute variables in env.example template
substitute_env_variables() {
    local template_file="$1"
    local output_file="$2"
    
    # Read the template and substitute variables
    sed \
        -e "s|<server name>|$SERVER_NAME|g" \
        -e "s|<application data directory>|$DATA_DIR_NAME|g" \
        -e "s|<path to your project root>|$PROJECT_ROOT|g" \
        -e "s|<server manager port>|$SERVER_MANAGER_PORT|g" \
        -e "s|<server manager 1 IP>|$SERVER_MANAGER_1_IP|g" \
        -e "s|<server manager 2 IP>|$SERVER_MANAGER_2_IP|g" \
        -e "s|<gui origin IP>|$GUI_ORIGIN_IP|g" \
        -e "s|<gui origin port>|$GUI_ORIGIN_PORT|g" \
        -e "s|<excel file name>|${EXCEL_FILE_NAME}.xlsx|g" \
        -e "s|<your server IP or domain name>|$PROXY_SERVER_NAME|g" \
        -e "s|<your server lising port>|$PROXY_LISTEN_PORT|g" \
        -e "s|<ssl certificate common name>|$PROXY_SRV_CN|g" \
        -e "s|<ssl subject alternative names dns>|$PROXY_SAN_DNS|g" \
        -e "s|<ssl subject alternative names ip>|$PROXY_SAN_IP|g" \
        -e "s|<maximum client body size>|$PROXY_CLIENT_MAX_BODY_SIZE|g" \
        -e "s|<proxy read timeout>|$PROXY_READ_TIMEOUT|g" \
        -e "s|<proxy send timeout>|$PROXY_SEND_TIMEOUT|g" \
        "$template_file" > "$output_file" && sed -i 's/\r$//' $output_file
}

# Function to show help
show_help() {
    echo -e "${CYAN}${BOLD}Face Recognition Server - Project Initialization${NC}"
    echo -e "${CYAN}=================================================${NC}"
    echo ""
    echo -e "${BOLD}DESCRIPTION:${NC}"
    echo -e "  This script initializes a new Face Recognition Server project by:"
    echo -e "  • Setting up the complete directory structure"
    echo -e "  • Creating configuration files (.env, models_settings.yaml)"
    echo -e "  • Validating required Docker Compose files"
    echo -e "  • Preparing the environment for service deployment"
    echo ""
    echo -e "${BOLD}USAGE:${NC}"
    echo -e "  ${GREEN}./init-project.sh [OPTIONS]${NC}"
    echo ""
    echo -e "${BOLD}OPTIONS:${NC}"
    echo -e "  ${YELLOW}-h, --help${NC}           Show this help message"
    echo -e "  ${YELLOW}--interactive${NC}        Run in interactive mode (default)"
    echo -e "  ${YELLOW}--batch${NC}              Run in batch mode with defaults (no prompts)"
    echo -e "  ${YELLOW}--project-root PATH${NC}  Set project root directory"
    echo -e "  ${YELLOW}--server-name NAME${NC}   Set server name (default: server1)"
    echo -e "  ${YELLOW}--data-dir NAME${NC}      Set data directory name (default: Data)"
    echo -e "  ${YELLOW}--recreate-env${NC}       Force recreate .env file (overwrite existing)"
    echo -e "  ${YELLOW}--skip-models${NC}        Skip creating models_settings.yaml"
    echo -e "  ${YELLOW}--quiet${NC}              Minimize output messages"
    echo ""
    echo -e "${BOLD}EXAMPLES:${NC}"
    echo -e "  ${GREEN}./init-project.sh${NC}                              # Interactive setup"
    echo -e "  ${GREEN}./init-project.sh --help${NC}                       # Show this help"
    echo -e "  ${GREEN}./init-project.sh --batch${NC}                      # Quick setup with defaults"
    echo -e "  ${GREEN}./init-project.sh --recreate-env${NC}               # Recreate environment file"
    echo -e "  ${GREEN}./init-project.sh --project-root /opt/fr-server${NC} # Custom project location"
    echo -e "  ${GREEN}./init-project.sh --server-name production${NC}     # Custom server name"
    echo -e "  ${GREEN}./init-project.sh --batch --recreate-env${NC}       # Batch mode + recreate .env"
    echo ""
    echo -e "${BOLD}PREREQUISITES:${NC}"
    echo -e "  ${BLUE}Required Files:${NC}"
    echo -e "    • docker-compose_main.yaml        (Main services configuration)"
    echo -e "    • docker-compose_gui.yaml         (GUI services configuration)"
    echo -e "    • docker-compose_worker_gpu0.yaml (GPU0 worker configuration)"
    echo -e "    • docker-compose_worker_gpu1.yaml (GPU1 worker configuration)"
    echo -e "    • env.example                     (Environment template)"
    echo -e "    • nginx.conf.template             (Nginx configuration template)"
    echo ""
    echo -e "${BOLD}DIRECTORY STRUCTURE CREATED:${NC}"
    echo -e "  ${CYAN}📁 PROJECT_ROOT/${NC}"
    echo -e "  ${CYAN}├── Models_Weights/                    ${BLUE}# AI model weights${NC}"
    echo -e "  ${CYAN}│   ├── face_detection/               ${BLUE}# YOLO face detection models${NC}"
    echo -e "  ${CYAN}│   ├── face_recognition/              ${BLUE}# Face recognition models${NC}"
    echo -e "  ${CYAN}│   │   └── .deepface/weights/         ${BLUE}# DeepFace model cache${NC}"
    echo -e "  ${CYAN}│   ├── phone_detection/               ${BLUE}# Object detection models${NC}"
    echo -e "  ${CYAN}│   └── models_settings.yaml           ${BLUE}# Model configuration${NC}"
    echo -e "  ${CYAN}├── Data/                              ${BLUE}# Runtime data directory${NC}"
    echo -e "  ${CYAN}│   ├── logs/SERVER_NAME/              ${BLUE}# Service logs${NC}"
    echo -e "  ${CYAN}│   ├── Users_DataBase/                ${BLUE}# User database${NC}"
    echo -e "  ${CYAN}│   ├── Actions/                       ${BLUE}# Action logs${NC}"
    echo -e "  ${CYAN}│   │   ├── Lock_screen/               ${BLUE}# Lock screen actions${NC}"
    echo -e "  ${CYAN}│   │   └── Sign_out/                  ${BLUE}# Sign out actions${NC}"
    echo -e "  ${CYAN}│   ├── gui_data/                      ${BLUE}# GUI application data${NC}"
    echo -e "  ${CYAN}│   │   ├── approved/blocked/pending/  ${BLUE}# User status directories${NC}"
    echo -e "  ${CYAN}│   │   └── *.json files               ${BLUE}# User status files${NC}"
    echo -e "  ${CYAN}│   └── Server_Data/SERVER_NAME/       ${BLUE}# Server-specific data${NC}"
    echo -e "  ${CYAN}└── .env                               ${BLUE}# Environment configuration${NC}"
    echo ""
    echo -e "${BOLD}CONFIGURATION FILES GENERATED:${NC}"
    echo -e "  ${BLUE}.env File:${NC}                Contains environment variables for all services"
    echo -e "    • Server identification and paths"
    echo -e "    • Network configuration (IPs, ports)"
    echo -e "    • API endpoints and URLs"
    echo -e "    • Container mount points"
    echo ""
    echo -e "  ${BLUE}models_settings.yaml:${NC}     AI model configuration with device settings"
    echo -e "    • Model weight file paths"
    echo -e "    • GPU device assignments"
    echo -e "    • Detection thresholds"
    echo -e "    • Recognition parameters"
    echo ""
    echo -e "  ${BLUE}Initial JSON files:${NC}       Empty user status files for GUI service"
    echo -e "    • users.json, approved.json, blocked.json, pending.json"
    echo ""
    echo -e "${BOLD}BATCH MODE DEFAULTS:${NC}"
    echo -e "  ${BLUE}Project Root:${NC}          Current directory"
    echo -e "  ${BLUE}Server Name:${NC}           server1"
    echo -e "  ${BLUE}Data Directory:${NC}        Data"
    echo -e "  ${BLUE}Server Manager Port:${NC}   9000"
    echo -e "  ${BLUE}Server Manager 1 IP:${NC}   50.50.0.10"
    echo -e "  ${BLUE}Server Manager 2 IP:${NC}   50.50.1.10"
    echo -e "  ${BLUE}GUI Origin IP:${NC}         50.50.0.9"
    echo -e "  ${BLUE}GUI Origin Port:${NC}       3000"
    echo -e "  ${BLUE}Excel File Name:${NC}       users"
    echo ""
    echo -e "${BOLD}RECREATING .env FILE:${NC}"
    echo -e "  Use ${YELLOW}--recreate-env${NC} to overwrite an existing .env file with new configuration."
    echo -e "  This is useful when:"
    echo -e "    • Updating server configuration"
    echo -e "    • Changing network settings"
    echo -e "    • Migrating between environments"
    echo -e "    • Fixing corrupted environment files"
    echo ""
    echo -e "${BOLD}AFTER INITIALIZATION:${NC}"
    echo -e "  1. ${YELLOW}Review and customize the generated .env file${NC}"
    echo -e "  2. ${YELLOW}Place your AI model weights in Models_Weights/ subdirectories:${NC}"
    echo -e "     • face_detection/"
    echo -e "     • face_recognition/"
    echo -e "     • phone_detection/"
    echo -e "  3. ${YELLOW}Copy your Excel user database to Data/gui_data/users.xlsx${NC}"
    echo -e "  4. ${YELLOW}Start services: ${CYAN}./start-services.sh${NC}"
    echo ""
    echo -e "${BOLD}TROUBLESHOOTING:${NC}"
    echo -e "  • Ensure you run this script from the directory containing Docker Compose files"
    echo -e "  • Check that env.example exists and is properly formatted"
    echo -e "  • Verify you have write permissions in the target directory"
    echo -e "  • Use ${YELLOW}--project-root${NC} option if you want to install elsewhere"
    echo -e "  • Use ${YELLOW}--recreate-env${NC} if .env file seems corrupted"
    echo -e "  • Check Docker and NVIDIA Docker runtime installation"
    echo ""
    echo -e "${BOLD}RELATED COMMANDS:${NC}"
    echo -e "  ${CYAN}./start-services.sh --help${NC}       # Service management help"
    echo -e "  ${CYAN}./stop-services.sh --help${NC}        # Service stopping help"
    echo -e "  ${CYAN}docker compose ls${NC}                # List running services"
    echo -e "  ${CYAN}nvidia-smi${NC}                       # Check GPU availability"
    echo ""
}

# Parse command line arguments
INTERACTIVE_MODE=true
BATCH_MODE=false
PROJECT_ROOT=""
SERVER_NAME_ARG=""
DATA_DIR_ARG=""
RECREATE_ENV=false
SKIP_MODELS=false
QUIET=false
NGINX_TEMPLATE_FILES_PATH="config_templates"
ENV_TEMPLIT_FILE_PATH="config_templates"
ENV_TEMPLIT_FILE_NAME="env.example"
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --interactive)
            INTERACTIVE_MODE=true
            BATCH_MODE=false
            shift
            ;;
        --env-templite-file-path)
            ENV_TEMPLIT_FILE_PATH="$2"
            shift 2
            ;;
        --env-templite-file-name)
            ENV_TEMPLIT_FILE_NAME="$2"
            shift 2
            ;;
        --nginx-template-files-path)
            NGINX_TEMPLATE_FILES_PATH="$2"
            shift 2
            ;;
        --batch)
            BATCH_MODE=true
            INTERACTIVE_MODE=false
            shift
            ;;
        --project-root)
            PROJECT_ROOT="$2"
            shift 2
            ;;
        --server-name)
            SERVER_NAME_ARG="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR_ARG="$2"
            shift 2
            ;;
        --recreate-env)
            RECREATE_ENV=true
            shift
            ;;
        --skip-models)
            SKIP_MODELS=true
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

# Clear screen and show header (only in interactive mode)
if [ "$INTERACTIVE_MODE" = true ] && [ "$QUIET" = false ]; then
    clear
fi

echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    Face Recognition Server Initialization                  ║"
echo "║                               $PROJECT_VERSION                             ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Show mode information
if [ "$BATCH_MODE" = true ]; then
    log_info "${YELLOW}🚀 Running in BATCH MODE with default values${NC}"
    [ "$RECREATE_ENV" = true ] && log_info "${YELLOW}🔄 Will recreate .env file${NC}"
    log_info "${BLUE}Use ${CYAN}--help${NC}${BLUE} to see available options${NC}"
    echo ""
else
    log_info "${YELLOW}🔧 Running in INTERACTIVE MODE${NC}"
    [ "$RECREATE_ENV" = true ] && log_info "${YELLOW}🔄 Will recreate .env file${NC}"
    log_info "${BLUE}Use ${CYAN}--batch${NC}${BLUE} for quick setup with defaults${NC}"
    echo ""
fi

print_section "📋 STEP 1: PROJECT DIRECTORY STRUCTURE SETUP"

# Get project root directory from user
CURRENT_DIR=$(pwd)
echo -e "${BLUE}Current directory: ${CYAN}$CURRENT_DIR${NC}"
echo ""

get_input "Project Root Directory" "$CURRENT_DIR" "PROJECT_ROOT"
while [ -z "$PROJECT_ROOT" ]; do
    echo -e "${RED}❌ Project root cannot be empty${NC}"
    get_input "Project Root Directory" "$CURRENT_DIR" "PROJECT_ROOT"
done

# Expand tilde and resolve path
PROJECT_ROOT=$(eval echo "$PROJECT_ROOT")
PROJECT_ROOT=$(realpath "$PROJECT_ROOT" 2>/dev/null || echo "$PROJECT_ROOT")

# Create project root if it doesn't exist
if [ ! -d "$PROJECT_ROOT" ]; then
    echo -e "${YELLOW}📁 Project root doesn't exist. Creating: $PROJECT_ROOT${NC}"
    mkdir -p "$PROJECT_ROOT"
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to create project root directory${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}📍 Project Root: $PROJECT_ROOT${NC}"



# Verify required files exist
echo -e "${BLUE}🔍 Verifying required files...${NC}"

required_files=("${CURRENT_DIR}/docker-compose_main.yaml" \
                "${CURRENT_DIR}/docker-compose_gui.yaml" \
                "${CURRENT_DIR}/docker-compose_worker_gpu0.yaml" \
                "${CURRENT_DIR}/docker-compose_worker_gpu1.yaml" \
                "${CURRENT_DIR}/${ENV_TEMPLIT_FILE_PATH}/${ENV_TEMPLIT_FILE_NAME}" \
                "${CURRENT_DIR}/${NGINX_TEMPLATE_FILES_PATH}/nginx.conf.template"\
                "${CURRENT_DIR}/${NGINX_TEMPLATE_FILES_PATH}/site.conf.template")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
        echo -e "${RED}❌ Missing: $file${NC}"
    else
        echo -e "${GREEN}✅ Found: $file${NC}"
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo -e "\n${RED}❌ Error: Required files are missing from project root${NC}"
    echo -e "${RED}   Missing files: ${missing_files[*]}${NC}"
    echo -e "${RED}   Please ensure all project files are in the specified directory${NC}"
    exit 1
fi

# Check if we need to copy files to the new project root
if [ "$PROJECT_ROOT" != "$CURRENT_DIR" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Project root is different from current directory${NC}"
    echo -e "${BLUE}Current directory: $CURRENT_DIR${NC}"
    echo -e "${BLUE}Project root: $PROJECT_ROOT${NC}"
    echo ""
    
    # Check if project root is empty or has docker-compose files
    if [ ! -f "$PROJECT_ROOT/docker-compose_main.yaml" ]; then
        echo -e "${YELLOW}Docker Compose files not found in project root.${NC}"
        read -p "Do you want to copy files from current directory to project root? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}📦 Copying project files...${NC}"
            cp -r "$CURRENT_DIR"/* "$PROJECT_ROOT/" 2>/dev/null || true
            cp -r "$CURRENT_DIR"/.* "$PROJECT_ROOT/" 2>/dev/null || true
            echo -e "${GREEN}✅ Files copied to project root${NC}"
        else
            echo -e "${RED}❌ Cannot proceed without Docker Compose files in project root${NC}"
            exit 1
        fi
    fi
fi

# Change to project root directory
cd "$PROJECT_ROOT" || {
    echo -e "${RED}❌ Cannot access project root directory${NC}"
    exit 1
}


echo -e "${GREEN}✅ All required files found${NC}"

# Collect configuration from user
print_section "⚙️  STEP 2: ENVIRONMENT CONFIGURATION"

echo -e "${YELLOW}Please provide the following configuration details:${NC}\n"

# Server Name
get_input "Server Name" "server1" "SERVER_NAME"
while [ -z "$SERVER_NAME" ]; do
    echo -e "${RED}❌ Server name cannot be empty${NC}"
    get_input "Server Name" "server1" "SERVER_NAME"
done

# Data Directory
get_input "Data Directory (relative to '$PROJECT_ROOT')" "Data" "DATA_DIR_NAME"
while [ -z "$DATA_DIR_NAME" ]; do
    echo -e "${RED}❌ Data directory cannot be empty${NC}"
    get_input "Data Directory (relative to project root)" "Data" "DATA_DIR_NAME"
done

DATA_DIR="$PROJECT_ROOT/$DATA_DIR_NAME"

# Server Manager Port
get_input "Server Manager Port" "9000" "SERVER_MANAGER_PORT"
while ! validate_port "$SERVER_MANAGER_PORT"; do
    echo -e "${RED}❌ Invalid port number. Please enter a port between 1-65535${NC}"
    get_input "Server Manager Port" "9000" "SERVER_MANAGER_PORT"
done

# Server Manager IPs
get_input "Server Manager 1 IP" "50.50.0.10" "SERVER_MANAGER_1_IP"
while ! validate_ip "$SERVER_MANAGER_1_IP"; do
    echo -e "${RED}❌ Invalid IP address format${NC}"
    get_input "Server Manager 1 IP" "50.50.0.10" "SERVER_MANAGER_1_IP"
done

get_input "Server Manager 2 IP" "50.50.1.10" "SERVER_MANAGER_2_IP"
while ! validate_ip "$SERVER_MANAGER_2_IP"; do
    echo -e "${RED}❌ Invalid IP address format${NC}"
    get_input "Server Manager 2 IP" "50.50.1.10" "SERVER_MANAGER_2_IP"
done

# GUI Configuration
get_input "GUI Origin IP" "50.50.0.9" "GUI_ORIGIN_IP"
while ! validate_ip "$GUI_ORIGIN_IP"; do
    echo -e "${RED}❌ Invalid IP address format${NC}"
    get_input "GUI Origin IP" "50.50.0.9" "GUI_ORIGIN_IP"
done

get_input "GUI Origin Port" "3000" "GUI_ORIGIN_PORT"
while ! validate_port "$GUI_ORIGIN_PORT"; do
    echo -e "${RED}❌ Invalid port number${NC}"
    get_input "GUI Origin Port" "3000" "GUI_ORIGIN_PORT"
done

get_input "Excel File Name (without .xlsx extension)" "users" "EXCEL_FILE_NAME"
while [ -z "$EXCEL_FILE_NAME" ]; do
    echo -e "${RED}❌ Excel file name cannot be empty${NC}"
    get_input "Excel File Name (without .xlsx extension)" "users" "EXCEL_FILE_NAME"
done

# Proxy Configuration
echo -e "\n${BLUE}🔒 Proxy Service Configuration:${NC}"

get_input "Proxy Server Name/IP (for SSL certificates)" "50.50.0.9" "PROXY_SERVER_NAME"
while [ -z "$PROXY_SERVER_NAME" ]; do
    echo -e "${RED}❌ Proxy server name cannot be empty${NC}"
    get_input "Proxy Server Name/IP (for SSL certificates)" "50.50.0.9" "PROXY_SERVER_NAME"
done

get_input "Proxy Listen Port" "443" "PROXY_LISTEN_PORT"
while ! validate_port "$PROXY_LISTEN_PORT"; do
    echo -e "${RED}❌ Invalid port number${NC}"
    get_input "Proxy Listen Port" "443" "PROXY_LISTEN_PORT"
done

get_input "SSL Certificate Common Name" "gui.internal" "PROXY_SRV_CN"
while [ -z "$PROXY_SRV_CN" ]; do
    echo -e "${RED}❌ SSL CN cannot be empty${NC}"
    get_input "SSL Certificate Common Name" "gui.internal" "PROXY_SRV_CN"
done

get_input "SSL Subject Alternative Names (DNS)" "gui.internal,localhost" "PROXY_SAN_DNS"
get_input "SSL Subject Alternative Names (IP)" "50.50.0.9,127.0.0.1" "PROXY_SAN_IP"

# Nginx Configuration Parameters
echo -e "\n${BLUE}⚙️  Nginx Configuration Parameters:${NC}"

get_input "Maximum Client Body Size" "100M" "PROXY_CLIENT_MAX_BODY_SIZE"
get_input "Proxy Read Timeout" "300s" "PROXY_READ_TIMEOUT"
get_input "Proxy Send Timeout" "300s" "PROXY_SEND_TIMEOUT"

print_section "📁 STEP 3: CREATING DIRECTORY STRUCTURE"

# Create main data directory
create_directory "$DATA_DIR" "Main data directory"

# Create subdirectories based on Docker Compose volume mounts
echo -e "\n${BLUE}Creating application subdirectories...${NC}"

# Main service directories
create_directory "$DATA_DIR/logs" "Logs directory"
create_directory "$DATA_DIR/logs/$SERVER_NAME" "Server-specific logs"

# GUI service directories
create_directory "$DATA_DIR/Users_DataBase" "Users database"
create_directory "$DATA_DIR/Actions" "Actions data"
create_directory "$DATA_DIR/gui_data" "GUI data"
create_directory "$DATA_DIR/gui_data/approved" "Approved users"
create_directory "$DATA_DIR/gui_data/blocked" "Blocked users"
create_directory "$DATA_DIR/gui_data/pending" "Pending users"

# Action subdirectories
create_directory "$DATA_DIR/Actions/Lock_screen" "Lock screen actions"
create_directory "$DATA_DIR/Actions/Sign_out" "Lock screen actions"

# Server data directories
create_directory "$DATA_DIR/Server_Data" "Server data"
create_directory "$DATA_DIR/Server_Data/$SERVER_NAME" "Server-specific data"

# =============================================================================
# PROXY SERVICE DIRECTORIES (for docker-compose_gui.yaml)
# =============================================================================
echo -e "\n${BLUE}Creating proxy service directories...${NC}"

# Create certs directory for SSL certificates (proxy service)
create_directory "$PROJECT_ROOT/certs" "SSL certificates directory"

# Create Models_Weights directory if it doesn't exist
create_directory "$PROJECT_ROOT/Models_Weights" "AI Models weights"
create_directory "$PROJECT_ROOT/Models_Weights/face_detection" "Face detection models"
create_directory "$PROJECT_ROOT/Models_Weights/face_recognition" "Face recognition models"
create_directory "$PROJECT_ROOT/Models_Weights/face_recognition/.deepface/weights" "Face recognition deepface models"
create_directory "$PROJECT_ROOT/Models_Weights/phone_detection" "Phone detection models"

# Create initial files
echo -e "\n${BLUE}Creating initial configuration files...${NC}"

# Create models_settings.yaml if it doesn't exist
if [ ! -f "$PROJECT_ROOT/Models_Weights/models_settings.yaml" ]; then
    echo -e "${YELLOW}📄 Creating models_settings.yaml${NC}"
    cat > "$PROJECT_ROOT/Models_Weights/models_settings.yaml" << 'EOF'
# =============================================================================
# AI Models Configuration File
# =============================================================================
# This file contains all configuration parameters for the Face Recognition
# and Object Detection AI models used in the system.
#
# Structure follows the original JSON format with added descriptions and
# optional values for better maintainability and understanding.
# =============================================================================

# =============================================================================
# MODEL WEIGHTS AND PATHS CONFIGURATION
# =============================================================================

# Directory containing all model weight files
# Type: string | Required: true
# Description: Base directory path where all model weights are stored
Models_Weights_dir: "Models_Weights"

# Object Detection Model Weights
# Type: string | Required: true
# Description: Filename of the YOLO model for phone/object detection
# Supported formats: .pt (PyTorch weights)
# Default model: YOLOv8 trained for phone detection (class 67)
ObjectDetection_model_weights: "phone_detection.pt"

# Face Detection Model Weights  
# Type: string | Required: true
# Description: Filename of the YOLO model specifically trained for face detection
# Supported formats: .pt (PyTorch weights)
# Architecture: YOLOv8 customized for face detection
FaceDetection_model_weights: "yolov8_model.pt"

# Face Recognition Model Weights
# Type: string | Required: true
# Description: Filename of the face recognition model weights
# Supported formats: .h5 (TensorFlow/Keras), .pth (PyTorch), .pt
# Available models: 'vgg_face_weights.h5','vggface2.pt'
FaceRecognition_model_weights: "vggface2.pt"

# Anti-Spoofing Model Weights
# Type: string | Required: false | Default: null
# Description: Filename of the anti-spoofing detection model
# Set to null to disable anti-spoofing functionality
# Supported models: FasNet-based CNN architectures
FaceSpoofChecker_model_weights: null

# =============================================================================
# DEVICE CONFIGURATION
# =============================================================================

# Object Detection Device
# Type: string | Required: true | Default: "cpu"
# Description: Computing device for object/phone detection models
# Options: "cpu", "cuda:0", "cuda:1", etc.
# Performance: GPU recommended for real-time processing
Object_Detection_Models_device: "cuda:0"

# Face Detection Device
# Type: string | Required: true | Default: "cpu"  
# Description: Computing device for face detection model
# Options: "cpu", "cuda:0", "cuda:1", etc.
# Performance: GPU recommended for real-time processing
Face_Detection_Model_device: "cuda:0"

# Face Recognition Device
# Type: string | Required: true | Default: "cpu"
# Description: Computing device for face recognition model
# ⚠️  CRITICAL: TensorFlow-based models REQUIRE GPU - cannot run on CPU
# Options: "GPU:0", "GPU:1", "GPU:2", etc. (TensorFlow format)
# Options: "cuda:0", "cuda:1", "cuda:2", etc. (PyTorch format)
# Hardware Requirement: NVIDIA GPU with CUDA support mandatory
Face_Recognition_Model_device: "cuda:0"

# Anti-Spoofing Device
# Type: string | Required: true | Default: "cpu"
# Description: Computing device for anti-spoofing detection
# Options: "cpu", "cuda:0", "cuda:1", etc.
# Performance: GPU recommended for optimal accuracy
spoof_Models_device: "cuda:0"

# =============================================================================
# FACE RECOGNITION MODEL CONFIGURATION
# =============================================================================

# Recognition Model Architecture
# Type: string | Required: true | Default: "VGG-Face"
# Description: Specifies which face recognition model architecture to use
# Supported Models:
#   DeepFace library models:
#     - "deepface__VGG_Face"    : Classic VGG-Face model (224x224 input)
#     - "deepface__r18"         : IResNet-18 (112x112 input)
#     - "deepface__r34"         : IResNet-34 (112x112 input) 
#     - "deepface__r50"         : IResNet-50 (112x112 input)
#     - "deepface__r100"        : IResNet-100 (112x112 input) - Recommended
#   FaceNet library models:
#     - "facenet__vggface2"     : InceptionResnetV1 pre-trained on VGGFace2 (120x120)
#     - "facenet__casia-webface": InceptionResnetV1 pre-trained on CASIA-WebFace (120x120)
# Format: "library__architecture" (double underscore separator)
Recognition_model_name: "facenet__vggface2"

# Recognition Similarity Metric
# Type: string | Required: true | Default: "cosine_similarity"
# Description: Distance/similarity metric for face comparison
# Options:
#   - "cosine_similarity": Measures angular similarity (0-1, higher = more similar)
#   - "euclidean": Measures Euclidean distance (lower = more similar)
# Recommendation: cosine_similarity for most face recognition tasks
Recognition_Metric: "euclidean"

# =============================================================================
# DETECTION CLASS AND THRESHOLDS CONFIGURATION
# =============================================================================

# Object Detection Class Number
# Type: integer | Required: true | Default: 67
# Description: COCO dataset class ID for target object detection
# Common Classes:
#   - 67: Cell phone/Mobile phone
#   - 0:  Person
#   - 32: Sports ball
#   - 39: Bottle
# Range: 0-79 (COCO dataset classes)
Object_class_number: 67

# Face Recognition Threshold
# Type: float | Required: true
# Description: Minimum similarity/distance threshold for face verification
# Cosine Similarity: 0.3 (higher values = stricter matching)
# Euclidean Distance: 1.2 (lower = stricter matching)
Recognition_Threshold: 1.25

# Object Detection Confidence Threshold
# Type: integer | Required: true | Default: 65
# Description: Minimum confidence percentage for object detection
# Range: 0-100 (percentage)
# Values:
#   - 50-65: Lenient detection (more objects detected, more false positives)
#   - 66-80: Balanced detection (recommended)
#   - 81-95: Strict detection (fewer false positives, may miss some objects)
Object_threshold: 65

# Anti-Spoofing Detection Threshold  
# Type: float | Required: true | Default: 0.99
# Description: Minimum confidence for classifying face as "real" vs "spoofed"
# Range: 0.0-1.0 (higher values = stricter anti-spoofing)
# Values:
#   - 0.5-0.7: Lenient (may allow some spoofed faces)
#   - 0.8-0.9: Balanced (recommended for most applications)
#   - 0.95-0.99: Very strict (maximum security, may reject some real faces)
Anti_Spoof_threshold: 0.99
# =============================================================================
EOF
    echo -e "${GREEN}✅ Created models_settings.yaml${NC}"
fi

# Create initial GUI data files
if [ ! -f "$DATA_DIR/gui_data/users.json" ]; then
    echo -e "${YELLOW}📄 Creating initial users.json${NC}"
    echo '[]' > "$DATA_DIR/gui_data/users.json"
    echo -e "${GREEN}✅ Created users.json${NC}"
fi

for status in approved blocked pending; do
    if [ ! -f "$DATA_DIR/gui_data/$status.json" ]; then
        echo -e "${YELLOW}📄 Creating $status.json${NC}"
        echo '[]' > "$DATA_DIR/gui_data/$status.json"
        echo -e "${GREEN}✅ Created $status.json${NC}"
    fi
done

# Create initial Excel file
if [ ! -f "$DATA_DIR/gui_data/$EXCEL_FILE_NAME.xlsx" ]; then
    echo -e "${YELLOW}📄 Creating placeholder for $EXCEL_FILE_NAME.xlsx${NC}"
    echo -e "${BLUE}   Note: You'll need to provide the actual Excel file${NC}"
fi

print_section "🔧 STEP 4: GENERATING .env FILE"

# Check if .env exists and handle recreation
ENV_FILE=".env"

if [ -f "$ENV_FILE" ] && [ "$RECREATE_ENV" = false ]; then
    if [ "$BATCH_MODE" = false ]; then
        echo -e "${YELLOW}⚠️  .env file already exists!${NC}"
        echo -e "${BLUE}Current .env file will be backed up before creating new one.${NC}"
        read -p "Do you want to recreate the .env file? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "${BLUE}ℹ️  Keeping existing .env file${NC}"
            # Skip to final verification
            print_section "🚀 STEP 5: FINAL VERIFICATION"
            
            if [ -f "$ENV_FILE" ]; then
                log_info "${GREEN}✅ Environment file exists${NC}"
            else
                echo -e "${RED}❌ Environment file missing${NC}"
                exit 1
            fi
            
            # Show summary and exit
            print_section "📊 SETUP SUMMARY"
            echo -e "${GREEN}✅ Project directories verified!${NC}"
            echo -e "${BLUE}ℹ️  Using existing .env configuration${NC}"
            echo -e "\n${GREEN}${BOLD}Project is ready for deployment! 🎉${NC}"
            exit 0
        fi
        RECREATE_ENV=true
    else
        # In batch mode, don't recreate unless explicitly requested
        if [ "$RECREATE_ENV" = false ]; then
            log_info "${BLUE}ℹ️  .env file exists, keeping existing (use --recreate-env to overwrite)${NC}"
            print_section "🚀 FINAL VERIFICATION"
            log_info "${GREEN}✅ Using existing .env file${NC}"
            echo -e "\n${GREEN}${BOLD}Project is ready for deployment! 🎉${NC}"
            exit 0
        fi
    fi
fi

# Backup existing .env if recreating
if [ -f "$ENV_FILE" ] && [ "$RECREATE_ENV" = true ]; then
    backup_file="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$backup_file"
    log_info "${YELLOW}📋 Backed up existing .env to: $backup_file${NC}"
fi

# Generate .env file from template
log_info "${YELLOW}📝 Creating $ENV_FILE file from env.example template...${NC}"

# Use the substitute function to create .env from env.example
substitute_env_variables "${ENV_TEMPLIT_FILE_PATH}/${ENV_TEMPLIT_FILE_NAME}" "$ENV_FILE"

if [ $? -eq 0 ]; then
    log_info "${GREEN}✅ Created $ENV_FILE file from template${NC}"
else
    echo -e "${RED}❌ Failed to create .env file from template${NC}"
    exit 1
fi

print_section "🚀 STEP 5: FINAL VERIFICATION"

# Verify .env file
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ Environment file created successfully${NC}"
else
    echo -e "${RED}❌ Failed to create environment file${NC}"
    exit 1
fi

# Show summary
print_section "📊 SETUP SUMMARY"

echo -e "${GREEN}✅ Project initialization completed successfully!${NC}\n"
echo -e "${BOLD}Project Configuration:${NC}"
echo -e "  📁 Project Root: ${CYAN}$PROJECT_ROOT${NC}"
echo -e "  📁 Data Directory: ${CYAN}$DATA_DIR${NC}"
echo -e "  🖥️  Server Name: ${CYAN}$SERVER_NAME${NC}"
echo -e "  🌐 Server Manager Port: ${CYAN}$SERVER_MANAGER_PORT${NC}"
echo -e "  🔗 Server Manager 1 IP: ${CYAN}$SERVER_MANAGER_1_IP${NC}"
echo -e "  🔗 Server Manager 2 IP: ${CYAN}$SERVER_MANAGER_2_IP${NC}"
echo -e "  🖼️  GUI Origin: ${CYAN}$GUI_ORIGIN_IP:$GUI_ORIGIN_PORT${NC}"

echo -e "\n${BOLD}Next Steps:${NC}"
echo -e "  1. ${YELLOW}Review the generated .env file and adjust if needed${NC}"
echo -e "  2. ${YELLOW}Place your AI model weights in: ${CYAN}$PROJECT_ROOT/Models_Weights/${NC}"
echo -e "  3. ${YELLOW}Copy your Excel file to: ${CYAN}$DATA_DIR/gui_data/$EXCEL_FILE_NAME.xlsx${NC}"
echo -e "  4. ${YELLOW}Start the services:${NC}"
echo -e "     ${CYAN}./start-services.sh${NC}"

echo -e "\n${BOLD}Configuration Files:${NC}"
echo -e "  📄 Environment: ${CYAN}.env${NC}"
echo -e "  🐳 Docker Compose: ${CYAN}docker-compose_*.yaml${NC}"
echo -e "  📋 Models Config: ${CYAN}Models_Weights/models_settings.yaml${NC}"

echo -e "\n${GREEN}${BOLD}Project is ready for deployment! 🎉${NC}"

# Make scripts executable
echo -e "\n${BLUE}Making scripts executable...${NC}"
chmod +x start-services.sh stop-services.sh
echo -e "${GREEN}✅ Scripts are now executable${NC}"

echo -e "\n${YELLOW}Tip: Run '${CYAN}./start-services.sh --help${NC}${YELLOW}' for service management options${NC}"