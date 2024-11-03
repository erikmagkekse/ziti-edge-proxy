#!/bin/bash

if [[ -n "$ZITI_IDENTITY" ]]; then
    echo "ZITI_IDENTITY detected, creating /app/identity.json..."

    echo "$ZITI_IDENTITY" | base64 -d > /app/identity.json

    if [[ $? -eq 0 ]]; then
        echo "Identity file /app/identity.json created successfully."

        export ZITI_IDENTITIES=/app/identity.json
        echo "Exported ZITI_IDENTITIES=/app/identity.json"
    else
        echo "Error: Failed to decode and create identity file."
        exit 1
    fi
fi

exec "$@"
