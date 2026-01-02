# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please **do not** open a public issue.

Instead, please report it privately:

1. **Email**: Send details to the repository maintainer
2. **Response time**: We will respond within 48 hours
3. **Disclosure**: We will work with you to understand and resolve the issue before any public disclosure

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Security Measures

This application implements the following security measures:

### Authentication & Authorization
- **bcrypt** password hashing with salt
- **Rate limiting**: 5/min registration, 10/min login attempts
- **Admin secret** with timing-safe comparison (`secrets.compare_digest`)

### Input Validation
- Date format validation (YYYY-MM-DD) on workout endpoints
- Username validation (3-20 chars, alphanumeric only)
- Body part validation against allowed list

### Configuration Security
- All credentials loaded from environment variables
- `.env` files excluded via `.gitignore`
- CORS configured via `ALLOWED_ORIGINS` env var

### Automated Security Scanning
- **Pre-commit hooks**: Gitleaks secret scanning before each commit
- **GitHub Actions**: Daily security scans with Gitleaks, pip-audit, safety
- **Local scripts**: `scripts/security/` for manual audits

## Best Practices for Deployment

1. **Never commit `.env` files** - Use `.env.example` as a template
2. **Rotate credentials regularly** - Especially after any suspected exposure
3. **Use strong secrets** - Generate with `openssl rand -hex 32`
4. **Enable Cloud Run authentication** for admin endpoints in production
5. **Install pre-commit hooks** - Run `pip install pre-commit && pre-commit install`

## Security Scripts

Run manual security audits:

```bash
# Scan for secrets in codebase
./scripts/security/scan_secrets.sh

# Validate .env has all required keys
./scripts/security/validate_env.sh

# Audit Python dependencies
./scripts/security/security_audit.sh
```
