#! /bin/bash
PYTHON_VERSION="3.10"
DEBIAN_VERSION="bookworm"
NODE_VERSION="20"
CUDA_VERSION="11.8.0"
UBUNTU_VERSION="22.04"
SERVICE_NAME=""
IMAGE_VERSION="v1.0"
BUILD_ALL=false
USE_OPTIMIZED=false

# Available services
ALL_SERVICES=(
    "server_manager_service"
    "decision_manager_service"
    "gateway_server_service"
    "pipelines_manager_service"
    "pipeline_worker_service"
    "face_ingest_service"
    "fr_server_load_balancing"
    "gui_proxy_service"
    "mirando_gui"
)

resolve_service_dir() {
    local service_name="$1"
    if [[ "$service_name" == "mirando_gui" ]]; then
        echo "./services/Mirando-GUI"
        return 0
    fi
    if [[ "$service_name" == "face_ingest_service" ]]; then
        echo "./services/Face_Ingest_Service"
        return 0
    fi
    local candidates=("./$service_name" "./services/$service_name")

    for dir in "${candidates[@]}"; do
        if [[ -d "$dir" ]]; then
            echo "$dir"
            return 0
        fi
    done

    echo ""
    return 1
}

help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --python-version <version>   Specify the Python version (default: 3.10)"
    echo "  --debian-version <version>   Specify the Debian version (default: bookworm)"
    echo "  --node-version <version>     Specify the Node.js version (default: 20)"
    echo "  --cuda-version <version>     Specify the CUDA version (default: 11.8.0)"
    echo "  --ubuntu-version <version>   Specify the Ubuntu version (default: 22.04)"
    echo "  --service-name <name>        Specify the service name to build"
    echo "  --image-version <version>    Specify the docker image version (default: v1.0)"
    echo "  --all                        Build all services"
    echo "  --optimized                  Use optimized Dockerfile for pipeline_worker_service (if available)"
    echo "  --help                       Show this help message"
    echo ""
    echo "Available services:"
    for service in "${ALL_SERVICES[@]}"; do
        echo "  - $service"
    done
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            help
            exit 0
            ;;
        --python-version)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        --debian-version)
            DEBIAN_VERSION="$2"
            shift 2
            ;;
        --node-version)
            NODE_VERSION="$2"
            shift 2
            ;;
        --cuda-version)
            CUDA_VERSION="$2"
            shift 2
            ;;
        --ubuntu-version)
            UBUNTU_VERSION="$2"
            shift 2
            ;;
        --service-name)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --image-version)
            IMAGE_VERSION="$2"
            # Add 'v' prefix if not present
            if [[ ! "$IMAGE_VERSION" =~ ^v ]]; then
                IMAGE_VERSION="v$IMAGE_VERSION"
            fi
            shift 2
            ;;
        --all)
            BUILD_ALL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "See help for the available options."
            help
            exit 1
            ;;
    esac
done

# Validation
if [[ "$BUILD_ALL" == "false" && -z "$SERVICE_NAME" ]]; then
    echo "Error: Either --service-name is required or use --all to build all services"
    echo "Use --help to see available options"
    exit 1
fi

if [[ "$BUILD_ALL" == "true" && -n "$SERVICE_NAME" ]]; then
    echo "Error: Cannot use both --all and --service-name options together"
    echo "Use --help to see available options"
    exit 1
fi

# Validate service name if specified
if [[ -n "$SERVICE_NAME" ]]; then
    if [[ ! " ${ALL_SERVICES[@]} " =~ " ${SERVICE_NAME} " ]]; then
        echo "Error: Invalid service name '$SERVICE_NAME'"
        echo "Available services: ${ALL_SERVICES[*]}"
        exit 1
    fi

    SERVICE_DIR_PATH=$(resolve_service_dir "$SERVICE_NAME")
    if [[ -z "$SERVICE_DIR_PATH" ]]; then
        echo "Error: Service directory '$SERVICE_NAME' does not exist"
        exit 1
    fi

    if [ ! -f "$SERVICE_DIR_PATH/Dockerfile" ]; then
        echo "Error: Dockerfile not found in service directory '$SERVICE_NAME'"
        exit 1
    fi
