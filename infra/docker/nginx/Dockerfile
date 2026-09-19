FROM nginx:1.27-alpine

# Remove default configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy custom reverse proxy configuration
COPY infra/docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

STOPSIGNAL SIGQUIT

CMD ["nginx", "-g", "daemon off;"]
