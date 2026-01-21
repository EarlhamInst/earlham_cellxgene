# SSL/TLS Configuration

This directory is reserved for SSL/TLS certificates and keys for HTTPS support.

## Future HTTPS Support

To enable HTTPS:

1. **Obtain SSL Certificates**:
   - Use Let's Encrypt (certbot) for free certificates
   - Or use your organization's CA-signed certificates
   - Or generate self-signed certificates for testing

2. **Place Certificates Here**:
   ```
   ssl/
   ├── certificate.crt      # SSL certificate
   ├── certificate.key      # Private key
   └── ca-bundle.crt        # CA certificate chain (if required)
   ```

3. **Update nginx.conf**:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name your-domain.com;
       
       ssl_certificate /etc/nginx/ssl/certificate.crt;
       ssl_certificate_key /etc/nginx/ssl/certificate.key;
       
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;
       ssl_prefer_server_ciphers on;
       
       # ... rest of configuration
   }
   
   # Redirect HTTP to HTTPS
   server {
       listen 80;
       server_name your-domain.com;
       return 301 https://$server_name$request_uri;
   }
   ```

4. **Update docker-compose.yml**:
   ```yaml
   nginx:
     ports:
       - "80:80"
       - "443:443"  # Add HTTPS port
     volumes:
       - ./services/nginx/ssl:/etc/nginx/ssl:ro  # Mount SSL directory
   ```

## Let's Encrypt Example

```bash
# Install certbot
sudo apt-get install certbot

# Obtain certificate (standalone mode)
sudo certbot certonly --standalone -d your-domain.com

# Certificates will be in:
# /etc/letsencrypt/live/your-domain.com/

# Copy to this directory:
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/certificate.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/certificate.key

# Set permissions
chmod 600 ssl/certificate.key
chmod 644 ssl/certificate.crt
```

## Self-Signed Certificate (Testing Only)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/certificate.key \
    -out ssl/certificate.crt \
    -subj "/CN=localhost"

# Set permissions
chmod 600 ssl/certificate.key
chmod 644 ssl/certificate.crt
```

**Note**: Self-signed certificates will show browser warnings. Use only for testing.

## Security Best Practices

- **Keep private keys secure**: Never commit `*.key` files to version control
- **Use strong protocols**: TLSv1.2 and TLSv1.3 only
- **Strong ciphers**: Disable weak ciphers
- **HSTS header**: Add `Strict-Transport-Security` header
- **Certificate renewal**: Automate Let's Encrypt renewal with cron

## .gitignore

This directory should be excluded from version control:

```gitignore
# In .gitignore
services/nginx/ssl/*.key
services/nginx/ssl/*.crt
services/nginx/ssl/*.pem
!services/nginx/ssl/README.md
```

## References

- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Nginx SSL Module](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)
