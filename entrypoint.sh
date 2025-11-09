#!/bin/bash

SERVICE_TYPE=${SERVICE_TYPE:-gateway}
echo "Starting $SERVICE_TYPE service..."

case $SERVICE_TYPE in
"gateway")
    cd /app/services/gateway_server_service && ./run_gateway.sh
;;
"pipelines-manager")
    cd /app/services/pipelines_manager_service && ./run_pipelines_manager.sh
;;
"pipeline-worker")
    cd /app/services/pipeline_worker_service && ./run_pipeline_worker.sh
;;
"decision-manager")
    cd /app/services/decision_manager_service && ./run_decision_manager.sh
;;
"server-manager")
    cd /app/services/server_manager_service && ./run_server_manager.sh
;;
"management")
    cd /app/services/management_service && ./run_management.sh
;;
"help")
    echo "Available services:"
    echo "  - gateway"
    echo "  - pipelines-manager"
    echo "  - pipeline-worker"
    echo "  - decision-manager"
    echo "  - server-manager"
    echo "  - management"
;;
*)
    echo "Unknown service type: $SERVICE_TYPE"
    exit 1
;;
esac