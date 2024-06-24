import os

class CeleryConf():
    task_search_queue = "tasks.search"
    task_search_prefix = "search_app.tasks.search.tasks"
    task_make_search = "search_app.tasks.search"


    # task_cls='search_app.celery_worker:BaseTask'
    # broker_url = os.environ.get("CELERY_BROKER_TRANSPORT_URL", None)
    # result_backend = os.environ.get("CELERY_RESULT_TRANSPORT_BACKEND", None)
    broker_url = 'redis://redis:6379/0'
    result_backend = 'redis://redis:6379/0'
    broker_connection_retry_on_startup = True
    worker_prefetch_multiplier = 10
    worker_heartbeat = 10
    task_concurrency=4
