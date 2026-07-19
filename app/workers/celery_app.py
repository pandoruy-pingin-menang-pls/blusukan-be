from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
import ssl

# Inisialisasi Celery App
celery_app = Celery(
    "blusukan_worker",
    broker=str(settings.CELERY_BROKER_URL),
    backend=str(settings.CELERY_BROKER_URL)
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=False,
    beat_schedule={
        # Jadwal harian jam 03.00 pagi waktu Jakarta
        "daily-stock-recalc": {
            "task": "app.workers.tasks_stock_recalc.calculate_daily_stock",
            "schedule": crontab(hour=3, minute=0),
            "args": (),
        },
    }
)

if str(settings.CELERY_BROKER_URL).startswith("rediss://"):
    celery_app.conf.update(
        broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
        redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE}
    )

# Load tasks
celery_app.autodiscover_tasks(["app.workers.tasks_stock_recalc"], force=True)
