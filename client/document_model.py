from logging import getLogger
from asyncio import TaskGroup
from typing import Any
from bs4.element import Tag
import textdistance
import nltk
import unidecode
from copy import copy
# import requests
# from bs4 import BeautifulSoup
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
# from xvfbwrapper import Xvfb
import rispy
import fitz
import string as str_cst
import re
import os
from pathlib import Path
import uuid

from client.random_wait import wait_rand
from client.async_backend import ToThreadPool
from client.search_backend import es_search
from client.text_pretreatment import text_embedding

lg = getLogger(__name__)



class Document():

    # def __new__(cls, document_extract:Tag, driver, database:str) :
    #     lg.debug("Construction d'un nouveau document")
    #     document_retrieve = DocumentRetriever(document_extract, driver)
    #     if document_retrieve.pdf_file and document_retrieve.biblio_data :
    #         instance = super().__new__(cls)
    #         instance.database = database
    #         instance.__document_retrieve = document_retrieve
    #         lg.debug(f"Le docuement est crée.")
    #         return instance  
        
    #     else:
    #         lg.debug("La creation du document à échoué (absence de fichier pdf ou de référence bibliographiques).")
    #         return None

    def __init__(self) -> None:
        pass
        # lg.debug("Enrichissement du document selon les données bilbiographiques")
        
        # self.doc_type = "pdf"

        # self.pdf        = self.__document_retrieve.pdf_file
        # self.es_pdf_id  = None
        # self.type       = self.__document_retrieve.biblio_data.get("type_of_reference")
        # self.title      = self.__document_retrieve.biblio_data.get("primary_title")
        # self.authors    = self.__document_retrieve.biblio_data.get('first_authors')
        # self.vol        = self.__document_retrieve.biblio_data.get('volume')
        # self.j_name     = self.__document_retrieve.biblio_data.get('journal_name')
        # self.nb         = self.__document_retrieve.biblio_data.get('number')
        # self.pages      = "-".join([self.__document_retrieve.biblio_data.get('start_page', ""), self.__document_retrieve.biblio_data.get('end_page', "")])
        # self.issn       = self.__document_retrieve.biblio_data.get('issn')
        # self.pub_year   = self.__document_retrieve.biblio_data.get('publication_year')
        # self.publisher  = self.__document_retrieve.biblio_data.get('publisher')

        # self.file_name = str(uuid.uuid1()) + ".pdf"
        # self.pdf_file_path = None

        # parsed_pdf = PDFParser(pdf_file=self.__document_retrieve.pdf_file)
        # self.paragraphs = parsed_pdf.paragraphs

        # del self.__document_retrieve


    @classmethod
    async def create_document(cls, database:str, search, document_extract:Tag, driver):

        lg.debug("Construction d'un nouveau document")
        document_retrieve = DocumentRetriever(document_extract, driver)

        if document_retrieve.pdf_file and document_retrieve.biblio_data :
            instance = cls()
            instance.database = database
            instance.created_on = search.created_on
            instance.user_query = search.user_query

            instance.__document_retrieve = document_retrieve
            lg.debug(f"Le docuement est crée.")

            async with TaskGroup() as tg :
                tg.create_task(instance.__populate_document())
                tg.create_task(instance.__parse_pdf_file())

            # await instance.__populate_document()

            # await instance.__parse_pdf_file()

            # parsed_pdf = PDFParser() (pdf_file=instance.__document_retrieve.pdf_file)
            # instance.paragraphs = parsed_pdf.paragraphs

            del instance.__document_retrieve
            return instance  
        
        else:
            lg.debug("La creation du document à échoué (absence de fichier pdf ou de référence bibliographiques).")
            return None


    async def __populate_document(self):

        lg.debug("Enrichissement du document selon les données bilbiographiques")
            
        self.doc_type = "pdf"

        self.pdf        = self.__document_retrieve.pdf_file
        self.es_pdf_id  = None
        self.type       = self.__document_retrieve.biblio_data.get("type_of_reference")
        self.title      = self.__document_retrieve.biblio_data.get("primary_title")
        self.authors    = self.__document_retrieve.biblio_data.get('first_authors')
        self.vol        = self.__document_retrieve.biblio_data.get('volume')
        self.j_name     = self.__document_retrieve.biblio_data.get('journal_name')
        self.nb         = self.__document_retrieve.biblio_data.get('number')
        self.pages      = "-".join([self.__document_retrieve.biblio_data.get('start_page', ""), self.__document_retrieve.biblio_data.get('end_page', "")])
        self.issn       = self.__document_retrieve.biblio_data.get('issn')
        self.pub_year   = self.__document_retrieve.biblio_data.get('publication_year')
        self.publisher  = self.__document_retrieve.biblio_data.get('publisher')

        # task : asyncio.Task = asyncio.create_task(self.__parse_pdf_file())
        # documents_parsing.add(task)
        # task.add_done_callback(documents_parsing.discard)

        self.file_name = str(uuid.uuid1()) + ".pdf"
        self.pdf_file_path = None

    @ToThreadPool
    async def __parse_pdf_file(self):

        parsed_pdf = await PDFParser().parse(pdf_file=self.__document_retrieve.pdf_file)
        self.paragraphs = parsed_pdf.paragraphs

    async def __get_document_paragraphs(self):
        infos = {
            "database"          :   self.database,
            "es_pdf_id"         :   self.es_pdf_id,
            "type"              :   self.type,
            "title"             :   self.title,
            "authors"           :   self.authors,
            "volume"            :   self.vol,
            "journal_name"      :   self.j_name,
            "number"            :   self.nb,
            "pages"             :   self.pages,
            'issn'              :   self.issn,
            "publication_year"  :   self.pub_year,
            "publisher"         :   self.publisher,
        }

        document = dict()

        for info in infos:
            if infos[info]:
                document.update({
                    info    :   infos[info]
                })
        
        for paragraph in self.paragraphs :
            document_out = copy(document)
            p_text = paragraph.get("content", None)
            if p_text:
                paragraph.update({
                    "embedding" :   await text_embedding.embedded(p_text)
                })
            document_out.update(paragraph)
            yield document_out
    
    async def get_pdf(self) -> dict | None :
        if self.pdf:
            infos = {
                "database"          :   self.database,
                "type"              :   self.type,
                "title"             :   self.title,
                "authors"           :   self.authors,
                "volume"            :   self.vol,
                "journal_name"      :   self.j_name,
                "number"            :   self.nb,
                "pages"             :   self.pages,
                'issn'              :   self.issn,
                "publication_year"  :   self.pub_year,
                "publisher"         :   self.publisher,
                'pdf_file_path'     :   self.pdf_file_path,
            }
            document = dict()

            for info in infos:
                if infos[info]:
                    document.update({
                        info    :   infos[info]
                    })
            
            return document
        else :
            return None

    def __call__(self, *args: Any, **kwds: Any) -> Any:

        return self.__get_document_paragraphs()


