from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import os

from dotenv import load_dotenv
load_dotenv(dotenv_path='./.env')
load_dotenv(dotenv_path="./db_init/db.env")
load_dotenv(dotenv_path="./dev.env", override=True)

from client.sql_models import Base, LogsBase

def read_pwd_file(file_path:str) -> str:
    with open(file=file_path, mode="r") as pwd_file:
        pwd = pwd_file.readline().replace("\n", "")
    return pwd

connect_args = {
    "ssl": {
        "ca"                : os.getenv("CLIENT_CERTIF_PATH") + "ca-cert.pem",
        "cert"              : os.getenv("CLIENT_CERTIF_PATH") + "client-cert.pem",
        "key"               : os.getenv("CLIENT_CERTIF_PATH") + "client-key.pem",
        "check_hostname"    : False,
    }
}

sql_url = URL.create(
    drivername="mariadb+pymysql",
    username=os.getenv("MARIADB_USER"),
    password=read_pwd_file("./db_init/mariadb_mysql_pwd.txt"),
    host="localhost",
    port=3306,
    database=os.getenv("MARIADB_DATABASE"),
)
class AppDB():
    sql_engine = None

    def __init__(self) -> None:
        pass
    
    @classmethod
    async def create_app_db(cls):
        self = cls()
        if not self.sql_engine :
            self.sql_engine = await self.get_sql_engine_app_db()
        
        return self


    async def get_sql_engine_app_db():

        engine = await create_async_engine(
            url=sql_url
            , connect_args=connect_args
        )
        Base.metadata.create_all(engine)
        return engine


sql_logs_url = URL.create(
    drivername="mariadb+pymysql",
    username=read_pwd_file("./db_init/mariadb_log_user_name"),
    password=read_pwd_file("./db_init/mariadb_log_user_pwd"),
    host="localhost",
    port=3306,
    database=os.getenv("MARIADB_FOR_LOGS"),
)

class LogsDB():
    logs_engine = None

    def __init__(self) -> None:
        pass

    @classmethod
    async def create_logs_engine(cls):
        self = cls()
        if not self.logs_engine:
            self.logs_engine = await self.get_sql_engine_logs_db()
        
        return self

    async def get_sql_engine_logs_db():

        logs_engine = await create_async_engine(
            url=sql_logs_url
            , connect_args=connect_args
        )
        LogsBase.metadata.create_all(logs_engine)
        return logs_engine
