#!/bin/bash
# validate_env.sh
# Checks if .env contains all keys from .env.example

EXAMPLE_FILE=".env.example"
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ $ENV_FILE does not exist."
    exit 1
fi

if [ ! -f "$EXAMPLE_FILE" ]; then
    echo "❌ $EXAMPLE_FILE does not exist."
    exit 1
fi

echo "Validating $ENV_FILE against $EXAMPLE_FILE..."

# Extract keys from example file (ignoring comments and empty lines)
grep -v '^#' "$EXAMPLE_FILE" | grep -v '^\s*$' | awk -F= '{print $1}' | while read -r key; do
    if ! grep -q "^$key=" "$ENV_FILE"; then
        echo "⚠️  Missing key in .env: $key"
    fi
done

echo "✅ Validation complete."
