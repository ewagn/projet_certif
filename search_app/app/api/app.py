from typing import Annotated
from datetime import timedelta
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator


from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fastapi import FastAPI, Depends, HTTPException, Path, Body, Query, status, Response, Security
from fastapi.security import OAuth2PasswordRequestForm

import search_app.core.logging.logging_init
from logging import getLogger

lg = getLogger("search_app.api")

from search_app.core.databases.sql_async_backend import async_engine
from search_app.core.databases.elasticsearch_async_backend import ESHandler
from search_app.core.databases.sql_async_models import Base
from search_app.app.api.models import User, UserCreate, UserDeleted, Search, SearchDeleted, SearchRequest, TaskResult, TaskCreated, Token, TokenData
import search_app.core.databases.sql_async_backend as crud
# import search_app.core.databases.sql_async_models as sql_models
import search_app.app.api.security as sec
from search_app.core.databases.sql_async_backend import get_db
from search_app.core.services.search_api import APISearch



@asynccontextmanager
async def lifespan(app : FastAPI):
    async with async_engine.begin() as conn :
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(async_engine, autoflush=False)()

    await crud.create_scopes_on_start(db=async_session)
    await crud.create_admin_user_on_start(db=async_session)

    await async_session.close()
    
    global es_async_handler
    es_async_handler = ESHandler()
    
    try :
        yield
    finally :
        await es_async_handler.es.close()


app = FastAPI(
    lifespan=lifespan
    )

Instrumentator().instrument(app).expose(app)

@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
    , db: AsyncSession = Depends(get_db)
) -> Token :
    
    user = await sec.authenticate_user(db=db, username = form_data.username, password = form_data.password)

    if not user :
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=sec.ACCESS_TOKEN_EXPIRE_MINUTES)

    scopes = user.scopes.intersection(form_data.scopes)

    access_token = await sec.create_access_token(
        data={"sub": user.email, "scopes": list(scopes)}
        , expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type='bearer')



@app.post(
        "/users/"
        , response_model=User
        , description="Route to create a user."
        , status_code=status.HTTP_201_CREATED)
