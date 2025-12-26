#!/bin/bash

# Test Caddyfile syntax
echo "Testing Caddyfile syntax..."
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

if [ $? -eq 0 ]; then
    echo "✅ Caddyfile syntax is valid"
else
    echo "❌ Caddyfile syntax error"
    exit 1
fi

# Test that we can start Caddy in dry-run mode
echo "Testing Caddy configuration..."
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile --dry-run

if [ $? -eq 0 ]; then
    echo "✅ Caddy configuration is valid"
else
    echo "❌ Caddy configuration error"
    exit 1
fi

echo "✅ All tests passed!"
