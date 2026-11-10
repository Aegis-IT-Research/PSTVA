#!/bin/bash

set -e

case "$1" in
  server)
    # Start Uvicorn server
      uvicorn core.app.api:app --host 0.0.0.0 --port 8000 --reload
    ;;
  workers)
    # Start Celery workers
    celery --workdir /app -A core.app.tasks worker --loglevel=info --autoscale=20,3
    ;;
  flower)
    # Start Flower for monitoring Celery tasks
    celery --workdir /app -A core.app.tasks flower --port=5555 --address=0.0.0.0
    ;;
  *)
    echo "Usage: $0 {server|workers|flower}"
    exit 1
    ;;
esac