async def create_user(
    user : UserCreate
    , db : AsyncSession = Depends(get_db)
    ):

    db_user = await crud.get_user_by_email(db = db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = await crud.create_user(db=db, user=user, scopes=(["me"]))
    
    if not db_user :
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User not created.")
    
    return db_user

@app.get("/users/", response_model=list[User])
async def read_users(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , skip: Annotated[int , Query()] = 0
    , limit: Annotated[int, Query()] = 100
    , db: AsyncSession = Depends(get_db)
    ) :
    
    users = await crud.get_users(db=db, skip=skip, limit=limit)

    return users

@app.get("/users/me/", response_model=User)
async def read_user_me(
    current_user : Annotated[User, Security(sec.get_current_active_user, scopes=['me'])]
):
    return current_user

@app.delete("/users/me", response_model=UserDeleted, status_code=status.HTTP_200_OK)
async def delete_user(
    current_user : Annotated[User, Security(sec.get_current_active_user, scopes=['me'])]
    , db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user(db=db, user_id=current_user.id)
    if not db_user :
        raise HTTPException(status_code=404, detail='User not found')
    
    await crud.delete_user(db=db, user=db_user)

    return db_user

@app.post(
        "/users/me/search"
        , response_model=TaskCreated
        , status_code=status.HTTP_202_ACCEPTED)
async def make_search(
    current_user : Annotated[User, Security(sec.get_current_active_user, scopes=['me'])]
    , search_params : Annotated[SearchRequest, Body()] 
    , search_type : Annotated[str, Query(
        max_length=3
        , min_length=3
        , description="Way to create search (WEB for webapp and API for API)")] = 'API'
    ) :
    """
    Lunch search in backend.
    Gives an ID you need to store for 
    """

    search_type = search_type.upper()

    if not search_type in ["API", "WEB"] :
        raise HTTPException(status_code=400, detail=f"The search_type parametes is not recognized : {search_type}")

    search_engine = APISearch()

    resp = await search_engine.make_search(search_request=search_params, user_id=current_user.id, search_type=search_type)

    return resp

@app.get("/users/me/searches/", response_model=list[Search], status_code=status.HTTP_200_OK)
async def get_search_for_user(
    current_user : Annotated[User, Security(sec.get_current_active_user, scopes=['me'])]
    , skip: Annotated[int , Query()] = 0
    , limit: Annotated[int, Query()] = 100
    , db: AsyncSession = Depends(get_db)):

    db_user = await crud.get_user(db=db, user_id=current_user.id)

    searches = await crud.get_all_searches_for_user(db=db, user=db_user, skip=skip, limit=limit)

    if searches :
        searches_out = list()
        for search in searches:
            out_dict = dict()
            out_dict.update({
                "id"                        : search.id,
                "search_index"              : search.search_index,
                "date_of_search"            : search.date_of_search,
                "research_type"             : search.research_type,
                "search_platform"           : search.search_platform,
                "user_id"                   : search.user_id,
                "generated_paragraphs"      : await es_async_handler.get_generated_paragraphs_from_ids(ids=[gp.id for gp in search.generated_paragraphs])
            })
            searches_out.append(out_dict)
    else :
        raise HTTPException(status_code=404, detail='No search found')
    
    return searches_out

@app.get("/users/me/searches/{search_id}", response_model=list[Search])
async def get_search_from_user_by_id(
    current_user : Annotated[User, Security(sec.get_current_active_user, scopes=['me'])]
    , search_id : str
    , db: AsyncSession = Depends(get_db)):

    db_user = await crud.get_user(db=db, user_id=current_user.id)

    search = await crud.get_search_by_id_from_user(db=db, user=db_user, search_id=search_id)

    if search :
        out_dict = {
            "id"                        : search.id,
            "search_index"              : search.search_index,
            "date_of_search"            : search.date_of_search,
            "research_type"             : search.research_type,
            "search_platform"           : search.search_platform,
            "user_id"                   : search.user_id,
            "generated_paragraphs"      : await es_async_handler.get_generated_paragraphs_from_ids(ids=[gp.id for gp in search.generated_paragraphs])
        }
        return out_dict
    else :
        raise HTTPException(status_code=404, detail='Search not found')

@app.delete("/users/me/searches/{search_id}", response_model=SearchDeleted, status_code=status.HTTP_200_OK)
async def delete_search_from_user(
    current_user : Annotated[User, Security(sec.get_current_active_user, scopes=['me'])]
    , search_id : str
    , db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user(db = db, user_id=current_user.id)
    
    search = await crud.get_search_by_id_from_user(db =db, user_id=current_user.id, search_id=search_id)

    if not search :
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail='Search not found')
    
    deleted = await crud.delete_search_from_user(db =db, user=db_user, search=search)

    if deleted :
        return search
    else :
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail='No modification made on database.')


@app.get("/users/{user_id}", response_model=User)
async def read_user(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , user_id: int
    , db: AsyncSession = Depends(get_db)
    ):

    db_user = await crud.get_user(db = db, user_id=user_id)

    if not db_user :
        raise HTTPException(status_code=404, detail='User not found')
    
    return db_user


@app.delete("/users/{user_id}", response_model=UserDeleted, status_code=status.HTTP_200_OK)
async def delete_user(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , user_id: int
    , db: AsyncSession = Depends(get_db)
    ):

    db_user = await crud.get_user(db=db, user_id=user_id)
    if not db_user :
        raise HTTPException(status_code=404, detail='User not found')
    
    user = UserDeleted.model_validate(db_user)
    
    deleted = await crud.delete_user(db=db, user=db_user)
    
    return user


@app.get("/users/{user_id}/searches/", response_model=list[Search], status_code=status.HTTP_200_OK)
async def get_search_for_user(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , user_id: int
    , skip: Annotated[int , Query()] = 0
    , limit: Annotated[int, Query()] = 100
    , db: AsyncSession = Depends(get_db)
    ):

    db_user = await crud.get_user(db=db, user_id=user_id)

    searches = await crud.get_all_searches_for_user(db=db, user=db_user, skip=skip, limit=limit)

    if searches :
        searches_out = list()
        for search in searches:
            out_dict = dict()
            out_dict.update({
                "id"                        : search.id,
                "search_index"              : search.search_index,
                "date_of_search"            : search.date_of_search,
                "research_type"             : search.research_type,
                "search_platform"           : search.search_platform,
                "user_id"                   : search.user_id,
                "generated_paragraphs"      : await es_async_handler.get_generated_paragraphs_from_ids(ids=[gp.id for gp in search.generated_paragraphs])
            })
            searches_out.append(out_dict)
    else :
        raise HTTPException(status_code=404, detail='No search found')
    
    return searches_out

@app.get("/users/{user_id}/searches/{search_id}", response_model=list[Search])
async def get_search_from_user_by_id(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , user_id: int
    , search_id : str
    , db: AsyncSession = Depends(get_db)):

    db_user = await crud.get_user(db=db, user_id=user_id)

    if not db_user :
        raise HTTPException(status_code=404, detail='User not found')

    search = await crud.get_search_by_id_from_user(db=db, user=db_user, search_id=search_id)

    if search :
        out_dict = {
            "id"                        : search.id,
            "search_index"              : search.search_index,
            "date_of_search"            : search.date_of_search,
            "research_type"             : search.research_type,
            "search_platform"           : search.search_platform,
            "user_id"                   : search.user_id,
            "generated_paragraphs"      : await es_async_handler.get_generated_paragraphs_from_ids(ids=[gp.id for gp in search.generated_paragraphs])
        }
        return out_dict
    else :
        raise HTTPException(status_code=404, detail='Search not found')

@app.delete("/users/{user_id}/searches/{search_id}", response_model=SearchDeleted, status_code=status.HTTP_200_OK)
async def delete_search_from_user(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , user_id: int
    , search_id : str
    , db: AsyncSession = Depends(get_db)
    ):

    db_user = await crud.get_user(db = db, user_id=user_id)

    if not db_user :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    
    search = await crud.get_search_by_id_from_user(db =db, user=db_user, search_id=search_id)

    if not search :
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail='Search not found')
    
    deleted = await crud.delete_search_from_user(db =db, user=db_user, search=search)

    if deleted :
        return search
    else :
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail='No modification made on database.')


