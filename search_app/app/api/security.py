from typing import Annotated
from datetime import timedelta, datetime, timezone
from pydantic import ValidationError
import os
from ast import literal_eval 

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import status, Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from passlib.context import CryptContext
from jose import JWTError, jwt

from search_app.app.api.models import UserInDB, TokenData, User
import search_app.core.databases.sql_async_backend as crud
from search_app.core.databases.sql_async_backend import get_db, SessionLocal
from search_app.core.databases.sql_backend import read_pwd_file
# import search_app.core.databases.sql_async_models as sql_models


# SECRET_KEY = 'c94a644abcf412a66613c4db16344e3107898d004c819bc38a6fb794e2870396'
SECRET_KEY = read_pwd_file(os.getenv("SECRET_KEY"))

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 12*60

pwd_context =  CryptContext(schemes=['bcrypt'], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token"
    , scopes=literal_eval(os.getenv('API_SCOPES'))
    # , scopes={
    #     "me"        : 'Access to operations from current User.',
    #     "admin"     : 'Access to operations for global administration.'
    # }
    )

def verify_password(plain_password : str, hashed_password : str):
    return pwd_context.verify(secret=plain_password, hash=hashed_password)

def get_password_hash(password : str):
    return pwd_context.hash(password)

# def get_user(db, username : str):
#     if username in db:
#         user_dict = db[username]
#         return UserInDB(**user_dict)

async def authenticate_user(db : AsyncSession,  username: str, password: str):

    user = await crud.get_user_by_email(db=db, email=username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

async def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
        security_scopes: SecurityScopes
        , token: Annotated[str, Depends(oauth2_scheme)]
        , db: AsyncSession = Depends(get_db)
        ):
    
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)

    except (JWTError, ValidationError):
        raise credentials_exception

    user = await crud.get_user_by_email(db=db, email=token_data.username)

    if user is None:
        raise credentials_exception
    
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
        
    return User.model_validate(user)

async def get_current_active_user(
    current_user: Annotated[User, Security(get_current_user, scopes=["me"])]
    ):

    if current_user.desactivation_date :
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user