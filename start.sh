#!/bin/bash

celery -A app.workers.celery_app beat --loglevel=info &

celery -A app.workers.celery_app worker --loglevel=info --concurrency=1 &

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
