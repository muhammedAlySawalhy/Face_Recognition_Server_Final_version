#!/bin/sh

# Function to check and validate environment variables
check_env_var() {
    local var_name="$1"
    local default_value="$2"
    local is_required="$3"
    
    # Get the current value
    eval current_value=\$$var_name
    
    if [ -z "$current_value" ]; then
        if [ -n "$default_value" ]; then
            # Only export if setting a default value
            export "$var_name"="$default_value"
            echo "⚠️  $var_name not set, using default: $default_value"
        elif [ "$is_required" = "true" ]; then
            echo "❌ $var_name is required but not set!"
            exit 1
        else
            echo "⚠️  $var_name: NOT SET"
        fi
    else
        # Variable already has a value, just report it (no need to re-export)
        echo "✅ $var_name: $current_value"
    fi
}

# Export environment variables as OS-level variables
check_env_var "JWT_SECRET" "omar_ehab_super_secret" "true"
check_env_var "ADMIN_PASSWORD" "admin123" "false"
check_env_var "GUI_DATA" "/data/gui_data" "true"
check_env_var "USERDATABASE" "/data/user_database" "true"
check_env_var "Actions" "/data/actions" "true"
check_env_var "S1_GET_URL" "http://host.docker.internal:8000/server1/redis/get" "true"
check_env_var "S2_GET_URL" "http://host.docker.internal:8000/server2/redis/get" "true"
check_env_var "S1_UPDATE_URL" "http://host.docker.internal:8000/server1/client/status/update" "true"
check_env_var "S2_UPDATE_URL" "http://host.docker.internal:8000/server2/client/status/update" "true"
check_env_var "EXCEL_PATH" "/app/public/data/users.xlsx" "true"


# Print exported variables for verification
echo "Environment variables exported:"
echo "JWT_SECRET=$JWT_SECRET"
echo "ADMIN_PASSWORD=$ADMIN_PASSWORD"
echo "GUI_DATA=$GUI_DATA"
echo "USERDATABASE=$USERDATABASE"
echo "Actions=$Actions"
echo "S1_GET_URL=$S1_GET_URL"
echo "S2_GET_URL=$S2_GET_URL"
echo "S1_UPDATE_URL=$S1_UPDATE_URL"
echo "S2_UPDATE_URL=$S2_UPDATE_URL"
echo "EXCEL_PATH=$EXCEL_PATH"

# Start the Next.js application
exec yarn start
