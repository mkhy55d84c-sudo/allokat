#!/bin/bash
export PYTHONPATH=/Users/dariosteinmann/Documents/CLAUDE/IDEAS/allokat
exec /Users/dariosteinmann/Library/Python/3.13/bin/streamlit run \
  /Users/dariosteinmann/Documents/CLAUDE/IDEAS/allokat/app.py \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  "$@"
