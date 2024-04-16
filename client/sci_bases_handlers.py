from logging import getLogger
from asyncio import TaskGroup, gather
from typing import Iterable, Optional
from selenium.webdriver import Chrome
from bs4 import BeautifulSoup
from xvfbwrapper import Xvfb

from client.web_scrapping_backend import create_webdriver
from client.document_model import Document
from client.random_wait import wait_rand

from client.async_backend import ToThreadPool, AsyncCode

lg = getLogger(__name__)

class ResearchPage():
    def __init__(self) -> None:
        pass
         
    @classmethod
    async def parse_result_page(cls, search,  url: Optional[str] | None, driver: Optional[Chrome] | None):

        if not url and not driver :
            e_text = "Il est nécéssaire d'avoir l'adresse de la page ou un navigateur ouvert sur cette pahge (driver)."
            lg.error(e_text)
            raise ValueError(e_text)
        
        self = cls()

        self.search = search

        if not driver :
            self.driver  = await create_webdriver()
            self.driver.get(url=url)
        else:
            self.driver = driver

        self.results_page = BeautifulSoup(self.driver.execute_script("return document.documentElement.outerHTML;"), 'html.parser')

        self.documents = list()
        await self.__get_documents_from_current_page()
        self.driver.quit()
        self.driver = None

        return self

    
    async def __get_page_results(self):

        return self.results_page.find_all('div', attrs={'class' : "gs_r gs_or gs_scl"})
    
    async def __get_documents_from_current_page(self):

        results = await self.__get_page_results()


        if results :
            documents = list()

            # for result in results :
            #     documents.append(Document(document_extract=result, driver=self.driver, database="google scholar", documents_parsing=documents_parsing_tasks))
            async with TaskGroup() as tg :
                for result in results :
                    documents.append(tg.create_task(Document().create_document(database="google scholar", document_extract=result, driver=self.driver)))
            
            self.documents = [document for document in documents if document]





class ScholarHandler():
    
    def __init__(self, search) -> None:
        lg.info("Création du moteur du scrapper google scholar.")
        self.search_params = search

        self.scholar_base_url = "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5"
    
    async def __aenter__(self):

        self.__vdisplay = Xvfb()
        self.__vdisplay.start()

        self.driver = await create_webdriver()

        return self
    
    async def __aexit__(self, *args, **kwargs):
        if self.driver :
            self.driver.quit()
        self.__vdisplay.stop()

    def __place_on_page(self, url:str):

        if not isinstance(url, str):
            e_text = "L'URL de la page doit être une string."
            raise ValueError(e_text)
        try :
            self.driver.get(url = url)
            wait_rand()
        except Exception as e :
            error = e
            breakpoint()
            
        self.results_page = BeautifulSoup(self.driver.execute_script("return document.documentElement.outerHTML;"), 'html.parser')
        # self.results_page = BeautifulSoup(self.driver.page_source, 'html.parser')

    def __get_research_pages_url(self, nb_pages_ret):

        navigator = self.results_page.find("div", attrs={'id' : "gs_n", 'role' : "navigation"})
        try :
            pages = navigator.find_all("a", limit=nb_pages_ret)
        except Exception as e :
            error = e
            breakpoint()

        base_url = "https://scholar.google.com"

        return [ base_url + page.get("href") for page in pages]
    
    # def __get_page_results(self):

    #     return self.results_page.find_all('div', attrs={'class' : "gs_r gs_or gs_scl"})
    
    # def __get_documents_from_current_page(self):
        
    #     results = self.__get_page_results()

    #     documents = list()

    #     if results :
    #         for result in results :
    #             documents.append(Document(document_extract=result, driver=self.driver, database="google scholar"))
            
    #         return [document for document in documents if document]


    async def __get_documents_from_research(self, query:list, nb_pages_ret):

        self.search_url = f"{self.scholar_base_url}&q={'+'.join(query)}&btnG=''"
        self.__place_on_page(url=self.search_url)

        
        if nb_pages_ret :
            self.pages = self.__get_research_pages_url(nb_pages_ret = nb_pages_ret)
        else :
            self.pages = None

        pages_results = list()

        async with TaskGroup() as tg :
            pages_results.append(tg.create_task(ResearchPage().parse_result_page(url=self.search_url, driver=self.driver)))
            if self.pages :
                for page_url in self.pages:
                    pages_results.append(tg.create_task(ResearchPage().parse_result_page(url=page_url)))


        documents = list()

        if pages_results :
            for page in pages_results :
                if page.documents :
                    documents.extend(page.documents)

        ## Old Code

        # page_documents = self.__get_documents_from_current_page()
        # if page_documents :
        #     documents.extend(page_documents)

        # if self.__pages :
        #     for result in self.__pages:
        #         self.__place_on_page(result)
        #         page_documents = self.__get_documents_from_current_page()
        #         if page_documents :
        #             documents.extend(page_documents)
        
        self.parsed_pdf_documents = documents
    
    async def search(self, query_terms:Iterable, nb_pages:int):
        
        if not isinstance(query_terms, Iterable) and not isinstance(query_terms, str) :
            e_text = "Le paramètre query_terms doit être un iterable (liste, tuple, set ...) et non une chaine de caractère"
            raise ValueError(e_text)

        if not isinstance(nb_pages, int) and nb_pages > 0 :
            e_text = f"Le paramètre nb_pages doit être un entier suppérieur à 0 : valeur entrée {str(nb_pages)}"
            raise ValueError(e_text)

        await self.__get_documents_from_research(query=query_terms, nb_pages_ret=nb_pages)