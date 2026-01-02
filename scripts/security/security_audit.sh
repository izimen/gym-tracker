#!/bin/bash
# security_audit.sh
# Runs dependency audits for Python project

echo "🔍 Auditing Python Dependencies..."

# Check if pip-audit is installed
if ! command -v pip-audit &> /dev/null; then
    echo "Installing pip-audit..."
    pip install pip-audit safety
fi

echo "Running pip-audit..."
pip-audit --strict
PIP_AUDIT_STATUS=$?

echo "Running safety check..."
safety check --full-report
SAFETY_STATUS=$?

if [ $PIP_AUDIT_STATUS -eq 0 ] && [ $SAFETY_STATUS -eq 0 ]; then
    echo "✅ All audits passed."
    exit 0
else
    echo "❌ Vulnerabilities found."
    exit 1
fi
