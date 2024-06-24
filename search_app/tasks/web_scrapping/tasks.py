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
from search_app.core.services.webscraping.google_scholar_scraping import DocumentRetriever, DocumentRetrieverWithoutScraping

lg : Logger = get_task_logger(__name__)



@app.task(name='get_google_scholar_search_url', queue="tasks.search")
def get_google_scholar_search_url(query_terms : list[str], query_params : dict | None = None):

    lg.info("Création de l'adresse de recherche à partir des termes de la recherche.")
    scholar_base_url = "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5"

    search_url = f"{scholar_base_url}&q={'+'.join(query_terms)}&btnG=''"

    return search_url

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
            files_to_parse = extractor.get_files()
            if files_to_parse :
                lg.debug('Ajout des fichiers à la liste des fichiers à traiter.') 
                files.append(files_to_parse)

    webdriver_package["driver"].delete_all_cookies()
    webdriver_package["driver"].quit()
    webdriver_package["folder"].rmdir()
    
    return files

@app.task(name='get_result_files', queue="tasks.search")
def get_result_files(results_list = list[list[tuple[bytes, str]]]):
    results_out = list()
    for results in results_list :
        results_out.extend(results)

    return results_out


@app.task(name='retrieve_files', queue="tasks.search")
def retrieve_files(
    # pages : list[str]
    ) -> list[tuple[bytes, str]]:

    # pages_scraping_list = list()

    # for page in pages :
    #     pages_scraping_list.append(parse_page_for_gs.s(page))
     
    # result = chord(pages_scraping_list)(get_result_files.s())

    pdf_folder = Path(os.getenv('SCRAPPED_PDF_FOLDER'))

    pdf_files = [pdf.name.split('.')[-2] for pdf in pdf_folder.iterdir() if pdf.is_file() and  pdf.name.split('.')[-1] == 'pdf']

    result = list()
    for pdf_name in pdf_files :
        extractor = DocumentRetrieverWithoutScraping(pdf_name = pdf_name)
        files_to_parser = extractor.get_files()
        if files_to_parser :
            lg.debug(f'Ajout du fichier {pdf_name}.pdf à la liste des fichiers à traiter.') 
            result.append(files_to_parser)
    
    return result