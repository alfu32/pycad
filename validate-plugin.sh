#!/bin/bash

# Check if the file path is provided as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <file_path>"
  exit 1
fi

# Calculate the SHA-256 hash of the file
sha256sum "$1"
