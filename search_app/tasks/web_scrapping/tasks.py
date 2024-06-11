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
import random

from search_app.celery_worker import app
from celery.app import task
from search_app.core.services.webscraping.google_scholar_scraping import DocumentRetriever

lg : Logger = get_task_logger(__name__)



@app.task(name='get_google_scholar_search_url', queue="tasks.search")
def get_google_scholar_search_url(query_terms : list[str], query_params : dict | None = None):

    lg.info("Création de l'adresse de recherche à partir des termes de la recherche.")
    scholar_base_url = "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5"

    search_url = f"{scholar_base_url}&q={'+'.join(query_terms)}&btnG=''"

    return search_url

# @app.task(name="get_webdriver_on_page", queue="tasks.search")
# def get_webdriver_on_page(url : str):

#     AGENT_LIST = [
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
#     "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:24.0) Gecko/20100101 Firefox/24.0",
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/91.0.4472.114 Safari/537.36",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0"
#     ]

#     lg.info("Creation d'un moteur de scraping.")
#     service = Service(executable_path='/usr/bin/chromedriver')
#     chrome_options = ChromeOptions()

#     # temp_folder = Path(os.getenv("TEMP_EMPL"))
#     # temp_folder.mkdir(parents=True, exist_ok=True)
#     temp_folder = Path('./temp_' + str(uuid.uuid4()))
#     temp_folder.mkdir(parents=True, exist_ok=True)

#     prefs = {
#         "download.default_directory" : str(temp_folder.absolute()),
#         'download.prompt_for_download': False,
#         'plugins.always_open_pdf_externally': True,
#     }

#     chrome_options.add_argument("--headless=new")
#     # chrome_options.add_argument('--disable-blink-features')
#     chrome_options.add_argument("--incognito")
#     chrome_options.add_argument("--disable-blink-features=AutomationControlled")
#     chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     chrome_options.add_experimental_option('useAutomationExtension', False)

#     chrome_options.add_experimental_option('prefs', prefs)

    

#     driver = Chrome(
#         options=chrome_options,
#         service=service
#         )
#     driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
#     driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": random.choice(AGENT_LIST)})
#     driver.get(url=url)
#     return driver, temp_folder

@app.task(name='get_research_pages_on_gs', queue="tasks.search", bind=True)
def get_research_pages_on_gs(self : task, url : str, nb_pages:int) -> list[str]:

    webdriver_package = self.get_webdriver(url=url)

    lg.info("Récupération des résultats de la recherche sur la page web google scholar.")
    results_page = BeautifulSoup(webdriver_package["driver"].execute_script("return document.documentElement.outerHTML;"), 'html.parser')

    navigator = results_page.find("div", attrs={'id' : "gs_n", 'role' : "navigation"})
    pages = navigator.find_all("a", limit=nb_pages)
    base_url = "https://scholar.google.com"

    pages_urls = [base_url + page.get("href") for page in pages]

    pages_urls[:0] = [webdriver_package["driver"].current_url]

    webdriver_package["folder"].rmdir()
    webdriver_package["driver"].delete_all_cookies()
    webdriver_package["driver"].quit()

    return pages_urls


@app.task(name='parse_page_for_gs', queue="tasks.search", bind=True)
def parse_page_for_gs(self : task, url: str) -> list[tuple[bytes, str]]:
    webdriver_package = self.get_webdriver(url=url)

    lg.info("Traitement des fichiers récupérés sur la page web google scholar.")
    results_page = BeautifulSoup(webdriver_package["driver"].execute_script("return document.documentElement.outerHTML;"), 'html.parser')
    results = results_page.find_all('div', attrs={'class' : "gs_r gs_or gs_scl"})
    
    files = list()
    for result in results :
            extractor = DocumentRetriever(document_extract=result, webdriver_package=webdriver_package)
            file = extractor.get_files()
            if file :
                lg.debug('Ajout des fichiers à la liste des fichiers à traiter.') 
                files.append(file)

    webdriver_package["driver"].delete_all_cookies()
    webdriver_package["driver"].quit()
    webdriver_package["folder"].rmdir()
    
    return files


# @app.task(name='retrieve_pages', queue="tasks.search")
# def retrieve_pages(query_terms : list[str], nb_pages : int, query_params : dict | None = None):
#     result = (
#         chain(get_google_scholar_search_url.s(query_terms=query_terms, query_params=query_params) 
#                         , get_webdriver_on_page.s() 
#                         , get_research_pages_on_gs.s(nb_pages=nb_pages))
#     )()
#     return result

@app.task(name='get_result_files', queue="tasks.search")
def get_result_files(results_list = list[list[tuple[bytes, str]]]):
    results_out = list()
    for results in results_list :
        results_out.extend(results)

    return results_out


@app.task(name='retrieve_files', queue="tasks.search")
def retrieve_files(pages : list[str]) -> list[tuple[bytes, str]]:

    pages_scraping_list = list()

    for page in pages :
        pages_scraping_list.append(parse_page_for_gs.s(page))
     
    result = chord(pages_scraping_list)(get_result_files.s())
    
    return result

# @app.task(name='get_papers_results_from_google_scholar', queue="tasks.search")
# def get_papers_results_from_google_scholar(query_terms : list[str], nb_pages : int, query_params : dict | None = None) -> list[list[tuple[bytes, str]]] :
     
#     result = (
#         get_google_scholar_search_url.s(query_terms=query_terms, query_params=query_params) 
#         | get_webdriver_on_page.s() 
#         | get_research_pages_on_gs.s(nb_pages=nb_pages)
#         | retrieve_files.s()
#     )
    
#     return result

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