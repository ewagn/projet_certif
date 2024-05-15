from pathlib import Path
from typing import Iterable, Any
from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from bs4.element import Tag
import os

import logging as lg

from search_app.core.services.webscraping.random_wait import wait_rand

class DocumentRetriever():
    def __init__(self, document_extract:Tag, driver:Chrome, temp_folder : Path) -> None:

        lg.debug("Récupération des données du document.")

        self.temp_folder = temp_folder

        self.driver = driver
        self.document_extract = document_extract

        self.result_id = document_extract.attrs['data-cid']

    def get_files(self) -> tuple[bytes, str] | None:
        lg.info("Récupération des fichiers disponnibles sur la page.")
        self.__get_pdf_file_if_exist()

        if self.pdf_file :
            self.ris_file = self.__get_bilio_info()
        
        if self.ris_file :
            # return {"pdf_file" : self.pdf_file, "ris_file" : self.ris_file}
            return self.pdf_file, self.ris_file
        else :
            return None

    def __get_bilio_info(self) -> dict:

        lg.debug("Récupération des données bibliographiques.")

        try :
            self.driver.find_element(by=By.XPATH, value=f"//div[@data-cid='{self.result_id}']//a[@aria-controls='gs_cit']").click()
            wait_rand(size="small")
            WebDriverWait(self.driver, 20.0).until(lambda d: self.driver.find_element(by=By.XPATH, value="//a[@class='gs_citi' and contains(., 'RefMan')]"))
        except Exception as e:
            e_text = f"Les données bibliogrqphiques n'ont pu être récupérées"
            lg.error(e_text, exc_info=True)
            return None

        ris_citation = self.driver.find_element(by=By.XPATH, value="//a[@class='gs_citi' and contains(., 'RefMan')]")

        if not ris_citation:
            lg.warning('Le document ne possède par de références bibliographiques téléchargeables')
            self.driver.find_element(by=By.XPATH, value=f"//div[@class='gs_md_d gs_md_ds gs_ttzi gs_vis']//a[@id='gs_cit-x']").click()
            return None
        ris_citation.click()
        wait_rand(size="small")

        dwl_dir = self.temp_folder
        files_in_temp = [f for f in dwl_dir.iterdir() if f.is_file()]
        if files_in_temp :
            ris_file = files_in_temp[0]
            ris_file_path = dwl_dir.joinpath(ris_file)
            with open(ris_file_path, mode="r") as risfile:
                ris_content = risfile.read()
            os.remove(ris_file_path)

        else :
            e_text = f"Erreur de récupération des références bibliographiques, le téléchargement n'a pas eu lieu."
            lg.error(e_text)
            raise ConnectionError(e_text)
        self.driver.find_element(by=By.XPATH, value=f"//div[@class='gs_md_d gs_md_ds gs_ttzi gs_vis']//a[@id='gs_cit-x']").click()
        wait_rand(size="small")
        
        if ris_content :
            return ris_content
        else :
            return None
    
    def __download_pdf_file(self):

        lg.info("Téléchargement du fichier PDF.")

        try :
            lg.debug("Suivi du lien de téléchargement.")
            self.driver.find_element(by=By.XPATH, value=f"//a[@data-clk-atid='{self.result_id}']").click()
            wait_rand()
        except Exception as e :
            e_text = "Erreur lors de la récupération du fichier PDF (ouverture du téléchargement)."
            lg.error(e_text, exc_info=True)
            return None

        lg.debug("Recupération du fichier dans le dossier temporaire.")
        dwl_dir = self.temp_folder
        files_in_temp = [f for f in  dwl_dir.iterdir() if f.is_file()]
        if files_in_temp :
            pdf_file = files_in_temp[0]
            if pdf_file :
                pdf_file = dwl_dir.joinpath(pdf_file)
                
                lg.debug("Lecture du fichier pdf.")
                with open(pdf_file, mode="rb") as pdf_local_file:
                    pdf = pdf_local_file.read()
                lg.debug("Suppression du fichier pdf du dossier temporaire.")
                os.remove(pdf_file)
                if pdf :
                    return pdf
                else:
                    return None
        else :
            return None
    
    def __get_pdf_file_if_exist(self):
        
        lg.info("Tentative de récupération du fichier PDF.")

        is_pdf = None

        lg.debug("Repérage du lien de téléchargement.")
        pdf_block = self.document_extract.find("a", attrs={'data-clk-atid' : self.result_id})
        if pdf_block :
            pdf_tag = pdf_block.find("span", attrs={'class' : 'gs_ctg2'})
            if pdf_tag :
                pdf_tag = pdf_tag.text
                if pdf_tag :
                    if 'pdf' in pdf_tag.lower() :
                        is_pdf = True

        if is_pdf :
            self.pdf_file = self.__download_pdf_file()
        else :
            lg.debug("Le lien de téléchagrement PDF est absent")
            self.pdf_file = None


