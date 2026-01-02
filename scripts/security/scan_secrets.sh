#!/bin/bash
# scan_secrets.sh
# Scans the repository for secrets using Gitleaks

if ! command -v gitleaks &> /dev/null; then
    echo "Gitleaks not found. Running via Docker..."
    docker run -v $(pwd):/path zricethezav/gitleaks:latest detect --source="/path" --verbose
else
    echo "Running Gitleaks (Local)..."
    gitleaks detect --source=. --verbose
fi
