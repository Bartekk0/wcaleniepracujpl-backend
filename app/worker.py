from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "jobboard_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task
def hello():
    return 'hello world'
