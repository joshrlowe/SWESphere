"""
Celery workers package for SWESphere.

This package provides the Celery application and all background tasks
for asynchronous processing.

Usage:
    # Start worker
    celery -A app.workers.celery_app worker --loglevel=info
    
    # Start beat scheduler
    celery -A app.workers.celery_app beat --loglevel=info
    
    # Start flower monitoring
    celery -A app.workers.celery_app flower --port=5555
"""

from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
