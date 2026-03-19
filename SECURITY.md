# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **DO NOT** create a public GitHub issue for security vulnerabilities
2. Send an email to the repository maintainer with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability and determine its severity
- **Fix Timeline**: Critical vulnerabilities will be addressed within 7 days
- **Disclosure**: We will coordinate with you on public disclosure timing

### Security Best Practices

When using NasFusion, please follow these security recommendations:

1. **Change Default Credentials**
   - Immediately change the default admin password (`admin123`)
   - Use strong, unique passwords

2. **Secure Your Secrets**
   - Generate strong `SECRET_KEY` and `JWT_SECRET_KEY` values
   - Never commit `.env` files to version control
   - Use `openssl rand -hex 32` to generate secure keys

3. **Network Security**
   - Use HTTPS in production (reverse proxy with SSL)
   - Restrict network access with firewall rules
   - Do not expose the application directly to the internet without protection

4. **Regular Updates**
   - Keep NasFusion updated to the latest version
   - Update Docker images regularly

5. **Backup**
   - Regularly backup your database and configuration
   - Store backups securely

## Known Security Considerations

- PT site credentials are encrypted in the database
- JWT tokens have configurable expiration
- All API endpoints require authentication (except health check)

Thank you for helping keep NasFusion and its users safe!
