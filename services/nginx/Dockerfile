FROM nginx:alpine

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create log directory
RUN mkdir -p /var/log/nginx

# Expose port
EXPOSE 80

# Health check (shorter intervals for faster feedback in development)
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=2 \
    CMD wget --quiet --tries=1 --spider http://localhost/api/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
