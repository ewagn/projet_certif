from celery import Celery, Task
from celery.utils.log import get_task_logger
from logging import ERROR

from search_app.core.databases.elasticsearch_backend import ESHandler
from search_app.core.databases.sql_backend import AppDB
from search_app.config import CeleryConf
from search_app.core.services.text_summarize.engine import TextSummerize
from search_app.core.logging.models import SQLHandler, AppFilter

app = Celery()
app.config_from_object(CeleryConf)
app.autodiscover_tasks(['tasks.search', 'tasks.summerize', 'tasks.web_scrapping', 'tasks.paper_parser'])

lg = get_task_logger(__name__)
sql_handler = SQLHandler(level=ERROR)
sql_handler.addFilter(AppFilter(name="app_filter"))
lg.addHandler(sql_handler)

class BaseTask(Task):
    _slq_db = None
    _es_handler = None
    _text_summerize = None

    @property
    def sql_db(self):
        """ORM base de données SQL Alchemy pour l'application de recherche."""
        if self._slq_db == None:
            self._slq_db = AppDB()
        
        return self._slq_db.sql_engine

    @property
    def esh(self):
        if self._es_handler == None :
            self._es_handler = ESHandler()
        
        return self._es_handler
    
    @property
    def text_summerize(self):
        if self._text_summerize == None :
            self._text_summerize = TextSummerize()
        
        return self._text_summerize