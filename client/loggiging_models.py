from logging import Handler, WARNING, LogRecord, Formatter, Filter
from sqlalchemy.orm import Session
from datetime import datetime


from client.sql_backend import logs_engine
from client.sql_models import Logs


class SQLHandler(Handler):
    def __init__(self, level: int | str = WARNING) -> None:
        self.sql_session = Session(logs_engine)
        super().__init__(level)

    def format(self, record: LogRecord) -> str:
        return super().format(record)
    
    def emit(self, record: LogRecord) -> None:
        log_to_emit =Logs(
            time_stamp  = datetime.fromtimestamp(record.created),
            logger      = record.name,
            msg_cat     = record.levelname,
            line        = record.lineno,
            msg         = record.message,
            error_infos = record.exc_text,
        )
        
        self.sql_session.add(log_to_emit)
        self.sql_session.commit()
        
        return super().emit(record)
    
    def close(self) -> None:
        self.sql_session.close()
        return super().close()

class ClientFilter(Filter):
    def __init__(self, name: str = "") -> None:
        super().__init__(name)

    def filter(self, record: LogRecord) -> bool | LogRecord:

        if not record.name.startswith('client.'):
            return False
        else :
            return True

console_formatter = Formatter(fmt="{asctime:<25} - {name:^50} : {levelname:^8} - {lineno:<4}   {message}", style='{')