fi
build_service(){
    local service_name="$1"
    local log_file="${service_name}_build.log"
    local image_name="fr-server-$service_name:$IMAGE_VERSION"
    local service_dir
    local service_build_arg
    local build_context="."

    service_dir=$(resolve_service_dir "$service_name")
    if [[ -z "$service_dir" ]]; then
        echo "Error: Service directory for '$service_name' not found"
        return 1
    fi
    service_build_arg="${service_dir#./}"

    # For the Mirando GUI we build with its directory as the context so COPY finds package.json/entrypoint
    if [[ "$service_name" == "mirando_gui" ]]; then
        build_context="$service_dir"
    fi
    
    # Determine build arguments based on service type
    local build_args=""
    case "$service_name" in
        "mirando_gui")
            image_name="fr-mirando-gui:$IMAGE_VERSION"
            build_args=""
            ;;
        "gui_proxy_service")
            image_name="fr_gui_server_proxy:$IMAGE_VERSION"
            build_args=""
            ;;
        "face_ingest_service")
            image_name="fr-face-ingestor:$IMAGE_VERSION"
            build_args=""
            ;;
        "fr_server_load_balancing")
            # Build and tag for the NGINX load balancer
            image_name="fr_loadbalance:${IMAGE_VERSION#v}"
            build_args=""
            ;;
        "pipeline_worker_service")
            build_args="--build-arg CUDA_VERSION=\"$CUDA_VERSION\" --build-arg UBUNTU_VERSION=\"$UBUNTU_VERSION\" --build-arg PYTHON_VERSION=\"$PYTHON_VERSION\" --build-arg SERVICE_NAME=\"$service_build_arg\""
            ;;
        *)
            build_args="--build-arg PYTHON_VERSION=\"$PYTHON_VERSION\" --build-arg DEBIAN_VERSION=\"$DEBIAN_VERSION\" --build-arg SERVICE_NAME=\"$service_build_arg\""
            ;;
    esac
    
    echo "Building service: $service_name"
    echo "Image name: $image_name"
    echo "Log file: $log_file"
    
    # Build the Docker image
    eval "docker build $build_args -t \"$image_name\" -f \"$service_dir/Dockerfile\" \"$build_context\" > \"$log_file\" 2>&1"
    local build_result=$?
    
    if [ $build_result -eq 0 ]; then
        echo "✅ Docker image '$image_name' built successfully."
        
        # Get image size
        local image_size=$(docker images "$image_name" --format "{{.Size}}" 2>/dev/null)
        if [ -n "$image_size" ]; then
            echo "   Image size: $image_size"
        fi
        
        # Tag as latest
        local latest_tag="fr-server-$service_name:latest"
        case "$service_name" in
            "mirando_gui")
                latest_tag="fr-mirando-gui:latest"
                ;;
            "gui_proxy_service")
                latest_tag="fr_gui_server_proxy:latest"
                ;;
            "face_ingest_service")
                latest_tag="fr-face-ingestor:latest"
                ;;
            "fr_server_load_balancing")
                latest_tag="fr_loadbalance:latest"
                # Also tag the legacy name used in docker-compose
                docker tag "$image_name" "fr_loadbalance:0"
                echo "   Tagged as 'fr_loadbalance:0'"
                ;;
        esac
        docker tag "$image_name" "$latest_tag"
        echo "   Tagged as '$latest_tag'"
        
        echo "   Build log saved to: $log_file"
        return 0
    else
        echo "❌ Error: Failed to build Docker image '$image_name'."
        echo "   Check the log file for details: $log_file"
        return 1
    fi
}

build_all_services(){
    local failed_services=()
    local successful_services=()
    local start_time=$(date +%s)
    
    echo "========================================="
    echo "Building All Services"
    echo "========================================="
    echo "Python Version: $PYTHON_VERSION"
    echo "Debian Version: $DEBIAN_VERSION"
    echo "Node Version: $NODE_VERSION"
    echo "CUDA Version: $CUDA_VERSION"
    echo "Ubuntu Version: $UBUNTU_VERSION"
    echo "Image Version: $IMAGE_VERSION"
    echo "Total Services: ${#ALL_SERVICES[@]}"
    echo "========================================="
    
    for service in "${ALL_SERVICES[@]}"; do
        echo ""
        echo "[$((${#successful_services[@]} + ${#failed_services[@]} + 1))/${#ALL_SERVICES[@]}] Processing: $service"
        echo "-----------------------------------------"
        
        if build_service "$service"; then
            successful_services+=("$service")
        else
            failed_services+=("$service")
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo ""
    echo "========================================="
    echo "Build Summary"
    echo "========================================="
    echo "Total time: ${minutes}m ${seconds}s"
    echo "Successful builds: ${#successful_services[@]}"
    echo "Failed builds: ${#failed_services[@]}"
    echo ""
    
    if [ ${#successful_services[@]} -gt 0 ]; then
        echo "✅ Successfully built services:"
        for service in "${successful_services[@]}"; do
            echo "   - $service"
        done
        echo ""
    fi
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        echo "❌ Failed to build services:"
        for service in "${failed_services[@]}"; do
            echo "   - $service"
        done
        echo ""
        return 1
    fi
    
    echo "🎉 All services built successfully!"
    return 0
}
# Main execution
if [[ "$BUILD_ALL" == "true" ]]; then
    # Build all services
    if build_all_services; then
        echo "All services completed successfully!"
        exit 0
    else
        echo "Some services failed to build. Check individual log files for details."
        exit 1
    fi
else
    # Build single service
    echo "========================================="
    echo "Building Single Service"
    echo "========================================="
    echo "Service: $SERVICE_NAME"
    echo "Python Version: $PYTHON_VERSION"
    echo "Debian Version: $DEBIAN_VERSION"
    echo "Node Version: $NODE_VERSION"
    echo "CUDA Version: $CUDA_VERSION"
    echo "Ubuntu Version: $UBUNTU_VERSION"
    echo "Image Version: $IMAGE_VERSION"
    echo "========================================="
    echo ""
    
    if build_service "$SERVICE_NAME"; then
        echo ""
        echo "🎉 Service '$SERVICE_NAME' built successfully!"
        exit 0
    else
        echo ""
        echo "❌ Failed to build service '$SERVICE_NAME'."
        exit 1
    fi
fi
