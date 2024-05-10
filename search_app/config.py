import os

class CeleryConf():
    task_search_queue = "tasks.search"
    task_search_prefix = "tasks.search.tasks"
    task_make_search = f"{task_search_prefix}.get_search_results"


    task_cls='search_app.celery:BaseTask'
    broker_url = os.environ.get("CELERY_BROKER_URL", None)
    result_backend = os.environ.get("CELERY_RESULT_BACKEND", None)