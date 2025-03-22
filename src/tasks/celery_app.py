from celery import Celery
from src.config import REDIS_HOST, REDIS_PORT

celery = Celery(
    'tasks',
    broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
    backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
    include=['src.tasks.tasks']
)

celery.conf.timezone = 'UTC'

celery.conf.beat_schedule = {
    'update-stats': {
        'task': 'src.tasks.tasks.update_link_stats',
        'schedule': 60.0,
    },
    'deactivate-expired-links': {
        'task': 'src.tasks.tasks.check_and_deactivate_links',
        'schedule': 60
    },
}