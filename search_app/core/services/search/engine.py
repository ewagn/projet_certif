from typing import Any
from search_app.celery_worker import Task
import spacy
from datetime import datetime


class QueryNERExtractor(Task):
    __nlp = None

    def __init__(self, query:str) -> None:
        if not isinstance(query, str):
            e_text = f"Le paramètre query doit être une stirng."
            raise ValueError(e_text)
        self.analyzed_query = self.nlp(text=query)
    
    @property
    def nlp(self):
        if not self.__nlp :
            self.__nlp = spacy.load("en_core_sci_lg")
                                    
        return self.__nlp

    # @classmethod
    # def analyze_prompt(cls, query:str):

    #     return self
    
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.analyzed_query.ents
    
    def  list_of_keywords(self) -> list[str]:

        out_list = list()
        for element in self.analyzed_query.ents:
            out_list.extend(element.text.split(" "))
        
        return out_list

# class ScientificSearch():
#     __scientific_online_databases = {
#         "google scholar" : ScholarHandler
#     } 
#     __sql_database = None

#     __es : ESHandler = None

#     def __init__(self) -> None:
#         pass

#     @property
#     def es(self):
#         if not self.__es :
#             self.__es = ESHandler().create_handler()

#         return self.__es
    
#     # @classmethod
#     # def create_search(cls):

#     #     self = cls()
#     #     self.__es_api = ESHandler().create_handler()


#     def __perform_search_in_scientific_database(self, search_params:dict):

#         search_results = list()

#         def perform_search(sci_db_engine):
#             sci_db_engine.search()
#             if sci_db.documents :
#                 search_results.extend(sci_db.documents)
            

#         async with TaskGroup() as tg :

#             for onl_dabase in self.__scientific_online_databases :
#                 async with self.__scientific_online_databases[onl_dabase](**search_params) as sci_db:
#                     tg.create_task(perform_search(search_params))
#                     # sci_db.search(query_terms=keywords, nb_pages=nb_pages)
#                     # if sci_db.parsed_pdf_documents :
#                     #     self.search_results.extend(sci_db.parsed_pdf_documents)

#     def search (self, prompt:str, search_params:dict=None, search_pltf:str='NSP', user_id:int=None):

#         if search_params :
#             nb_pages = search_params.get('nb_pages', 1)
#         else :
#             nb_pages = 1

#         # date_of_search = datetime.now()
#         # search_prompt = prompt
#         # search_keywords = await QueryNERExtractor().analyze_prompt(query=prompt)
#         # search_index = datetime.now().strftime(format="%Y%m%d%H%M") + "-".join(await self.search_keywords.list_of_keywords())

#         search_params = {
#             "date_of_search"    :   datetime.now(),
#             "search_prompt"     :   prompt,
#             "search_keywords"   :   await QueryNERExtractor().analyze_prompt(query=prompt),
#             "search_index"      :   datetime.now().strftime(format="%Y%m%d%H%M") + "-".join(await self.search_keywords.list_of_keywords()),
#             "user_id"           :   user_id,
#             "search_pltf"       :   search_pltf,
#             "nb_pages"          :   nb_pages
#         }


#         self.__es_api.create_index(**search_params)

#         self.__perform_search_in_scientific_database(search_params)

#         self.__record_search(**search_params)

#     def __record_to_database(self, search_pltf:str, date_of_search:datetime, search_index:str, user_id:int=None,  *args, **kwargs):
#         if not self.__sql_database:
#             self.__sql_database = AppDB().create_app_db()
#         search = SearchResults(
#             search_index        = search_index
#             ,date_of_search     = date_of_search
#             # ,research_type      = 
#             ,search_platform    = search_pltf
#         )
#         if user_id :
#             search.user_id = user_id
        
#         with AsyncSession(self.__sql_database.sql_engine) as session:
#             session.add(search)
#             session.commit()


#     def __record_search(self, search_pltf:str, user_id:int, date_of_search:datetime, search_index:str, *args, **kwargs):

#         if not self.search_results:
#             e_text = f"Aucun résultat de recherche à enregistrer. La recherche a-t-elle été exécutée ?"
#             raise RuntimeError(e_text)
#         else :
#             self.__es_api.create_index(index_name=search_index)
#             # es_search.add_documents(query_string=self.search_prompt, documents=self.__unwrap_documents_paragraphs, index=self.search_index)
#             self.__es_api.add_documents(query_string=self.search_prompt, documents=self.search_results, created_on=date_of_search, index=self.search_index)
#             self.__record_to_database(search_pltf=search_pltf, date_of_search=date_of_search, user_id=user_id)