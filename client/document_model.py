from logging import getLogger
from asyncio import TaskGroup
from typing import Any
import textdistance
import nltk
import unidecode
from copy import copy
import rispy
import fitz
import string as str_cst
import re
import os
import aiofiles
from aiopath import AsyncPath
import uuid
from datetime import datetime

from client.elasticsearch_backend import ESHandler
from client.async_backend import ToThreadPool
from client.text_pretreatment import text_embedding

lg = getLogger("app")



class Document():

    def __init__(self, pdf_file, ris_file, database:str, created_on:datetime, user_query:str, search_index:str, *args, **kwargs) -> None:
        self.doc_type = "pdf"
        self.pdf_exists = None
        self.paragraphs = None
        self.es_pdf_id  = None

        self.database = database
        self.created_on = created_on
        self.user_query = user_query
        self.index = search_index
        self.pdf = pdf_file
        self.ris_file = ris_file


    @classmethod
    async def create_document(cls, pdf_file, ris_file, database:str, created_on:datetime, user_query:str, search_index:str, *args, **kwargs):

        lg.debug("Construction d'un nouveau document")

        instance = cls(pdf_file, ris_file, database, created_on, user_query, search_index, *args, **kwargs)

        instance.__es_api = await ESHandler().create_handler()
        

        lg.debug(f"Le docuement est crée.")

        async with TaskGroup() as tg:
            ref_parsing = tg.create_task(instance.__parse_bibref())
            pdf_parsing = tg.create_task(instance.__parse_pdf_file())



        if  ref_parsing and pdf_parsing:
            lg.info("Le document à été crée")
            return instance  
        
        else:
            lg.info("La creation du document à échoué (absence de fichier pdf ou de référence bibliographiques).")
            return None

    async def __parse_bibref(self):

        lg.debug("Enrichissement du document selon les données bilbiographiques")

        biblio = rispy.load(self.ris_file)
        if biblio :
            if isinstance(biblio, list) :
                biblio = biblio[0]

            self.type       = biblio.get("type_of_reference")
            self.title      = biblio.get("primary_title")
            self.authors    = biblio.get('first_authors')
            self.vol        = biblio.get('volume')
            self.j_name     = biblio.get('journal_name')
            self.nb         = biblio.get('number')
            self.pages      = "-".join([biblio.get('start_page', ""), biblio.get('end_page', "")])
            self.issn       = biblio.get('issn')
            self.pub_year   = biblio.get('publication_year')
            self.publisher  = biblio.get('publisher')

            lg.debug("Les données bibliographiques ont été récupérées.")
            return True

        else :
            lg.debug("Les données bibliographiques n'ont pu être parsées")
            return False

    async def __save_pdf_to_fs(self):

        self.file_name = str(uuid.uuid1()) + ".pdf"
        self.pdf_file_path = AsyncPath(os.getenv("PDF_FS_PATH")).joinpath(self.file_name)
        await self.pdf_file_path.mkdir()
        # self.pdf_file_path.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(self.pdf_file_path, mode="wb+") as file:
            await file.write(self.pdf)

        lg.debug("Le fichier PDF est enregistré dans le FS.")

    async def __parse_pdf_file(self):

        parsed_pdf = await PDFParser().parse(pdf_file=self.pdf_file)

        if parsed_pdf :
            self.paragraphs = parsed_pdf.paragraphs

            await self.__es_api.check_if_pdf_exists_in_db(document=self)

            if self.pdf_exists == False :
                await self.__save_pdf_to_fs()
                
            
            lg.debug("les données du PDF ont été récupérées.")
        else :
            lg.info("Le PDF n'a pu être parsé.")
            return False


    async def get_document_paragraphs(self):
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
            "created_on"        :   self.created_on,
            "user_query"        :   self.user_query
        }

        document = dict()

        for info in infos:
            if infos[info]:
                document.update({
                    info    :   infos[info]
                })
        
        for paragraph in self.paragraphs :
            document_copy = copy(document)
            p_text = paragraph.get("content", None)
            if p_text and not "embedding" in paragraph:
                paragraph.update({
                    "embedding" :   await text_embedding.embedded(p_text)
                })
            document_copy.update(paragraph)

            document_out = {
                "_index":   self.index,
                "doc":      document_copy,
            }

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
                "created_on"        :   self.created_on,
            }
            document = dict()

            for info in infos:
                if infos[info]:
                    document.update({
                        info    :   infos[info]
                    })


            out_document = {
                "_index":   "pdf_files",
                "doc":      document,
            }
            
            return out_document
        else :
            return None

    async def __call__(self, *args: Any, **kwds: Any) -> Any:
        if self.pdf_exists == 'False':
            yield self.get_pdf()

        async for paragraph in self.get_document_paragraphs() :
            yield paragraph

class PDFParser():
    __tversky = textdistance.Tversky(ks=(1, 0.5))
    __stopwords = set(nltk.corpus.stopwords.words('english'))
    __english_words = set(nltk.corpus.words.words())

    def __init__(self, pdf_file) -> None:
        self.__file = pdf_file

        self.__toc_titles = None
        self.__toc_titles_hierarchy = None
    
    @classmethod
    async def parse(cls, pdf_file):
        lg.info("Initialisation de l'outil de parsing du PDF")

        self = cls(pdf_file)

        try :
            self.__parsed_pdf = fitz.Document(stream=self.__file)
        except Exception as e :
            error = e
            breakpoint()

        await self.__parse_toc()

        await self.__parse_pdf()

        if self.paragraphs :
            return self
        
        else :
            return None

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