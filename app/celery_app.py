from celery import Celery
from app.config import settings
celery_app = Celery(
    'tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_backend=settings.REDIS_URL,
    broker_connection_retry_on_startup=True
)

from app import tasks
