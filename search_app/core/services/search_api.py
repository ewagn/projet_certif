from typing import Sequence
from celery import Celery
from celery.result import AsyncResult

import config
from search_app.app.api.models import SearchRequests, TaskResult, SummerizedParagraph

task_celery = config.CeleryConf
celery_app = Celery()
celery_app.config_from_object(task_celery)

class APISearch():

    def __init__(self) -> None:
        pass

    async def make_search(self, search_request : SearchRequests , user_id : int, search_type : str) -> AsyncResult :

        request_kwargs = search_request.model_dump()
        request_kwargs.update({'user_id' : user_id
                               , 'research_type' : search_type})

        result : AsyncResult = celery_app.send_task(
            task_celery.task_make_search
            , kwargs=request_kwargs
            , queue=task_celery.task_search_queue
        )

        return result
    
    async def get_task(self, task_id : str) -> AsyncResult | None :
        result = AsyncResult(id=task_id)

        try :
            result.status
            if result.status == "SUCCESS" :
                result.forget()
        except Exception :
            return None
        
        return result