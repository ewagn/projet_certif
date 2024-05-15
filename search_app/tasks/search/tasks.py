from elasticsearch import helpers
import itertools as it
from typing import Any
from datetime import datetime
from celery import chain, group, chord
from sqlalchemy.orm import Session
from celery.utils.log import get_task_logger
from logging import Logger


from search_app.celery_worker import app
from search_app.tasks.web_scrapping.tasks import get_papers_results_from_google_scholar, get_google_scholar_search_url, get_webdriver_on_page, get_research_pages_on_gs, retrieve_files
from search_app.tasks.paper_parser.tasks import parse_documents
from search_app.tasks.summerize.tasks import summerization_step, summerize_paragraph, record_to_es
from search_app.core.databases.sql_models import SearchResults
from search_app.core.services.parsing.pdf_parsing import Document
from search_app.core.services.search.engine import QueryNERExtractor
from search_app.core.services.text_summarize.models import SummerizedParagraph

lg : Logger = get_task_logger(__name__)

@app.task(bind = True)
def add_pdfs_to_es(self, documents : list[Document]):

    documents_where_pdf_to_record = [doc for doc in documents if doc and not doc.pdf_exists]

    resp = helpers.bulk(client=self.esh, actions=[doc.get_pdf() for doc in documents_where_pdf_to_record])

    results = resp.get("items")

    if results:
        for document, result in zip(documents_where_pdf_to_record, results) :
            document.es_pdf_id = result["_id"]
    else :
        e_text = "Les documents pdf n'ont pu être enregistrés dans la base de données"
        lg.error(e_text)
        raise RuntimeError(e_text)
    
    return documents

@app.task(bind = True)
def add_paragraph_to_es(self, documents : list[Document]) -> None :
    
    resp = helpers.bulk(self.esh, actions=it.chain.from_iterable([doc() for doc in documents]))

    if resp['errors'] :
        errors = list()
        for item in resp['items'] :
            data = list(item.values())[0]
            if "error" in data :
                errors.append(f'{data["error"]["type"]} -> {data["error"]["reason"]}')
        
        e_text = "Des erreurs sont apparues lors de l'ajout des paragraphs a la base de données elasticsearch : " + ", ".join(errors)
        lg.error(e_text)
        raise RuntimeError(e_text)
        

# @app.task
# def create_search_index(query_terms : list[str]) -> str :
#     search_index = "search-index-" + datetime.now().strftime(format="%Y%m%d%H%M") + "-".join(query_terms)
#     return search_index


@app.task(bind=True)
def search_in_es_database(self, prompt: str) -> dict[str, Any]:
    result = self.esh.search_from_query(query_promt=prompt)
    return result


@app.task
def get_paragraphs_content_for_answer(search_result : dict[str, Any]) -> list[tuple[str, dict]]:
    buckets_result = search_result['aggregations']['sample']['selected_paragraphs']['buckets']

    paragraphs_by_cathegory = list()

    if buckets_result :
        for bucket in buckets_result :

            category  = dict()
            for doc in bucket['docs']['hits']['hits'] :
                category[category].update({
                    doc['_id'] : {
                        'content'   : doc['_source']['content'],
                        'pdf_id'    : doc['_source']['es_pdf_id'],
                    }
                })
            paragraphs_by_cathegory.append((category, bucket['key']))

    
    return paragraphs_by_cathegory

@app.task(bind=True)
def add_search_to_db(self, generated_paragrpahs : list[SummerizedParagraph], search_index : str, created_on : datetime, research_type : str, search_platform : str, user_id : int | None = None, *args, **kwargs) -> list[dict[str, Any]]:
    search = SearchResults(
        search_index            = search_index
        , date_of_search        = created_on
        , research_type         = research_type
        , search_platform       = search_platform
        , user_id               = user_id
        , generated_paragrpahs  = [p.get_sql_model() for p in generated_paragrpahs]
    )
    with Session(self.sql_db) as session :
        session.add(search)
        session.commit()
        session.refresh(search)

    lg.info(f"La rechecherche à été ajoutée à la base de donnée : {search.id}")

    search_to_return = search.to_dict()

    search_to_return['generated_paragrpahs'] = [gp() for gp in generated_paragrpahs]

    return generated_paragrpahs

@app.task
def retrieve_bibliographical_info(self, summerized_paragraph : SummerizedParagraph) -> SummerizedParagraph:
    
    lg.info("Récupération des données bibliographiques du paragraphe généré.")
    summerized_paragraph.retrieve_bibliographical_info(es_handler=self.esh)

    return summerized_paragraph


