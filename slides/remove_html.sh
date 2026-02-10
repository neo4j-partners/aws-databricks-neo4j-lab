#!/bin/bash
# Remove all HTML files from the slides directory
find "$(dirname "$0")" -name "*.html" -type f -delete
echo "Done. All HTML files removed."
