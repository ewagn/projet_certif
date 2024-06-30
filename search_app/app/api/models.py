from pydantic import BaseModel, Field, computed_field, ValidationError, ValidationInfo, field_validator, ConfigDict
from datetime import datetime
import os

class Token(BaseModel):
    access_token    : str
    token_type      : str

class TokenData(BaseModel):
    username    : str | None = None
    scopes      : list[str] = []


class UserBase(BaseModel):
    email       : str
    firstname   : str | None = None
    lastname    : str | None = None

    @field_validator('email')
    @classmethod
    def check_email(cls, v : str, info: ValidationInfo) -> str:
        if isinstance(v, str):
            is_email = "@" in v
            assert is_email, f"{info.field_name} must contain a '@'."
        return v
    

class UserCreate(UserBase):
    password : str

class UserOut(UserBase):
    id                  : int
    scopes              : set[str]
    create_date         : datetime
    desactivation_date  : datetime | None = None  

class User(UserOut):
    model_config = ConfigDict(from_attributes=True)

class UserDeleted(UserOut):
    model_config = ConfigDict(from_attributes=True)

    deleted             : bool = True

# class GeneratedParagraph(BaseModel):
#     id                          : int
#     generated_pargraphs_es_id   : str
#     noted                       : int

class SummerizedParagraph(BaseModel):
    id          : str
    title       : str
    content     : str
    refs        : list[str]

    # class Config:
    #     orm_mode = True

class UserInDB(User):
    hashed_password: str

class SearchBase(BaseModel):
    search_platform         : str

class SearchOneRetrieve(SearchBase):
    id                      : int
    search_index            : str
    search_type             : str


class SearchDeleted(SearchOneRetrieve):
    model_config = ConfigDict(from_attributes=True)

    user_id                 : int
    deleted                 : bool = True

class Search(SearchOneRetrieve):
    user_id                 : int
    date_of_search          : datetime
    generated_paragraphs    : list[SummerizedParagraph]

class SearchRequest(SearchBase):
    prompt          : str
    # search_type     : str = "api"
    search_platform : str = "google_scholar"

class TaskBase(BaseModel):
    id      : str
    # name    : str

class TaskCreated(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    send_time       : datetime = datetime.now()

    @computed_field
    def retrieve_result_url(self) -> str :
        return os.getenv('API_ENDPOINT') + "/tasks/" + self.id

    # retrive_url     : str = Field()


class TaskResult(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    status  : str
    result  : Search | str | None = None
    @field_validator('result')
    @classmethod
    def result_validator(cls, v : str, info: ValidationInfo) -> Search | str | None :
        if isinstance(v, str) :
            return v
        elif isinstance(v, dict):
            return Search.model_validate(v)
        else :
            return None