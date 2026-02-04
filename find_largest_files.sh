#!/bin/bash
# Find the top 10 largest files in the repository

find . -type f -not -path './.git/*' -exec ls -la {} \; 2>/dev/null | \
    awk '{print $5, $9}' | \
    sort -rn | \
    head -10