# @app.task
# def perform_search(prompt : str, search_params : dict| None = None, user_id : int | None = None) -> dict[str, Any]:
    
#     created_on = datetime.now()
#     query_terms = QueryNERExtractor(query=prompt)
#     search_index = "search-index-" + created_on.strftime(format="%Y%m%d%H%M") + "-".join(query_terms)

#     resp = chain(
#         get_papers_results_from_google_scholar.s(query_terms=query_terms.list_of_keywords())
#         , parse_documents.s(user_query = prompt, search_index=search_index, created_on=created_on)
#         , add_pdfs_to_es.s()
#         , add_paragraph_to_es.s()
#         , search_in_es_database.s(prompt=prompt)
#         , get_paragraphs_content_for_answer.s()
#     )()

#     return resp

# @app.task
# def retrieve_pages(query_terms : list[str], nb_pages:int):
#     result = (
#         (get_google_scholar_search_url.s(query_terms=query_terms.list_of_keywords(), query_params=search_params) 
#                         | get_webdriver_on_page.s() 
#                         | get_research_pages_on_gs.s(nb_pages=nb_pages))
#     )()
#     return result

#### BACK
# @app.task
# def parsing_step(papers : list[tuple[bytes, str]], user_query: str, search_index: str, created_on: datetime, *args, **kwargs) -> list[tuple[str, dict]]:
    
#     result = (parse_documents.s(papers = papers, user_query = user_query, search_index=search_index, created_on=created_on) 
#                             | add_pdfs_to_es.s()
#                             | add_paragraph_to_es.s()
#                             | search_in_es_database.s(prompt=user_query)
#                             | get_paragraphs_content_for_answer.s())()
    
#     return result


# @app.task
# def parsing_step(papers : list[list[tuple[bytes, str]]], user_query: str, search_index: str, created_on: datetime, *args, **kwargs) -> list[tuple[str, dict]]:
    
#     result = (app.signature('parse_documents', kwargs={'papers' : papers, 'user_query' : user_query, 'search_index' : search_index, 'created_on' : created_on}) 
#                             | add_pdfs_to_es.s()
#                             | add_paragraph_to_es.s()
#                             | search_in_es_database.s(prompt=user_query)
#                             | get_paragraphs_content_for_answer.s())()
    
#     return result

#### BACK
# @app.task
# def parse_documents_chain(query_terms: list[str], nb_pages : int, user_query: str, search_index: str, created_on: datetime, query_params: dict | None = None) ->  list[tuple[str, dict]]:
#     get_papers_results_from_google_scholar = [
#         retrieve_files.s(page=page)
#         for page in retrieve_pages(query_terms=query_terms, nb_pages=nb_pages, query_params = query_params).get(disable_sync_subtasks=False)]
    
#     result = chord(get_papers_results_from_google_scholar)(parsing_step.s(user_query = user_query, search_index=search_index, created_on = created_on))()

#     return result


# @app.task
# def parse_documents_chain(query_terms: list[str], nb_pages : int, user_query: str, search_index: str, created_on: datetime, query_params: dict | None = None) ->  list[tuple[str, dict]]:
#     get_papers_results_from_google_scholar = [
#         app.signature('retrieve_files', kwargs={'page' : page})
#         for page in app.signature('retrieve_pages', kwargs={'query_terms' : query_terms, 'nb_pages' : nb_pages, 'query_params' : query_params})]
    
#     result = chord(get_papers_results_from_google_scholar)(parsing_step.s(user_query = user_query, search_index=search_index, created_on = created_on))

#     return result

