import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300, # 5 minutes maximum for a task
)

# Example task
@celery_app.task(name="example_async_task")
def example_async_task(word: str):
    # Simulate a heavy task like AI inference
    return {"status": "success", "word": word, "processed": True}
