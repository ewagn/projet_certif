from __future__ import annotations
from typing import List
from sqlalchemy import ForeignKey, Table, Column, UniqueConstraint
from sqlalchemy import String, DateTime, Integer, func, DATETIME
from sqlalchemy.types import BLOB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship, WriteOnlyMapped
from datetime import datetime


class Base(DeclarativeBase, AsyncAttrs):
    pass

role_association_table = Table(
    "role_association_table"
    , Base.metadata
    , Column("user_id", ForeignKey("user_account.id"))
    , Column("role_id", ForeignKey("role.id"))
)

class User(Base):
    __tablename__ = "user_account"
    
    id                  :   Mapped[int] = mapped_column(primary_key=True)
    email               :   Mapped[str] = mapped_column(String(264))
    password            :   Mapped[str] = mapped_column(String(264))
    firstname           :   Mapped[str | None] = mapped_column(String(30))
    lastname            :   Mapped[str | None] = mapped_column(String(30))
    role                :   Mapped[list[Role]] = relationship(secondary=role_association_table, lazy="joined")
    create_date         :   Mapped[datetime] = mapped_column(insert_default=func.now())
    desactivation_date  :   Mapped[datetime | None] = mapped_column(DATETIME())
    search              :   WriteOnlyMapped["SearchResults"] = relationship(
                                                                                    cascade="all, delete-orphan"
                                                                                    , passive_deletes=True
                                                                                    , order_by="SearchResults.date_of_search")

    __table_args__ = (UniqueConstraint("email"), )

    @property
    def scopes(self) -> set[str] | None:
        if self.role :
            set_out = set()
            for role in self.role:
                set_out.add(role.scope)
            return set_out
        else :
            return None
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.email!r}, fullname={self.firstname!r} {self.lastname!r})"


class Role(Base):
    __tablename__ = "role"
    id              : Mapped[int] = mapped_column(primary_key=True)
    scope           : Mapped[str] = mapped_column(String(30))
    description     : Mapped[str] = mapped_column(String(264))

class SearchResults(Base):
    __tablename__ = "search"
    id                      :   Mapped[int] = mapped_column(primary_key=True)
    search_index            :   Mapped[str] = mapped_column(String(250))
    date_of_search          :   Mapped[datetime] = mapped_column(DateTime())
    search_type             :   Mapped[str] = mapped_column(String(3)) ### WEB or API
    search_platform         :   Mapped[str] = mapped_column(String(48))
    user_id                 :   Mapped[int | None] = mapped_column(ForeignKey("user_account.id", ondelete="cascade"))
    generated_paragraphs    :   Mapped[List['GeneratedParagraphs']] = relationship(back_populates="search", lazy="joined")


class GeneratedParagraphs(Base):
    __tablename__ = "generated_paragaphs"
    id                          :   Mapped[int] = mapped_column(primary_key=True)
    generated_pargraphs_es_id   :   Mapped[str] = mapped_column(String(250))
    noted                       :   Mapped[int | None] = mapped_column(Integer())
    search_id                   :   Mapped[int] = mapped_column(ForeignKey("search.id"))
    search                      :   Mapped['SearchResults'] = relationship(back_populates="generated_paragraphs", lazy="noload")

    