# class ScholarHandler():
    
#     def __init__(self, database:str, created_on:datetime, user_query:str, search_index:str, query_terms:Iterable, nb_pages:int, *args, **kwargs) -> None:
#         lg.info("Création du moteur du scrapper google scholar.")

#         self.database = database
#         self.created_on = created_on
#         self.user_query = user_query
#         self.search_index = search_index
#         self.query_terms = query_terms
#         self.nb_pages = nb_pages

#         # self.search_params = search
#         self.documents = list()

#         self.scholar_base_url = "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5"
    
#     def __enter__(self):

#         self.__vdisplay = Xvfb()
#         self.__vdisplay.start()

#         return self
    
#     def __axit__(self, *args, **kwargs):

#         self.__vdisplay.stop()

#     def __get_research_pages_url(self, results_page:Tag):

#         navigator = results_page.find("div", attrs={'id' : "gs_n", 'role' : "navigation"})
#         try :
#             pages = navigator.find_all("a", limit=self.nb_pages)
#         except Exception as e :
#             error = e
#             breakpoint()

#         base_url = "https://scholar.google.com"

#         return [ base_url + page.get("href") for page in pages]

#     def __get_result_page_files(self, url: str | None, driver: Chrome | None):
        
#         if driver:
#             driver = driver

#         elif not driver and url :
#             driver  = create_webdriver()
#             driver.get(url=url)

#         else :
#             e_text = "Il est nécéssaire d'avoir l'adresse de la page ou un navigateur ouvert sur cette pahge (driver)."
#             lg.error(e_text)
#             raise ValueError(e_text)

#         results_page = BeautifulSoup(self.driver.execute_script("return document.documentElement.outerHTML;"), 'html.parser')
#         results = results_page.find_all('div', attrs={'class' : "gs_r gs_or gs_scl"})

#         for result in results :

#             extractor = DocumentRetriever(document_extract=result, driver=driver)

#             yield from extractor.get_files()

#         driver.quit()
#         driver = None

#     async def __parse_page(self, url: Optional[str] | None, driver: Optional[Chrome] | None):

#         async with TaskGroup() as tg :
#             async for files in  self.__get_result_page_files(url, driver):
#                 if files :
#                     self.documents.append(tg.create_task(Document().create_document(database="google scholar", created_on=self.created_on, user_query=self.user_query, search_index= self.search_index, **files)))


#     def __get_documents_from_research(self):

#         self.search_url = f"{self.scholar_base_url}&q={'+'.join(self.query_terms)}&btnG=''"
#         driver = create_webdriver()
#         driver.get(url = self.search_url)
#         results_page = BeautifulSoup(self.driver.execute_script("return document.documentElement.outerHTML;"), 'html.parser')
        
#         if self.nb_pages :
#             self.pages = self.__get_research_pages_url(results_page = results_page)
#         else :
#             self.pages = None

#         with TaskGroup() as tg :

#             tg.create_task(self.__parse_page(driver=driver))

#             if self.pages :
#                 for page in self.pages :
#                     tg.create_task(self.__parse_page(url=page))
    
#     def search(self):
        
#         if not isinstance(self.query_terms, Iterable) :
#             e_text = "Le paramètre query_terms doit être un iterable (liste, tuple, set ...) et non une chaine de caractère"
#             raise ValueError(e_text)

#         if not isinstance(self.nb_pages, int) or self.nb_pages < 0 :
#             e_text = f"Le paramètre nb_pages doit être un entier suppérieur à 0 : valeur entrée {self.nb_pages:s}"
#             raise ValueError(e_text)

#         self.__get_documents_from_research()

#     def get_documents(self):
#         if self.documents == None:
#             lg.warning("La recherche n'a pas été conduite ou n'a rapporté aucun documents.")
#             return None
#         else :
#             for document in self.documents :
#                 for record in document():
#                     yield record