class DocumentRetriever():
    def __init__(self, document_extract:Tag, driver) -> None:

        lg.debug("Récupération des données du document.")

        self.driver = driver

        self.result_id = document_extract.attrs['data-cid']

        self.__get_pdf_file_if_exist(document_extract = document_extract)

        if self.pdf_file :
            self.biblio_data = self.__get_bilio_info()


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
        # ris_citation = BeautifulSoup(ris_citation.get_attribute('outerHTML'), 'html.parser')
        # ris_file_url = ris_citation.find("a", string="RefMan").get('href')
        # ris_citation.find("a", string="RefMan").click()
        if not ris_citation:
            lg.warning('Le document ne possède par de références bibliographiques téléchargeables')
            self.driver.find_element(by=By.XPATH, value=f"//div[@class='gs_md_d gs_md_ds gs_ttzi gs_vis']//a[@id='gs_cit-x']").click()
            return None
        ris_citation.click()
        wait_rand(size="small")

        # try:
        dwl_dir = "/Users/etiennewagner/Documents/Reconversion/Licence IA/2eme_annee/projet_certif/client/temp"
        files_in_temp = [f for f in os.listdir(dwl_dir) if os.path.isfile(os.path.join(dwl_dir, f))]
        if files_in_temp :
            ris_file = files_in_temp[0]
            ris_file = os.path.join(dwl_dir, ris_file)
            biblio = rispy.load(Path(ris_file))
            os.remove(os.path.join(dwl_dir, ris_file))


            # resp = requests.get(url=ris_file_url)
        # except:
        else :
            e_text = f"Erreur de récupération des références bibliographiques, le téléchargement n'a pas eu lieu."
            lg.error(e_text)
            raise ConnectionError(e_text)
        self.driver.find_element(by=By.XPATH, value=f"//div[@class='gs_md_d gs_md_ds gs_ttzi gs_vis']//a[@id='gs_cit-x']").click()
        wait_rand(size="small")
        
        # if 400 <= resp.status_code and resp.status_code < 500:
        #     resp = requests.get(url=ris_file_url)

        
        # if 200 <= resp.status_code < 300:
        #     biblio = rispy.loads(resp.content.decode(encoding='utf-8'))
        #     wait_rand()
        #     self.driver.find_element(by=By.XPATH, value=f"//div[@class='gs_md_d gs_md_ds gs_ttzi gs_vis']//a[@id='gs_cit-x']").click()
        #     wait_rand()

        # else :
        #     e_text = f"Erreur lors de la récupération des données bibliographiques: code {resp.status_code}, reason {resp.reason}"
        #     breakpoint()
        #     raise RuntimeError(e_text)
        
        if biblio :
            if isinstance(biblio, list) :
                biblio = biblio[0]
                
            return biblio
        else :
            return None
    
    # def __download_pdf_file_alternate(self, url):
    #     wd = create_webdriver(file_type_to_dowload="pdf")
    #     wd.get(url=url)
    #     wd.close()
    #     dwl_dir = "/Users/etiennewagner/Documents/Reconversion/Licence IA/2eme_annee/projet_certif/client/temp"
    #     pdf_file = [f for f in os.listdir(dwl_dir) if os.path.isfile(os.path.join(dwl_dir, f))][0]
    #     if pdf_file :
    #         pdf_file = os.path.join(dwl_dir, pdf_file)
    #         with open(Path(pdf_file), mode="rb") as pdf_local_file:
    #             pdf = pdf_local_file.read()
    #         os.remove(os.path.join(dwl_dir, pdf_file))
    #         if pdf :
    #             return pdf
    #         else:
    #             return None

        ### Old Code
        # resp = requests.get(url=wd.current_url)
        # wd.close()
        # wd.
        # if 200 <= resp.status_code and resp.status_code < 300:
        #     return resp.content
        # elif resp.status_code == 404:
        #     return None
        # else :
        #     e_text = f"Erreur lors du téléchargement du fichier pdf avec le méthode alternative : code {resp.status_code}, reason {resp.reason}"
        #     breakpoint()
        #     raise RuntimeError(e_text)

    
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
        dwl_dir = "/Users/etiennewagner/Documents/Reconversion/Licence IA/2eme_annee/projet_certif/client/temp"
        files_in_temp = [f for f in os.listdir(dwl_dir) if os.path.isfile(os.path.join(dwl_dir, f))]
        if files_in_temp :
            pdf_file = files_in_temp[0]
            if pdf_file :
                pdf_file = os.path.join(dwl_dir, pdf_file)
                
                lg.debug("Lecture du fichier pdf.")
                with open(Path(pdf_file), mode="rb") as pdf_local_file:
                    pdf = pdf_local_file.read()
                lg.debug("Suppression du fichier pdf du dossier temporaire.")
                os.remove(os.path.join(dwl_dir, pdf_file))
                if pdf :
                    return pdf
                else:
                    return None
        else :
            return None

        ### Old code

        # try :
        #     resp = requests.get(url=url)
        # except Exception as e:
        #     e_text = f"Erreur lors du téléchargement du fichier pdf"
        #     raise RuntimeError(e_text) from e
        
        # if 200 <= resp.status_code and resp.status_code < 300:
        #     return resp.content
        # elif 400 <= resp.status_code and resp.status_code < 500 :
        #     return self.__download_pdf_file_alternate(url=url)
        # else:
        #     breakpoint()
        #     e_text = f"Erreur lors du téléchargement du fichier pdf : code {resp.status_code}, reason {resp.reason}"
        #     raise RuntimeError(e_text)
    
    def __get_pdf_file_if_exist(self, document_extract:Tag):
        
        lg.info("Tentative de récupération du fichier PDF.")

        is_pdf = None

        lg.debug("Repérage du lien de téléchargement.")
        pdf_block = document_extract.find("a", attrs={'data-clk-atid' : self.result_id})
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


        ### Old Code
        # pdf_url = None
        # pdf_block = document_extract.find("a", attrs={'data-clk-atid' : self.result_id})

        # if pdf_block :
        #     pdf_tag = pdf_block.find("span", attrs={'class' : 'gs_ctg2'})
        #     if pdf_tag :
        #         pdf_tag = pdf_tag.text
        #         if pdf_tag :
        #             if 'pdf' in pdf_tag.lower() :
        #                 pdf_url = pdf_block.get('href')

        # if pdf_url :
        #     self.pdf_file = self.__download_pdf_file(url=pdf_url)
        # else :
        #     self.pdf_file = None

