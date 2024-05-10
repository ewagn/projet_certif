from datetime import datetime
from celery import chain, group

from search_app.celery import app, lg
from search_app.core.services.parsing.pdf_parsing import Document

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

@app.task
def parse_documents (papers:list[tuple[bytes, str]], user_query:str, search_index:str, created_on : datetime) -> list[Document] | None :
    
    parsed_documents = group(
            create_documents_from_google_scholar.s(pdf_file = pdf_file, ris_file = ris_file, created_on = created_on, user_query = user_query, search_index=search_index)
            for pdf_file, ris_file in papers)()

    parse_documents = [doc for doc in parse_documents.get() if doc]
    return parsed_documents

@app.task
def parse_documents_to_dict(papers : list[tuple[bytes, str]], user_query : str, search_index : str) -> list[dict[str, str]]:
    created_on = datetime.now()

    parsed_documents = (
        group(
            create_documents_from_google_scholar.s(pdf_file = pdf_file, ris_file = ris_file, created_on = created_on, user_query = user_query, search_index=search_index) 
            for pdf_file, ris_file in papers)
        | get_documents_paragraphs_for_put_on_db.s())()

    return parsed_documents