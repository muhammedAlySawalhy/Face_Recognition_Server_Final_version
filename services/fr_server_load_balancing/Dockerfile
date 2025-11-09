FROM nginx:1.25-alpine

# Install gettext to provide envsubst for template rendering
RUN apk add --no-cache gettext

# Use Nginx foreground start; actual config rendered at runtime by docker-compose command
CMD ["nginx", "-g", "daemon off;"]
