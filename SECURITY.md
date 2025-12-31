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

- **Environment-based configuration**: All sensitive credentials are stored in environment variables
- **Rate limiting**: API endpoints are protected against brute force attacks
- **Admin authentication**: Administrative endpoints require secret token
- **CORS**: Cross-origin requests are properly configured

## Best Practices for Deployment

1. **Never commit `.env` files** - Use `.env.example` as a template
2. **Rotate credentials regularly** - Especially after any suspected exposure
3. **Use strong secrets** - Generate with `openssl rand -hex 32`
4. **Enable Cloud Run authentication** for admin endpoints in production
