from pathlib import Path
from typing import Iterable, Any
from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4.element import Tag
import os
from copy import copy

import logging as lg

from search_app.core.services.webscraping.random_wait import wait_rand
from search_app.core.services.webscraping.drivers import ScrapingDriver

class DocumentRetrieverWithoutScraping():
    _pdf_folder = None

    def __init__(self, pdf_name : str) -> None:

        lg.debug("Récupération des données du document.")

        self.pdf_name = pdf_name

    def get_files(self) -> tuple[bytes, str] | None:
        lg.info("Récupération des fichiers disponnibles sur la page.")
        self.__get_pdf_file_if_exist()

        if self.pdf_file :
            self.ris_file = self.__get_bilio_info()
        
            if self.ris_file :
                return self.pdf_file, self.ris_file
            else :
                return None
        else :
                return None

    @property
    def pdf_folder(self) -> Path:
        if not self._pdf_folder:
            self._pdf_folder = Path(os.getenv('SCRAPPED_PDF_FOLDER'))
        return self._pdf_folder


    def __get_bilio_info(self, *args, **kwargs) -> dict:

        ris_file = self.pdf_folder.joinpath(self.pdf_name + '.ris')
            # ris_file_path = dwl_dir.joinpath(ris_file)
        with open(ris_file.absolute(), mode="r") as risfile:
            ris_content = risfile.read()

        if ris_content :
            return ris_content
        else :
            return None
    
    def __get_pdf_file_if_exist(self):
        
        lg.info("Tentative de récupération du fichier PDF.")

        pdf_file = self.pdf_folder.joinpath(self.pdf_name + ".pdf")

        with open(file=pdf_file.absolute(), mode='rb') as f_pdf:
            self.pdf_file = f_pdf.read()
        lg.debug('Le pdf a été chargé')

class DocumentRetriever():

    _scraping_driver = ScrapingDriver()

    def __init__(self, document_extract:Tag, webdriver_package : dict[str, Chrome | Path]) -> None:

        lg.debug("Récupération des données du document.")

        self._webdriver_package = webdriver_package
        self.document_extract = document_extract
        self.url = copy(self.driver.current_url)

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
        else :
                return None
        
    @property
    def driver(self) -> Chrome:
        return self._webdriver_package['driver']
    
    @driver.setter
    def driver(self, value):
        self._webdriver_package.update({
            'driver' : value
        })

    @property
    def temp_folder(self) -> Path:
        return self._webdriver_package['folder']
    
    @temp_folder.setter
    def temp_folder(self, value):
        self._webdriver_package.update({
            'folder' : value
        })

    def rebuild_driver(self):
        lg.debug('reconstruction du moteur de scraping')
        self.temp_folder.rmdir()
        new_driver_package  = self._scraping_driver.get_driver(url = self.url)
        self.driver         = new_driver_package['driver']
        self.temp_folder    = new_driver_package['folder']


    def __get_bilio_info(self, *args, **kwargs) -> dict:

        lg.debug("Récupération des données bibliographiques.")

        try :
            self.driver.find_element(by=By.XPATH, value=f"//div[@data-cid='{self.result_id}']//a[@aria-controls='gs_cit']").click()
            wait_rand(size="medium")
            WebDriverWait(self.driver, 20.0).until(lambda d: self.driver.find_element(by=By.XPATH, value="//a[@class='gs_citi' and contains(., 'RefMan')]"))
        except NoSuchElementException as e :
            retry = kwargs.get('retry', 3)
            if retry :
                lg.debug(f"Rééssaie de telechargement des données bibliographiques : tentative restantes {retry}")
                retry += -1
                self.rebuild_driver()
                self.__get_bilio_info(retry = retry)
            else:
                e_text = f"Les données bibliogrqphiques n'ont pu être récupérées"
                lg.error(e_text, exc_info=True)
                return None
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
            # ris_file_path = dwl_dir.joinpath(ris_file)
            with open(ris_file.absolute(), mode="r") as risfile:
                ris_content = risfile.read()
            os.remove(ris_file.absolute())

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
    
    def __download_pdf_file(self, *args, **kwargs):

        lg.info("Téléchargement du fichier PDF.")

        try :
            lg.debug("Suivi du lien de téléchargement.")
            self.driver.find_element(by=By.XPATH, value=f"//a[@data-clk-atid='{self.result_id}']").click()
            wait_rand(size='medium')
        except NoSuchElementException as e :
            retry = kwargs.get('retry', 3)
            if retry :
                lg.debug(f"Rééssaie de telechargement du fichier pdf : tentative restantes {retry}")
                retry += -1
                self.rebuild_driver()
                self.__download_pdf_file(retry = retry)
            else:
                e_text = "Erreur lors de la récupération du fichier PDF (ouverture du téléchargement)."
                lg.error(e_text, exc_info=True)
                return None
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
                # pdf_file = dwl_dir.joinpath(pdf_file)
                
                lg.debug("Lecture du fichier pdf.")
                with open(pdf_file.absolute(), mode="rb") as pdf_local_file:
                    pdf = pdf_local_file.read()
                lg.debug("Suppression du fichier pdf du dossier temporaire.")
                os.remove(pdf_file.absolute())
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