class PDFParser():
    __tversky = textdistance.Tversky(ks=(1, 0.5))
    __stopwords = set(nltk.corpus.stopwords.words('english'))
    __english_words = set(nltk.corpus.words.words())

    def __init__(self) -> None:
        pass
        
        # lg.info("Initialisation de l'outil de parsing du PDF")

        # self.__file = pdf_file

        # self.__toc_titles = None
        # self.__toc_titles_hierarchy = None

        # try :
        #     self.__parsed_pdf = fitz.Document(stream=self.__file)
        # except Exception as e :
        #     error = e
        #     breakpoint()

        # self.__parse_toc()

        # self.__parse_pdf()
    
    @classmethod
    async def parse(cls, pdf_file):
        lg.info("Initialisation de l'outil de parsing du PDF")

        self = cls()

        self.__file = pdf_file

        self.__toc_titles = None
        self.__toc_titles_hierarchy = None

        try :
            self.__parsed_pdf = fitz.Document(stream=self.__file)
        except Exception as e :
            error = e
            breakpoint()

        await self.__parse_toc()

        await self.__parse_pdf()

    async def __parse_toc(self):

        lg.info("Récupération de la table des matières du PDF")

        lg.debug("Vérification de l'existance de la table des matières.")
        toc = self.__parsed_pdf.get_toc()
        
        if toc :
            lg.debug("La table des matières existe.")
            self.__toc_titles = set()
            self.__toc_titles_hierarchy = dict()

            lg.debug("Récupération des titres dans la tables de matières.")
            for title in toc:
                self.__toc_titles.add(title[1].strip().lower())
                self.__toc_titles_hierarchy.update({
                        tuple(await self.__preprocessing_text(title[1])):   {
                        'title'     :  title[1].strip().lower(),
                        'hierarchy' :   title[0]}
                })
    
    async def __preprocessing_text(self, string:str) -> list :

        lg.info("Préprocessing du texte")

        out_text = unidecode.unidecode(string)
        out_text = ''.join([c for c in out_text if c not in str_cst.punctuation])
        out_text = ''.join([i for i in out_text if not i.isdigit()])

        out_words = out_text.strip().lower().split()
        out_words = [word for word in out_words if len(word) > 3]
        out_words = [word for word in out_words if word not in self.__stopwords]

        return out_words

    
    async def __compare_to_titles(self, string:str):

        lg.info("Correspondance des titres récupérés dans le corps du PDF avec la table des matières.")

        string_to_compare = self.__preprocessing_text(string)

        lg.debug("Compraisons sérielle des titres avec la méthode tversky.")
        comparison = dict()
        for title in self.__toc_titles:
            score = self.__tversky(title, string_to_compare)
            if score > 0.8 :
                comparison.update({score :   title})
        
        lg.debug("Sélection du titre le plus probalble selon le score de proximité.")
        if comparison :
            max_score = max(comparison)
            return (self.__toc_titles_hierarchy[comparison[max_score]]['hierarchy'], self.__toc_titles_hierarchy[comparison[max_score]]['title'])
        else:
            return None

    async def __parse_pdf(self):

        lg.info("Parsing du fichier PDF.")

        paragraphs = list()
        part_tite = ""
        sub_title = ""

        lg.debug("Itération sur les pages et paragraphes du PDF.")
        for p_nb, page in enumerate(self.__parsed_pdf, start=1):
            for p in page.get_text('blocks'):

                title = True

                lg.debug("Segmentation du texte en paragraphes.")
                p_text : list = p[4].split('\n')

                lg.debug("Tentative d'indentificiation des titres.")
                text :list = p_text.copy()

                text_out = list()

                while self.__toc_titles and title and text :
                    title = await self.__compare_to_titles(text[0])
                    if title :
                        hierarchy, title_string = title

                        if hierarchy == 1 :
                            part_tite = title_string
                        else :
                            sub_title = title_string
                        
                        text.pop(0)

                    else :
                        text_out.append(text.pop(0))


                lg.debug("Création des paragraphs ")
                if text_out :
                    
                    lg.debug("Fusion du texte.")
                    text_out = " ".join(text_out)

                    lg.debug("Calcul de la longueur de la protion de texte traitée.")
                    paragraph_length = re.subn(pattern=r"[^\w\s]|[\d]", repl='', string=text_out)[0]
                    paragraph_length = [word for word in nltk.word_tokenize(text_out) if word.lower() in self.__english_words]

                    lg.debug("Ajout du paragraphe aux paragraphes")
                    if len(paragraph_length) >= 5 :
                        if paragraphs and paragraphs[-1][-1][-1] != "." :
                            paragraphs[-1][-1] = paragraphs[-1][-1] + " " + text_out.strip()
                        else :
                            paragraphs.append([p_nb, part_tite, sub_title, text_out.strip()])
        
        lg.debug("Formatage des paragraphes récupérés.")
        if paragraphs :
            paragraphs_out = list()
            for paragraph in paragraphs :
                paragraph_out = dict()
                page_nb, part_tite, sub_title, p_text = paragraph
                paragraph_out.update({
                    'pdf_page'  :   page_nb,
                    'content'   :   p_text,
                })

                if part_tite :
                    paragraph_out.update({
                    'part_title'   :   part_tite,
                })
                if sub_title :
                    paragraph_out.update({
                    'sub_title'   :   sub_title,
                })
                paragraphs_out.append(paragraph_out)

        self.paragraphs = paragraphs_out