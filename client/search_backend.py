from logging import getLogger
import spacy
from typing import Any
from datetime import datetime

from sqlalchemy import select
# from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from client.elasticsearch_backend import Search, es_search
from client.sci_bases_handlers import ScholarHandler
from client.sql_models import SearchResults
from client.sql_backend import AppDB

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
    __corpus_data_base = Search()
    __scientific_online_databases = {
        "google scholar" : ScholarHandler
    } 
    __sql_database = None

    def __init__(self) -> None:

        self.search_index   = None
        self.search_prompt  = None
        self.search_results = None


    async def __perform_search_in_scientific_database(self, nb_pages:int):

        keywords = await self.search_keywords.list_of_keywords()

        self.search_results = list()
        for onl_dabase in self.__scientific_online_databases :
            async with self.__scientific_online_databases[onl_dabase]() as sci_db:
                sci_db.search(query_terms=keywords, nb_pages=nb_pages)
                if sci_db.parsed_pdf_documents :
                    self.search_results.extend(sci_db.parsed_pdf_documents)

    async def search (self, prompt:str, search_params:dict=None):

        if search_params :
            nb_pages = search_params.get('nb_pages', 1)
        else :
            nb_pages = 1

        self.search_prompt = prompt
        self.search_keywords = await QueryNERExtractor().analyze_prompt(query=prompt)
        self.search_index = datetime.now().strftime(format="%Y%m%d%H%M") + "-".join(await self.search_keywords.list_of_keywords())

        await es_search.create_index(index_name=self.search_index)

        await self.__perform_search_in_scientific_database(nb_pages=nb_pages)

        await self.__record_search()

    async def __record_to_database(self, search_pltf:str, date_of_search, user_id:int=None):
        if not self.__sql_database:
            self.__sql_database = await AppDB().create_app_db()
        search = SearchResults(
            search_index        = self.search_index
            ,date_of_search     = date_of_search
            # ,research_type      = 
            ,search_platform    = search_pltf
        )
        if user_id :
            search.user_id = user_id
        
        async with AsyncSession(self.__sql_database.sql_engine) as session:
            session.add(search)
            session.commit()


    async def __record_search(self, search_pltf:str='NSP', user_id:int=None):

        if not self.search_results:
            e_text = f"Aucun résultat de recherche à enregistrer. La recherche a-t-elle été exécutée ?"
            raise RuntimeError(e_text)
        else :
            date_of_search = datetime.now()
            await es_search.create_index(index_name=self.search_index)
            # es_search.add_documents(query_string=self.search_prompt, documents=self.__unwrap_documents_paragraphs, index=self.search_index)
            await es_search.add_documents(query_string=self.search_prompt, documents=self.search_results, created_on=date_of_search, index=self.search_index)
            await self.__record_to_database(search_pltf=search_pltf, date_of_search=date_of_search, user_id=user_id)

