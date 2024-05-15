from datetime import datetime
from celery import chain, group, chord
from celery.utils.log import get_task_logger
from logging import Logger

from search_app.celery_worker import app
from search_app.core.services.parsing.pdf_parsing import Document

lg = get_task_logger(__name__)

@app.task(bind=True)
def create_documents_from_google_scholar(self, pdf_file:bytes, ris_file:str, created_on:datetime, user_query:str, search_index:str) -> Document | None :
    lg.info("Scrapping de la page google scholar.")
    database = "google_scholar"
    doc = Document().create_document(pdf_file=pdf_file, ris_file=ris_file, database=database, created_on=created_on, user_query=user_query, search_index=search_index, es_handler=self.esh)

    return doc

@app.task
def get_documents_paragraphs_for_put_on_db(documents = list[Document | None]) -> list[dict[str, str]]:

    documents_elements_to_put_on_db = list()
    for document in documents :
        if document :
            documents_elements_to_put_on_db.extend(document())
    
    return documents_elements_to_put_on_db

@app.task(name='parse_documents')
def parse_documents (papers : list[list[tuple[bytes, str]]], user_query:str, search_index:str, created_on : datetime, *args, **kwargs) -> list[Document | None] | None :
    
    parsing_documents_list = list()

    for papers_list in papers:
        for pdf_file, ris_file in papers_list :
            parsing_documents_list.append(
                create_documents_from_google_scholar.s(pdf_file = pdf_file, ris_file = ris_file, created_on = created_on, user_query = user_query, search_index=search_index)()
            )


    result = group(parsing_documents_list)()

    return result


# @app.task
# def parse_documents_to_dict(papers : list[tuple[bytes, str]], user_query : str, search_index : str) -> list[dict[str, str]]:
#     created_on = datetime.now()

#     parsed_documents = (
#         chord(
#             create_documents_from_google_scholar.s(pdf_file = pdf_file, ris_file = ris_file, created_on = created_on, user_query = user_query, search_index=search_index) 
#             for pdf_file, ris_file in papers).s()
#         | get_documents_paragraphs_for_put_on_db.s())

#     return parsed_documents