@app.task(name='search_app.tasks.search')
def get_search_results(prompt : str, search_type : str, search_platform : str,  search_params : dict| None = None, user_id : int | None = None) -> dict[str, Any]:
    
    created_on = datetime.now()
    query_terms = QueryNERExtractor(query=prompt)
    search_index = "search-index-" + created_on.strftime(format="%Y%m%d%H%M") + "-".join(query_terms.list_of_keywords())
    
    lg.info(f"Réalisation d'une recherche avec les termes {', '.join(query_terms.list_of_keywords())}.")

    lg.info("Scrapping de la recherche google scholar.")
    
    if search_params :
        nb_pages = search_params.get("nb_pages", 1)
    else :
        nb_pages = 1

    # url = get_google_scholar_search_url()
    # first_webdriver, _ = get_webdriver_on_page(url=url)
    # search_pages = get_research_pages_on_gs(first_webdriver, nb_pages=nb_pages)


    
    
    result = chain(
        # get_papers_results_from_google_scholar.s(query_terms = query_terms.list_of_keywords(), nb_pages = nb_pages, query_params = search_params)
        get_google_scholar_search_url.s(query_terms=query_terms.list_of_keywords(), query_params=search_params)
        | get_webdriver_on_page.s()
        | get_research_pages_on_gs.s(nb_pages=nb_pages)
        # , retrieve_files.s()
        # , parse_documents.s(user_query = prompt, search_index = search_index, created_on = created_on) 
        # , add_pdfs_to_es.s()
        # , add_paragraph_to_es.s()
        # , search_in_es_database.s(prompt=prompt)
        # , get_paragraphs_content_for_answer.s()
        # , summerization_step.s(search_index = search_index, created_on = created_on)
        # , add_search_to_db.s(search_index=search_index, created_on=created_on, research_type=search_type, search_platform=search_platform, user_id=user_id)
    )()


    #### BACK
    # result = (
    #     app.signature('get_papers_results_from_google_scholar', kwargs={query_terms : query_terms.list_of_keywords(), 'nb_pages' : nb_pages, 'query_params' : search_params})
    #     | app.signature('parse_documents', kwargs={'user_query' : prompt, 'search_index' : search_index, 'created_on' : created_on}) 
    #     | add_pdfs_to_es.s()
    #     | add_paragraph_to_es.s()
    #     | search_in_es_database.s(prompt=prompt)
    #     | get_paragraphs_content_for_answer.s()
    #     | app.signature('summerization_step', kwargs={'search_index' : search_index, 'created_on' : created_on})
    #     | add_search_to_db.s(search_index=search_index, created_on=created_on, research_type=search_type, search_platform=search_platform, user_id=user_id)
    # )()
    
    # get_papers_results_from_google_scholar = [
    #     retrieve_files.s(page=page)
    #     for page in retrieve_pages.s(query_terms=query_terms.list_of_keywords(), nb_pages=nb_pages)]
    
    # parse_documents_chain = chord(get_papers_results_from_google_scholar)(parsing_step.s(user_query = prompt, search_index=search_index, created_on = created_on))

    # get_documents = [
    #         (
    #             summerize_paragraph.s(category=category, paragraphs=paragraphs, search_index=search_index, created_on=created_on)
    #             | record_to_es.s()
    #             | retrieve_bibliographical_info.s()
    #         )
    #         for category, paragraphs in parse_documents_chain]
    
    #### BACK
    # get_documents = [summerization_step.s(category = category, paragraphs = paragraphs, search_index =search_index, created_on = created_on)
    #         for category, paragraphs in parse_documents_chain(query_terms=query_terms.list_of_keywords(), nb_pages = nb_pages, user_query=prompt, search_index = search_index, created_on = created_on, query_params = search_params).get(disable_sync_subtasks=False)]


    # get_documents = [app.signature('summerization_step', kwargs={'category' : category, 'paragraphs' : paragraphs, 'search_index' : search_index, 'created_on' : created_on})
    #         for category, paragraphs in parse_documents_chain(query_terms=query_terms.list_of_keywords(), nb_pages = nb_pages, user_query=prompt, search_index = search_index, created_on = created_on, query_params = search_params)]
    
    # resp = chord(get_documents)(
    #         add_search_to_db.s(search_index=search_index, created_on=created_on, research_type=search_type, search_platform=search_platform, user_id=user_id)
    #         )()
    
    # resp = (
    #     get_papers_results_from_google_scholar.s(query_terms=query_terms.list_of_keywords())
    #     | parse_documents.s(user_query = prompt, search_index=search_index, created_on=created_on)
    #     | add_pdfs_to_es.s()
    #     | add_paragraph_to_es.s()
    #     | search_in_es_database.s(prompt=prompt)
    #     | group( 
    #         (
    #             summerize_paragraph.s(category=category, paragraphs=paragraphs, search_index=search_index, created_on=created_on)
    #             | record_to_es.s()
    #             | retrieve_bibliographical_info.s()
    #         ).s()
    #         for category, paragraphs in get_paragraphs_content_for_answer.s())
    #     | add_search_to_db.s(search_index=search_index, created_on=created_on, research_type=search_type, search_platform=search_platform, user_id=user_id)
    #     )()

    return result