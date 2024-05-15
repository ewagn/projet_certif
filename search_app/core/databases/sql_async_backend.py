from typing import Sequence, Iterable
from datetime import datetime
from passlib.context import CryptContext
import ssl
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import URL, select, ScalarResult, Result, and_
from sqlalchemy.orm import joinedload
from ast import literal_eval
import os
from logging import getLogger

lg = getLogger("search_app.api")

from search_app.core.databases.sql_backend import read_pwd_file
from search_app.core.databases.sql_async_models import User, SearchResults, Role
from search_app.app.api.models import UserCreate

sql_url = URL.create(
    drivername="mariadb+aiomysql",
    username=os.getenv("MARIADB_USER"),
    password=read_pwd_file(os.getenv("MARIADB_PASSWORD_FILE")),
    host=os.getenv("MARIADB_ROOT_HOST"),
    # host="mariadb",
    port=3306,
    database=os.getenv("MARIADB_DATABASE"),
)

ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
ssl_context.load_verify_locations(os.getenv("CLIENT_CERTIF_PATH") + "/ca-cert.pem")
ssl_context.load_cert_chain(certfile=os.getenv("CLIENT_CERTIF_PATH") + "/client-cert.pem", keyfile=os.getenv("CLIENT_CERTIF_PATH") + "/client-key.pem",)
ssl_context.check_hostname = False

connect_args = {
    "ssl": ssl_context
}

async_engine = create_async_engine(
    url = sql_url
    , connect_args = connect_args
)
SessionLocal = async_sessionmaker(autoflush=False, bind=async_engine)

async def get_db():

    db = SessionLocal()

    try :
        yield db
    finally :
        await db.close()

pwd_context =  CryptContext(schemes=['bcrypt'], deprecated="auto")

async def create_scopes_on_start(db : AsyncSession):

    scopes = literal_eval(os.getenv('API_SCOPES'))
    # async with db.begin():
    to_commit = False
    for scope in scopes :
        db_scope = await db.execute(
            select(Role)
                .where(Role.scope == scope)
        )
        db_scope = db_scope.one_or_none()
        if not db_scope :
            to_commit = True
            to_record_scope = Role(
                scope = scope,
                description = scopes[scope]
            )
            db.add(to_record_scope)
    
    if to_commit :
        await db.commit()


async def get_user(db : AsyncSession, user_id : int) -> User :
    # async with db.begin():
    users = await db.scalars(
        select(User)
            .filter_by(id=user_id)
            .limit(1)
    )

    return users.unique().one_or_none()

async def get_user_by_email(db : AsyncSession, email : str) -> User:
    # async with db.begin():
    users = await db.scalars(
        select(User)
            .filter_by(email = email)
            .limit(1)
    )

    return users.unique().one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> Sequence[User]:
    # async with db.begin():
    users = await db.scalars(
        select(User)
            .offset(skip)
            .limit(limit)
    )

    return users.unique().all()

async def create_user(db: AsyncSession, user: UserCreate, scopes : Iterable[str]) :
    hashed_password = pwd_context.hash(secret=user.password)


    # async with db.begin():

    db_scopes = await db.scalars(
        select(Role)
            .where(Role.scope.in_(scopes))
    )
    db_scopes = db_scopes.all()
    
    db_user = User(
        email       = user.email,
        password    = hashed_password,
        firstname   = user.firstname,
        lastname    = user.lastname
    )
    db_user.role.extend(db_scopes)

    try:
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    except Exception :
        lg.error(f"Erreur de crétation de l'utilisateur {db_user.email}", exc_info=True)
        db_user = None
    
    return db_user

async def create_admin_user_on_start(db : AsyncSession) :
    admin_email = read_pwd_file(os.getenv('API_ADMIN_USERNAME'))

    db_user = await get_user_by_email(db=db, email=admin_email)

    if not db_user :

        admin_user_to_record = UserCreate(
            email       =   admin_email,
            password    =   read_pwd_file(os.getenv('API_ADMIN_PWD')),
        )
        await create_user(db=db, user=admin_user_to_record, scopes=set(literal_eval(os.getenv('API_SCOPES')).keys()))



async def delete_user(db : AsyncSession, user : User) :
    # async with db.begin():

    await db.delete(user)
    await db.commit()

    return True

async def get_search_by_id(db: AsyncSession, search_id : int) -> SearchResults :
    # async with db.begin():
    search = await db.scalars(
        select(SearchResults)
            .filter_by(id = search_id)
            .limit(1)
    )

    return search.unique().one_or_none()

async def get_last_search(db: AsyncSession, user_id : int) :
    # async with db.begin():
    search = await db.scalars(
        select(SearchResults)
        .filter_by(user_id = user_id)
        .order_by(SearchResults.date_of_search.asc())
        .limit(1)
    )
    
    return search.unique().one_or_none()

async def get_all_searches(db: AsyncSession, skip: int = 0, limit: int = 100) -> Sequence[SearchResults]:
    # async with db.begin():
    searches = await db.scalars(
        select(SearchResults)
            .offset(skip)
            .limit(limit)
    )
    return searches.unique().all()

async def get_all_searches_for_user(db: AsyncSession, user : User, skip: int = 0, limit: int = 100) :

    # async with db.begin():
    searches = await db.scalars(
        user.search.select()
            .offset(skip)
            .limit(limit)
    )
    
    return searches.unique().all()

async def get_searchs_from_date(db: AsyncSession, user_id : int,  date : datetime, skip: int = 0, limit: int = 100) -> Sequence[SearchResults] :
    # async with db.begin():
    searchs = await db.scalars(
        select(SearchResults)
        .filter(
            and_(
                SearchResults.user_id == user_id
                , SearchResults.date_of_search >= date))
        .order_by(SearchResults.date_of_search.desc())
        .offset(skip)
        .limit(limit=limit)
    )

    return searchs.unique().all()

async def get_search_by_id_from_user(db: AsyncSession, user : User, search_id : int) -> SearchResults :
    # async with db.begin():
    search = await db.scalars(
        user.search.select()
            .filter_by(id=search_id)
            .limit(1)
    )
    
    return search.unique().one_or_none()

async def delete_search(db: AsyncSession, search : SearchResults) -> bool:
    # async with db.begin():
    db.delete(search)
    db.commit()

    return True
    
async def delete_search_from_user(db: AsyncSession, user : User, search : SearchResults) -> bool :
    
    # async with db.begin():
    user.search.remove(search)
    db.commit()

    return True