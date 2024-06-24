from __future__ import annotations
from typing import List, Any
from sqlalchemy import ForeignKey, Table, Column, UniqueConstraint
from sqlalchemy import String, DateTime, Integer, func, DATETIME
from sqlalchemy.types import BLOB
# from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship, WriteOnlyMapped
from datetime import datetime

class Base(DeclarativeBase):
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
    role                :   Mapped[List[Role]] = relationship(secondary=role_association_table)
    create_date         :   Mapped[datetime] = mapped_column(insert_default=func.now())
    desactivation_date  :   Mapped[datetime | None] = mapped_column(DATETIME())

    # addresses   :   Mapped[List["Address"] | None] = relationship(
    #                                             back_populates="user", cascade="all, delete"
    #                                             )
    search              :   WriteOnlyMapped["SearchResults"] = relationship(
                                                                                    cascade="all, delete-orphan"
                                                                                    , passive_deletes=True
                                                                                    , order_by="SearchResults.date_of_search")

    __table_args__ = (UniqueConstraint("email"), )
            
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"

class Role(Base):
    __tablename__ = "role"
    id              : Mapped[int] = mapped_column(primary_key=True)
    scope           : Mapped[str] = mapped_column(String(30))
    description     : Mapped[str] = mapped_column(String(264))

    __table_args__ = (UniqueConstraint("scope"), )

# class Address(Base):
#     __tablename__ = "address"
#     id              :   Mapped[int] = mapped_column(primary_key=True)
#     email_address   :   Mapped[str] = mapped_column(String(264))
#     user_id         :   Mapped[int] = mapped_column(ForeignKey("user_account.id"))
#     user            :   Mapped["User"] = relationship(back_populates="addresses")

#     def __repr__(self) -> str:
#         return f"Address(id={self.id!r}, email_address={self.email_address!r})"

# m2m_paragraph_table = Table(
#     "mtm_association_pargraph_table"
#     , Base.metadata
#     , Column("searches", ForeignKey("search.id"), primary_key=True)
#     , Column("paragprahs", ForeignKey("generated_paragaphs.id"), primary_key=True)
# )

# m2m_search_platform_table = Table(
#     "mtm_association_platform_table"
#     , Base.metadata
#     , Column("searches", ForeignKey("search.id"), primary_key=True)
#     , Column("platform", ForeignKey("platforms.id"), primary_key=True)
# )

class SearchResults(Base):
    __tablename__ = "search"
    id                      :   Mapped[int] = mapped_column(primary_key=True)
    search_index            :   Mapped[str] = mapped_column(String(250))
    date_of_search          :   Mapped[datetime] = mapped_column(DateTime())
    search_type             :   Mapped[str] = mapped_column(String(3)) ### WEB or API
    # search_platform         :   Mapped[List[Platforms]] = relationship(secondary=m2m_search_platform_table, back_populates="searchs")
    search_platform         :   Mapped[str] = mapped_column(String(48))
    user_id                 :   Mapped[int | None] = mapped_column(ForeignKey("user_account.id", ondelete="cascade"))
    # user                    :   Mapped[User | None] = relationship(back_populates="search")
    generated_paragraphs    :   Mapped[List[GeneratedParagraphs]] = relationship(back_populates="search")
    # generated_paragrpahs    :   Mapped[List[GeneratedParagraphs]] = relationship(secondary=m2m_paragraph_table, back_populates="searchs")
    
    def to_dict(self) -> dict[str, Any]:
        return {field.name:getattr(self, field.name) for field in self.__table__.c}

# class Platforms(Base):
#     __tablename__ = "platforms"
#     id                      :   Mapped[int] = mapped_column(primary_key=True)
#     name                    :   Mapped[str] = mapped_column(String(48))
#     searches                :   Mapped[List[SearchResults]] = relationship(secondary=m2m_search_platform_table, back_populates="platforms")



class GeneratedParagraphs(Base):
    __tablename__ = "generated_paragaphs"
    id                          :   Mapped[int] = mapped_column(primary_key=True)
    generated_pargraphs_es_id   :   Mapped[str] = mapped_column(String(250))
    noted                       :   Mapped[int | None] = mapped_column(Integer())
    search_id                   :   Mapped[int] = mapped_column(ForeignKey("search.id"))
    search                      :   Mapped["SearchResults"] = relationship(back_populates="generated_paragraphs")
    # searchs                     :   Mapped[List[SearchResults]] = relationship(secondary=m2m_paragraph_table, back_populates="generated_paragrpahs")

    

class LogsBase(DeclarativeBase):
    pass

class Logs (LogsBase):
    __tablename__ = "logs"
    id              :   Mapped[int]         = mapped_column(primary_key=True)
    time_stamp      :   Mapped[datetime]    = mapped_column(DateTime())
    logger          :   Mapped[str]         = mapped_column(String(250))
    file_module     :   Mapped[str]         = mapped_column(String(250))
    msg_cat         :   Mapped[str]         = mapped_column(String(8))
    line            :   Mapped[int]         = mapped_column(Integer())
    msg             :   Mapped[str]         = mapped_column(BLOB())
    error_infos     :   Mapped[str]         = mapped_column(BLOB())