from __future__ import annotations
from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.types import BLOB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"
    id          :   Mapped[int] = mapped_column(primary_key=True)
    firstname   :   Mapped[str] = mapped_column(String(30))
    lastname    :   Mapped[str | None] = mapped_column(String(30))
    username    :   Mapped[str] = mapped_column(String(30))
    addresses   :   Mapped[List["Address"] | None] = relationship(
                                                back_populates="user", cascade="all, delete"
                                                )
    search      :   Mapped[List["SearchResults"] | None] = relationship(back_populates="user")
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"

class Address(Base):
    __tablename__ = "address"
    id              :   Mapped[int] = mapped_column(primary_key=True)
    email_address   :   Mapped[str] = mapped_column(String(264))
    user_id         :   Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    user            :   Mapped["User"] = relationship(back_populates="addresses")

    def __repr__(self) -> str:
        return f"Address(id={self.id!r}, email_address={self.email_address!r})"

class SearchResults(Base):
    __tablename__ = "search"
    id              :   Mapped[int] = mapped_column(primary_key=True)
    search_index    :   Mapped[str] = mapped_column(String(250))
    date_of_search  :   Mapped[datetime] = mapped_column(DateTime())
    # research_type   :   Mapped[str] = mapped_column(String(3))
    search_platform :   Mapped[str] = mapped_column(String(3)) ### WEB or API
    user_id         :   Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    user            :   Mapped[User | None] = relationship(back_populates="search")

class LogsBase(DeclarativeBase):
    pass

class Logs (LogsBase):
    __tablename__ = "logs"
    id              :   Mapped[int] = mapped_column(primary_key=True)
    time_stamp      :   Mapped[datetime] = mapped_column(DateTime())
    logger          :   Mapped[str] = mapped_column(String(250))
    file_moduel     :   Mapped[str] = mapped_column(String(250))
    msg_cat         :   Mapped[str] = mapped_column(String(8))
    line            :   Mapped[int] = mapped_column(Integer())
    msg             :   Mapped[str] = mapped_column(BLOB())
    error_infos     :   Mapped[str] = mapped_column(BLOB())