from sqlalchemy import URL, create_engine
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

engine = create_engine(
    url=sql_url
    , connect_args=connect_args
)
Base.metadata.create_all(engine)

sql_logs_url = URL.create(
    drivername="mariadb+pymysql",
    username=read_pwd_file("./db_init/mariadb_log_user_name"),
    password=read_pwd_file("./db_init/mariadb_log_user_pwd"),
    host="localhost",
    port=3306,
    database=os.getenv("MARIADB_FOR_LOGS"),
)
logs_engine = create_engine(
    url=sql_logs_url
    , connect_args=connect_args
)
LogsBase.metadata.create_all(logs_engine)