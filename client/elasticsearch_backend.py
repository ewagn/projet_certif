from elasticsearch import AsyncElasticsearch
from logging import getLogger
from typing import Generator
from dotenv import load_dotenv
load_dotenv('.env')
import os

from client.document_model import Document

lg = getLogger("app")

class ESHandler():
    instances = 0
    es = None
    __is_pdf_index = None
    
    def __init__(self) -> None:
        pass

    @classmethod
    async def create_handler(cls) :

        self = cls()
        if self.es == None or self.instances == 0:
            await self.__create_es_resource()

        self.instances += 1

    async def __create_es_resource(self):
        
            self.es = AsyncElasticsearch(
                hosts=[{'host': 'localhost', 'port': 9200, 'scheme': 'https'}],
                ssl_assert_hostname='es01',
                basic_auth=('elastic', os.getenv('ELASTIC_PASSWORD')),
            # cert_reqs="CERT_REQUIRED",
                ca_certs="./certifs/es/ca/ca.crt")

            await self.es.info()
            lg.info("La connexion à la base de données ElasticSearch est établie.")
    
    async def __create_pdf_index(self):
        is_pdf_index_exists = await self.es.indices.exists(index="pdf_files")
        if not is_pdf_index_exists :
            await self.es.indices.create(index="pdf_files")

        lg.info("L'index de 'pdf_files' a été crée.")        

    async def create_index(self, index_name:str, *args, **kwargs):
        await self.es.indices.delete(index=index_name, ignore_unavailable=True)
        mappings={
            'properties': {
                'embedding': {
                    'type'          : 'dense_vector',
                    'dims'           : 384,
                    "index"         : True,
                    "similarity"    : "dot_product",
                }
            }
        }
        await self.es.indices.create(index=index_name, mappings=mappings)
        lg.info(f"L'index {index_name} a été crée.")
        
    
    # async def save_pdf_to_fs(self, document:Document):
    #     path_string = os.getenv("PDF_FILES_PATH")
    #     if not path_string :
    #         path_string = "./pdf_files"
    #     pdf_folder_path = AsyncPath(path_string)
    #     await pdf_folder_path.mkdir(parents=True, exist_ok=True) 
    #     pdf_file_name = document.file_name
    #     pdf_file_path = pdf_folder_path.joinpath(pdf_file_name)

    #     async with aiofiles.open(pdf_file_path, mode="wb+") as pdf_file :
    #         await pdf_file.write(document.pdf)
        
    #     document.pdf_file_path = str(pdf_file_path)


    async def check_if_pdf_exists_in_db(self, document:Document):

        bool_query = list()

        fields = {
            "title" : {"query": document.title, "fuzziness": "AUTO"},
            'issn'  : {"query": document.issn},
            }
        
        for field in fields:
            if getattr(document, field) :
                bool_query.append({'match' : {field : fields[field]}})


        if fields and len(fields) > 1 :
            query_params = {
                "bool" :    {
                    "should" :  bool_query,
                    "minimum_should_match" : 1,
                }
            }
        elif fields :
            query_params = fields[0]
        
        else :
            return None

        sort_order = ["_score"]
        result = await self.es.search(index='pdf_files', query=query_params, sort=sort_order)
        results = result['hits']['hits']
        if results :
            document.es_pdf_id = results[0]["_id"]
            document.pdf_exists = True
        else :
            lg.debug("Le PDF n'a pas été retrouvé dans la base de donnée")
            document.pdf_exists = False
        
    # async def __add_pdf(self, document:Document, created_on:datetime):
    #     self.__save_pdf_to_fs(document=document)
    #     pdf_doc = document.get_pdf()
    #     pdf_doc.update({
    #         "created_on"    :   created_on,
    #     })
    #     insert_result = await self.es.index(index='pdf_files', document=pdf_doc)
    #     pdf_id = insert_result["_id"]
    #     if pdf_id :
    #         document.es_pdf_id = pdf_id
    #     else :
    #         e_text = "L'insertion du fichier PDF dans l'index pdf_files à échoué"
    #         raise ConnectionError(e_text)

    async def add_documents(self, documents:Generator):
        if not self.__is_pdf_index:
            await self.__create_pdf_index()
    
        return await self.es.bulk(operations=documents, refresh='true')
    
    def __del__(self):
        if self.instances == 1:
            self.es.close()
            self.es = None
        self.instances += -1