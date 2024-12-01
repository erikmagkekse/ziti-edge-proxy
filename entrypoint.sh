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
else
    echo "ZITI_IDENTITY not detected. Checking ZITI_IDENTITIES for configuration..."

    if [[ -z "$ZITI_IDENTITIES" ]]; then
        echo "Error: ZITI_IDENTITIES is not set. Please configure it as a file pattern."
        exit 1
    fi

    dir=$(dirname "$ZITI_IDENTITIES")
    pattern=$(basename "$ZITI_IDENTITIES")

    if [[ ! -d "$dir" ]]; then
        echo "Error: Directory $dir does not exist."
        exit 1
    fi

    echo "Scanning for files matching: $ZITI_IDENTITIES"

    files=$(find "$dir" -maxdepth 1 -name "$pattern" -type f 2>/dev/null | tr '\n' ',' | sed 's/,$//')

    if [[ -n "$files" ]]; then
        export ZITI_IDENTITIES="$files"
        echo "ZITI_IDENTITIES updated to: $ZITI_IDENTITIES"
    else
        echo "Error: No files found matching the pattern: $ZITI_IDENTITIES"
        exit 1
    fi
fi

exec "$@"
