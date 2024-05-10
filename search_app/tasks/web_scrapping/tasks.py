from selenium.webdriver import Chrome, ChromeOptions
from bs4 import BeautifulSoup
from bs4.element import Tag
from pathlib import Path
import os
from celery import group
from typing import Any

from search_app.celery import app, lg
from search_app.core.services.webscraping.google_scholar_scraping import DocumentRetriever

@app.task
def get_google_scholar_search_url(query_terms : list[str], query_params : dict | None = None):

    lg.info("Création de l'adresse de recherche à partir des termes de la recherche.")
    scholar_base_url = "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5"

    search_url = f"{scholar_base_url}&q={'+'.join(query_terms)}&btnG=''"

    return search_url

@app.task
def get_webdriver_on_page(url : str):

    lg.info("Creation d'un moteur de scraping.")
    chrome_options = ChromeOptions()

    temp_folder = Path(os.getenv("TEMP_EMPL"))
    temp_folder.mkdir(parents=True, exist_ok=True)

    prefs = {
        "download.default_directory" : str(temp_folder),
        'download.prompt_for_download': False,
        'plugins.always_open_pdf_externally': True,
    }

    chrome_options.add_argument("--headless=new")
    chrome_options.add_experimental_option('prefs', prefs)

    driver = Chrome(
        options=chrome_options
        )
    driver.get(url=url)
    return driver

@app.task()
def get_research_pages_on_gs(nb_pages:int, driver :Chrome) -> list[Chrome]:

    lg.info("Récupération des résultats de la recherche sur la page web google scholar.")
    results_page = BeautifulSoup(driver.execute_script("return document.documentElement.outerHTML;"), 'html.parser')

    navigator = results_page.find("div", attrs={'id' : "gs_n", 'role' : "navigation"})
    pages = navigator.find_all("a", limit=nb_pages)
    base_url = "https://scholar.google.com"

    pages_urls = [base_url + page.get("href") for page in pages]

    pages_urls[:0] = driver.current_url

    return pages_urls


@app.task
def parse_page_for_gs(driver : Chrome) -> list[tuple[bytes, str]]:

    lg.info("Traitement des fichiers récupérés sur la page web google scholar.")
    results_page = BeautifulSoup(driver.execute_script("return document.documentElement.outerHTML;"), 'html.parser')
    results = results_page.find_all('div', attrs={'class' : "gs_r gs_or gs_scl"})
    
    files = list()
    for result in results :
            extractor = DocumentRetriever(document_extract=result, driver=driver)
            file = extractor.get_files()
            if file :
                 files.append(file)
    
    driver.quit()
    
    return files

def get_papers_results_from_google_scholar(query_terms : list[str], query_params : dict | None = None) -> list[tuple[bytes, str]] :

    lg.info("Scrapping de la recherche google scholar.")
    nb_pages = query_params.get("nb_pages", 1)
    
    result = (
         get_google_scholar_search_url.s(query_terms=query_terms, query_params=query_params)
         | get_webdriver_on_page.s()
         | group(
            (get_webdriver_on_page.s(page)
            | parse_page_for_gs.s())
            for page in get_research_pages_on_gs.s(nb_pages=nb_pages)
        )
    )

    return result