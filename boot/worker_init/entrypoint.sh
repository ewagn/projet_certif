#!/bin/bash

# cd ./workspace 

MODULE="search_app.celery_worker"
TASK_QUEUE="tasks.search"

# cd ./workspace/search-app

# celery -A ${MODULE} worker -Q ${TASK_QUEUE}  -P threads  --prefetch-multiplier=1  --concurrency=4  --loglevel=INFO
celery -A ${MODULE} worker -Q ${TASK_QUEUE} --loglevel=DEBUG