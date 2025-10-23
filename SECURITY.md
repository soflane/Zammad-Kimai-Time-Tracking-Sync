# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please do the following:

### Please DO NOT:
- Open a public GitHub issue
- Disclose the vulnerability publicly before it has been addressed

### Please DO:
1. **Email us directly** at [dev@ayoute.be] (replace with actual email)
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. Allow us reasonable time to respond and fix the issue before public disclosure

## What to Expect

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours
- **Assessment**: We will investigate and assess the vulnerability within 5 business days
- **Fix Timeline**: Critical vulnerabilities will be addressed within 7 days; others within 30 days
- **Disclosure**: We will coordinate with you on public disclosure timing
- **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Measures

This project implements the following security measures:

### Data Protection
- **Encryption at Rest**: API tokens and sensitive credentials are encrypted using Fernet (symmetric encryption)
- **Secure Password Storage**: User passwords are hashed using bcrypt with salt
- **Environment Variables**: Sensitive configuration stored in `.env` files (never committed)

### API Security
- **Authentication**: JWT tokens with configurable expiration
- **CORS**: Whitelist-based origin validation
- **Input Validation**: All inputs validated using Pydantic schemas
- **Webhook Verification**: HMAC signature validation for incoming webhooks
- **HTTPS Only**: All external API calls require TLS

### Database Security
- **SQL Injection Prevention**: SQLAlchemy ORM prevents injection attacks
- **Connection Pooling**: Secure connection management
- **Parameterized Queries**: All queries use bound parameters

### GDPR Compliance
- **Data Minimization**: Only essential personal data is stored
- **Right to Export**: API endpoints for data export
- **Right to Erasure**: API endpoints for data deletion
- **Data Retention**: Configurable retention policies for audit logs
- **Audit Trail**: Complete logging of all data access and modifications

### Docker Security
- **Non-root User**: Containers run as non-root user
- **Minimal Base Images**: Alpine-based images for reduced attack surface
- **Security Scanning**: Automated vulnerability scanning in CI/CD
- **Secrets Management**: Environment variables and Docker secrets for sensitive data

## Dependency Security

- **Dependabot**: Automated dependency updates enabled
- **npm audit**: Regular frontend dependency audits
- **pip audit**: Regular backend dependency audits
- **SAST**: Static analysis in CI/CD pipeline

## Best Practices for Deployment

1. **Use Strong Secrets**:
   ```bash
   # Generate strong random keys
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Enable HTTPS**:
   - Use Let's Encrypt or your own SSL certificates
   - Configure Nginx with strong TLS settings
   - Disable HTTP, redirect to HTTPS

3. **Database Security**:
   - Use strong database passwords
   - Restrict database access to application containers only
   - Enable PostgreSQL SSL connections
   - Regular backups with encryption

4. **Network Security**:
   - Use Docker networks to isolate services
   - Expose only necessary ports
   - Consider using a reverse proxy with rate limiting
   - Implement firewall rules

5. **Regular Updates**:
   - Keep all dependencies up to date
   - Monitor security advisories
   - Apply security patches promptly

## Security Checklist for Production

- [ ] Changed all default passwords
- [ ] Generated strong `SECRET_KEY` and `ENCRYPTION_KEY`
- [ ] Configured HTTPS with valid certificates
- [ ] Enabled firewall and restricted ports
- [ ] Set up automated backups
- [ ] Configured log monitoring
- [ ] Enabled Dependabot
- [ ] Reviewed and restricted CORS origins
- [ ] Configured rate limiting
- [ ] Set up security monitoring/alerts

## Known Security Considerations

### V1 Limitations
- Single admin user (no role-based access control)
- Basic authentication (no 2FA, no OIDC)
- Local database (no encryption at rest at DB level)

### Planned Security Enhancements (V2+)
- Multi-user support with RBAC
- Two-factor authentication (2FA)
- OIDC/SAML integration
- Database-level encryption
- Advanced audit logging with retention policies
- Security headers (CSP, HSTS, etc.)

## Contact

For security concerns, please contact: [security@your-domain.com]

For general questions: [Open a GitHub Discussion](https://github.com/your-org/repo/discussions)

---

Thank you for helping keep this project secure!
