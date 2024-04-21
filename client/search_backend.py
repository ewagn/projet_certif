from logging import getLogger
from asyncio import TaskGroup
import spacy
from typing import Any, Iterable, Optional
from datetime import datetime

# from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from client.elasticsearch_backend import ESHandler
from client.sci_bases_handlers import ScholarHandler
from client.sql_models import SearchResults
from client.sql_backend import AppDB

lg = getLogger("app")

class QueryNERExtractor():
    __nlp = spacy.load("en_core_sci_lg")

    def __init__(self) -> None:
        pass

    @classmethod
    async def analyze_prompt(cls, query:str):
        if not isinstance(query, str):
            e_text = f"Le paramètre query doit être une stirng."
            raise ValueError(e_text)
        
        self = cls()
        
        self.analyzed_query = self.__nlp(text=query)

        return self
    
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.analyzed_query.ents
    
    async def  list_of_keywords(self):

        out_list = list()
        for element in self.analyzed_query.ents:
            out_list.extend(element.text.split(" "))
        
        return out_list

class ScientificSearch():
    __scientific_online_databases = {
        "google scholar" : ScholarHandler
    } 
    __sql_database = None

    def __init__(self) -> None:
        pass
    
    @classmethod
    async def create_search(cls):

        self = cls()
        self.__es_api = await ESHandler().create_handler()


    async def __perform_search_in_scientific_database(self, search_params:dict):

        search_results = list()

        async def perform_search(sci_db_engine):
            await sci_db_engine.search()
            if sci_db.documents :
                search_results.extend(sci_db.documents)
            

        async with TaskGroup() as tg :

            for onl_dabase in self.__scientific_online_databases :
                async with self.__scientific_online_databases[onl_dabase](**search_params) as sci_db:
                    tg.create_task(perform_search(search_params))
                    # sci_db.search(query_terms=keywords, nb_pages=nb_pages)
                    # if sci_db.parsed_pdf_documents :
                    #     self.search_results.extend(sci_db.parsed_pdf_documents)

    async def search (self, prompt:str, search_params:dict=None, search_pltf:str='NSP', user_id:int=None):

        if search_params :
            nb_pages = search_params.get('nb_pages', 1)
        else :
            nb_pages = 1

        # date_of_search = datetime.now()
        # search_prompt = prompt
        # search_keywords = await QueryNERExtractor().analyze_prompt(query=prompt)
        # search_index = datetime.now().strftime(format="%Y%m%d%H%M") + "-".join(await self.search_keywords.list_of_keywords())

        search_params = {
            "date_of_search"    :   datetime.now(),
            "search_prompt"     :   prompt,
            "search_keywords"   :   await QueryNERExtractor().analyze_prompt(query=prompt),
            "search_index"      :   datetime.now().strftime(format="%Y%m%d%H%M") + "-".join(await self.search_keywords.list_of_keywords()),
            "user_id"           :   user_id,
            "search_pltf"       :   search_pltf,
            "nb_pages"          :   nb_pages
        }


        await self.__es_api.create_index(**search_params)

        await self.__perform_search_in_scientific_database(search_params)

        await self.__record_search(**search_params)

    async def __record_to_database(self, search_pltf:str, date_of_search:datetime, search_index:str, user_id:int=None,  *args, **kwargs):
        if not self.__sql_database:
            self.__sql_database = await AppDB().create_app_db()
        search = SearchResults(
            search_index        = search_index
            ,date_of_search     = date_of_search
            # ,research_type      = 
            ,search_platform    = search_pltf
        )
        if user_id :
            search.user_id = user_id
        
        async with AsyncSession(self.__sql_database.sql_engine) as session:
            session.add(search)
            session.commit()


    async def __record_search(self, search_pltf:str, user_id:int, date_of_search:datetime, search_index:str, *args, **kwargs):

        if not self.search_results:
            e_text = f"Aucun résultat de recherche à enregistrer. La recherche a-t-elle été exécutée ?"
            raise RuntimeError(e_text)
        else :
            await self.__es_api.create_index(index_name=search_index)
            # es_search.add_documents(query_string=self.search_prompt, documents=self.__unwrap_documents_paragraphs, index=self.search_index)
            await self.__es_api.add_documents(query_string=self.search_prompt, documents=self.search_results, created_on=date_of_search, index=self.search_index)
            await self.__record_to_database(search_pltf=search_pltf, date_of_search=date_of_search, user_id=user_id)