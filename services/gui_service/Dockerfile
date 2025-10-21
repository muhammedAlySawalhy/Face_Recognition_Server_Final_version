# Define ARGs at the top (available to all stages)
ARG NODE_VERSION=20
ARG SERVICE_NAME=gui_service
#----------------------------------------------------------------------------------#
# First Stage - Dependencies Stage
# This stage is responsible for installing Node.js dependencies
FROM node:${NODE_VERSION} AS deps
WORKDIR /app
ARG SERVICE_NAME
# Copy package files
COPY ./${SERVICE_NAME}/package.json ./
# Only install dependencies for your target platform --frozen-lockfile
RUN yarn install --production  --network-timeout 10000000 --verbose
#----------------------------------------------------------------------------------#
# Second Stage - Builder Stage
# This stage builds the Next.js application
FROM node:${NODE_VERSION} AS builder
ARG SERVICE_NAME
WORKDIR /app
# Build the application (no env vars needed at build time)
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

COPY --from=deps /app/node_modules ./node_modules
# Copy source code
COPY ./${SERVICE_NAME}/  .
RUN yarn build
#----------------------------------------------------------------------------------#
# Final Stage - Runner Stage
# This stage creates the final application image for running the GUI service
FROM node:${NODE_VERSION}-alpine AS runner
ARG SERVICE_NAME
WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy built application
COPY --from=builder --chown=node:node /app/.next        ./.next
COPY --from=builder --chown=node:node /app/public       ./public
COPY --from=builder --chown=node:node /app/package.json ./package.json
COPY --from=builder --chown=node:node /app/scripts       ./scripts
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/next.config.js ./next.config.js

# Copy the startup script
COPY ./${SERVICE_NAME}/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create data directories that will be mounted
RUN mkdir -p /app/gui_data /app/users_db /app/actions  /app/public/data
RUN chown -R node:node /app

# Switch to non-root user
USER node

# Use the startup script as entrypoint to export environment variables
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
