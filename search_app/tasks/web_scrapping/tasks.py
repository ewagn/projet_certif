from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from bs4.element import Tag
from pathlib import Path
import os
from celery import group, chord, chain
from typing import Any
import uuid
from celery.utils.log import get_task_logger
from logging import Logger

from search_app.celery_worker import app
from search_app.core.services.webscraping.google_scholar_scraping import DocumentRetriever

lg : Logger = get_task_logger(__name__)

@app.task
def get_google_scholar_search_url(query_terms : list[str], query_params : dict | None = None):

    lg.info("Création de l'adresse de recherche à partir des termes de la recherche.")
    scholar_base_url = "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5"

    search_url = f"{scholar_base_url}&q={'+'.join(query_terms)}&btnG=''"

    return search_url

@app.task
def get_webdriver_on_page(url : str):

    lg.info("Creation d'un moteur de scraping.")
    service = Service(executable_path='/usr/bin/chromedriver')
    chrome_options = ChromeOptions()

    # temp_folder = Path(os.getenv("TEMP_EMPL"))
    # temp_folder.mkdir(parents=True, exist_ok=True)
    temp_folder = Path('./temp_' + uuid.uuid4())
    temp_folder.mkdir(parents=True, exist_ok=True)

    prefs = {
        "download.default_directory" : str(temp_folder),
        'download.prompt_for_download': False,
        'plugins.always_open_pdf_externally': True,
    }

    chrome_options.add_argument("--headless=new")
    chrome_options.add_experimental_option('prefs', prefs)

    driver = Chrome(
        options=chrome_options,
        service=service
        )
    driver.get(url=url)
    return driver, temp_folder

@app.task()
def get_research_pages_on_gs(driver : Chrome, temp_folder : Path, nb_pages:int,) -> list[str]:

    lg.info("Récupération des résultats de la recherche sur la page web google scholar.")
    results_page = BeautifulSoup(driver.execute_script("return document.documentElement.outerHTML;"), 'html.parser')

    navigator = results_page.find("div", attrs={'id' : "gs_n", 'role' : "navigation"})
    pages = navigator.find_all("a", limit=nb_pages)
    base_url = "https://scholar.google.com"

    pages_urls = [base_url + page.get("href") for page in pages]

    pages_urls[:0] = driver.current_url

    return pages_urls


@app.task
def parse_page_for_gs(driver : Chrome, temp_folder : Path) -> list[tuple[bytes, str]]:

    lg.info("Traitement des fichiers récupérés sur la page web google scholar.")
    results_page = BeautifulSoup(driver.execute_script("return document.documentElement.outerHTML;"), 'html.parser')
    results = results_page.find_all('div', attrs={'class' : "gs_r gs_or gs_scl"})
    
    files = list()
    for result in results :
            extractor = DocumentRetriever(document_extract=result, driver=driver, temp_folder=temp_folder)
            file = extractor.get_files()
            if file :
                 files.append(file)
    
    driver.quit()
    os.remove(temp_folder)
    
    return files


@app.task(name='retrieve_pages')
def retrieve_pages(query_terms : list[str], nb_pages : int, query_params : dict | None = None):
    result = (
        chain(get_google_scholar_search_url.s(query_terms=query_terms, query_params=query_params) 
                        , get_webdriver_on_page.s() 
                        , get_research_pages_on_gs.s(nb_pages=nb_pages))
    )
    return result


@app.task(name='retrieve_files')
def retrieve_files(pages : list[str]) -> list[list[tuple[bytes, str]]]:

    pages_scraping_list = list()

    for page in pages :
         pages_scraping_list.append(chain(get_webdriver_on_page.s(page), parse_page_for_gs.s())())
     
    result = group(pages_scraping_list)().get()
    
    return result

@app.task(name='get_papers_results_from_google_scholar')
def get_papers_results_from_google_scholar(query_terms : list[str], nb_pages : int, query_params : dict | None = None) -> list[list[tuple[bytes, str]]] :
     
    result = (
        get_google_scholar_search_url.s(query_terms=query_terms, query_params=query_params) 
        | get_webdriver_on_page.s() 
        | get_research_pages_on_gs.s(nb_pages=nb_pages)
        | retrieve_files.s()
    )
    
    return result

# @app.task
# def get_papers_results_from_google_scholar(query_terms : list[str], query_params : dict | None = None) -> list[tuple[bytes, str]] :

#     lg.info("Scrapping de la recherche google scholar.")
#     nb_pages = query_params.get("nb_pages", 1)
    
#     retrieving_pages = get_google_scholar_search_url.s(query_terms=query_terms, query_params=query_params) | get_webdriver_on_page.s() | get_research_pages_on_gs.s(nb_pages=nb_pages)
    
    
#     get_papers_results_from_google_scholar = chord(
#             (get_webdriver_on_page.s(page)
#             | parse_page_for_gs.s())
#             for page in retrieving_pages.s()
#         )

#     # result = (
#     #      get_google_scholar_search_url.s(query_terms=query_terms, query_params=query_params)
#     #      | get_webdriver_on_page.s()
#     #      | chord(
#     #         (get_webdriver_on_page.s(page)
#     #         | parse_page_for_gs.s())
#     #         for page in get_research_pages_on_gs.s(nb_pages=nb_pages)
#     #     ).s()
#     # )

#     return result