@app.get("/searches/", response_model=list[Search])
async def get_searches(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , skip: Annotated[int , Query()] = 0
    , limit: Annotated[int, Query()] = 100
    , db: AsyncSession = Depends(get_db)
    ):
    
    searches = await crud.get_all_searches(db=db, skip=skip, limit=limit)

    if searches :
        searches_out = list()
        for search in searches:
            out_dict = dict()
            out_dict.update({
                "id"                        : search.id,
                "search_index"              : search.search_index,
                "date_of_search"            : search.date_of_search,
                "research_type"             : search.research_type,
                "search_platform"           : search.search_platform,
                "user_id"                   : search.user_id,
                "generated_paragraphs"      : await es_async_handler.get_generated_paragraphs_from_ids(ids=[gp.id for gp in search.generated_paragraphs])
            })
            searches_out.append(out_dict)
    else :
        raise HTTPException(status_code=404, detail='No search found')
    
    return searches_out

@app.get("/searches/{search_id}", response_model=Search, status_code=status.HTTP_200_OK)
async def get_search_by_id(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , search_id : str
    , db: AsyncSession = Depends(get_db)
    ):

    search = await crud.get_search_by_id(db = db, search_id=search_id)
    if search :
        out_dict = {
            "id"                        : search.id,
            "search_index"              : search.search_index,
            "date_of_search"            : search.date_of_search,
            "research_type"             : search.research_type,
            "search_platform"           : search.search_platform,
            "user_id"                   : search.user_id,
            "generated_paragraphs"      : await es_async_handler.get_generated_paragraphs_from_ids(ids=[gp.id for gp in search.generated_paragraphs])
        }
        return out_dict
    else :
        raise HTTPException(status_code=404, detail='Search not found')

    
@app.delete("/searches/{search_id}", response_model=SearchDeleted, status_code=status.HTTP_200_OK)
def delete_search(
    current_user: Annotated[User, Security(sec.get_current_active_user, scopes=['admin'])]
    , search_id : str
    , db: AsyncSession = Depends(get_db)
    ):

    search = crud.get_search_by_id(db=db, search_id=search_id)

    if search :

        crud.delete_search(db=db, search=search)

    else :
        raise HTTPException(status_code=404, detail='Search not found')
    
    return search

@app.get("/tasks/{task_id}", response_model=TaskResult)
async def get_task(
    task_id : str
    , response : Response
    ):


    response_engine = APISearch()
    result = await response_engine.get_task(task_id=task_id)

    if not result :
        raise HTTPException(status_code=404, detail='Task not found')

    if result.state == "SUCCESS" :
        response.status_code = status.HTTP_200_OK
    
    else :
        response.status_code = status.HTTP_202_ACCEPTED
    
    return result