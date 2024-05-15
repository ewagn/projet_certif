from sqlalchemy import URL, create_engine
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import os

# from dotenv import load_dotenv
# load_dotenv(dotenv_path='./.env')
# load_dotenv(dotenv_path="./db_init/db.env")
# load_dotenv(dotenv_path="./dev.env", override=True)

from search_app.core.databases.sql_models import Base, LogsBase

def read_pwd_file(file_path:str) -> str:
    with open(file=file_path, mode="r") as pwd_file:
        pwd = pwd_file.readline().replace("\n", "")
    return pwd

connect_args = {
    "ssl": {
        "ca"                : os.getenv("CLIENT_CERTIF_PATH") + "/ca-cert.pem",
        "cert"              : os.getenv("CLIENT_CERTIF_PATH") + "/client-cert.pem",
        "key"               : os.getenv("CLIENT_CERTIF_PATH") + "/client-key.pem",
        "check_hostname"    : False,
    }
}

sql_url = URL.create(
    drivername="mariadb+pymysql",
    username=os.getenv("MARIADB_USER"),
    password=read_pwd_file(os.getenv("MARIADB_PASSWORD_FILE")),
    host=os.getenv("MARIADB_ROOT_HOST"),
    # host="mariadb",
    port=3306,
    database=os.getenv("MARIADB_DATABASE"),
)
class AppDB():
    _sql_engine = None

    def __init__(self) -> None:
        pass

    @property
    def sql_engine(self):
        if self._sql_engine == None:
            self._sql_engine = create_engine(
                url=sql_url
                , connect_args=connect_args
            )
            Base.metadata.create_all(self._sql_engine)
        return self._sql_engine

sql_logs_url = URL.create(
    drivername="mariadb+pymysql",
    username=read_pwd_file(os.getenv("MARIADB_LOG_USER_FILE")),
    password=read_pwd_file(os.getenv("MARIADB_LOG_PWD_FILE")),
    host=os.getenv("MARIADB_ROOT_HOST"),
    # host="isearch_app-mariadb",
    port=3306,
    database=os.getenv("MARIADB_FOR_LOGS"),
)

class LogsDB():
    _logs_engine = None

    def __init__(self, func) -> None:
        self._func = func
        self.logs_engine
    
    @property
    def logs_engine(self):
        if self._logs_engine == None:
            self._logs_engine = create_engine(
                url=sql_logs_url
                , connect_args=connect_args
            )
            LogsBase.metadata.create_all(self._logs_engine)
        return self._logs_engine
    
    def __call__(self, *args, **kwds):
        def wrapper(*args, **kwds):
            with Session(self.logs_engine) as session :
                result = self._func(session=session, *args, **kwds)
                return result
        return wrapper