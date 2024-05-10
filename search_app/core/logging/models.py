from logging import Handler, LogRecord, Filter
from sqlalchemy.orm import Session
import logging
import logging.handlers
from datetime import datetime
import time
import threading
from queue import Empty, SimpleQueue


from search_app.core.databases.sql_backend import LogsDB
from search_app.core.databases.sql_models import Logs


class SQLHandler(Handler):
    def __init__(self, level: int | str = None) -> None:
        super().__init__(level)

    def format(self, record: LogRecord) -> str:
        return super().format(record)
    
    @LogsDB()
    def emit(self, session : Session, record: LogRecord) -> None:
        log_to_emit =Logs(
            time_stamp  = datetime.fromtimestamp(record.created),
            file_moduel = record.filename,
            logger      = record.name,
            msg_cat     = record.levelname,
            line        = record.lineno,
            msg         = record.message,
            error_infos = record.exc_text,
        )
        
        session.add(log_to_emit)
        session.commit()
        
        return

class AppFilter(Filter):
    def __init__(self, name: str = "") -> None:
        super().__init__(name)

    def filter(self, record: LogRecord) -> bool | LogRecord:

        return "search_app" in record.name

# console_formatter = Formatter(fmt="%(asctime)-25s - %(name)-50s : %(levelname)-8s - %(lineno)-4s   %(message)s")

class SingleThreadQueueListener(logging.handlers.QueueListener):

    monitor_thread = None
    listeners = []
    sleep_time = 0.1

    @classmethod
    def _start(cls):

        if cls.monitor_thread is None or not cls.monitor_thread.is_alive():
            cls.monitor_thread = t = threading.Thread(
                target=cls._monitor_all, name="logging_monitor")
            t.daemon = True
            t.start()

    @classmethod
    def _join(cls):

        if not cls.monitor_thread is None and cls.monitor_thread.is_alive():
            cls.monitor_thread.join()
        cls.monitor_thread = None

    @classmethod
    def _monitor_all(cls):

        noop = lambda: None
        time.sleep(cls.sleep_time)
        for listener in cls.listeners:
            try:
                task_done = getattr(listener.queue, 'task_done', noop)
                while True:
                    record = listener.dequeue(False)
                    if record is listener._sentinel:
                        cls.listeners.remove(listener)
                    else:
                        listener.handle(record)
                    task_done()
            except Empty:
                continue
    
    def start(self):
        SingleThreadQueueListener.listeners.append()
        SingleThreadQueueListener._start()

    def stop(self):
        self.enqueue_sentinel()


class LogContext():

    def __init__(self) -> None:
        self.listeners = []

    def iter_loggers(self):

        for name in logging.root.manager.loggerDict:
            yield logging.getLogger(name)
        yield logging.getLogger()

    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exec_type, exec_value, traceback):
        self.close()
    
    def open(self):

        for logger in self.iter_loggers():
            if handlers := logger.handlers:
                queue = SimpleQueue
                listener = SingleThreadQueueListener(queue=queue, *handlers)
                logger.handlers = [logging.handlers.QueueHandler(queue)]
                self.listeners.append((listener, logger))
                listener.start()
    
    def close(self):

        while self.listeners:
            listener, logger = self.listeners.pop()
            logger.handlers = listener.handlers
            listener.stop()



LOGGING = {
    "version":  1,
    "filters":  {
        "filter_on_app":    {
            '()':       "search_app.core.logging.models.AppFilter",
            'param':    'noshow',
        }
    },
    "formatters":   {
        "default":  {"format": "%(asctime)s %(levelname)-8s %(message)s"},
        "console":  {"format": "%(asctime)-25s - %(name)-3s (%(filename)-50s) : %(levelname)-8s - %(lineno)-4s   %(message)s"}
    },
    "handlers": {
        "app":  {
            "class":        "search_app.core.logging.models.SQLHandler",
            "formatter":    "default",
            "filters":      ['filter_on_app']
        },
        "console":  {
            "class":        "logging.StreamHandler",
            "formatter":    "console"
        }
    },
    "loggers":  {
        "search_app.api":  {
            "handlers": ["app", "console"],
            "level":    "INFO"
        }
    }
}