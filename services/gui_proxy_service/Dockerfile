FROM nginx:alpine

# envsubst (from gettext) for template rendering, openssl for CSR/key ops, CA bundle for trust
RUN apk add --no-cache gettext openssl ca-certificates && update-ca-certificates

# Copy template & entrypoint
# Provide a default template (overridden at runtime by mounted template)
COPY config_templates/site.conf.template /etc/nginx/templates/site.conf.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# (Optional) If you also keep a custom nginx.conf, copy it:
# COPY nginx.conf /etc/nginx/nginx.conf

# Nice-to-have: explicit stop signal for graceful shutdowns
STOPSIGNAL SIGQUIT

CMD ["/entrypoint.sh"]
