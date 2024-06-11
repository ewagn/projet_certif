from celery import Celery, Task
from celery.utils.log import get_task_logger
from logging import ERROR, DEBUG, getLogger, FileHandler, Logger
from pathlib import Path
from selenium.webdriver import Chrome

from search_app.core.databases.elasticsearch_backend import ESHandler
from search_app.core.databases.sql_backend import AppDB
from search_app.config import CeleryConf
from search_app.core.services.text_summarize.engine import TextSummerize
from search_app.core.logging.models import SQLHandler, AppFilter
from search_app.core.services.webscraping.drivers import ScrapingDriver

class BaseTask(Task):
    _slq_db = None
    _es_handler = None
    _text_summerize = None
    _webdriver_factory = None

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
    
    @property
    def webdriver_factory(self) :
        if not self._webdriver_factory :
            self._webdriver_factory = ScrapingDriver()
        return self._webdriver_factory
    
    def get_webdriver(self, url : str) -> tuple[Chrome, Path]:

        driver, temp_folder = self.webdriver_factory.get_driver(url=url)

        wedriver_package = {
            'driver' : driver,
            'folder' : temp_folder
        }

        return wedriver_package

app = Celery('celery_worker', task_cls=BaseTask)
app.config_from_object(CeleryConf)

app.autodiscover_tasks(['search_app.tasks.search', 'search_app.tasks.summerize', 'search_app.tasks.web_scrapping', 'search_app.tasks.paper_parser'])

fh = FileHandler(filename="./search_app/log_worker.log", mode="a")
fh.setLevel(DEBUG)
sql_handler = SQLHandler(level=ERROR)
sql_handler.addFilter(AppFilter(name="app_filter"))

root_logger = getLogger("")
lg = get_task_logger(__name__)
lg.propagate = True

root_logger.addHandler(fh)
root_logger.addHandler(sql_handler)

# lg.addHandler(fh)
# lg.addHandler(sql_handler)
