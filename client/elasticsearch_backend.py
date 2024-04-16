from elasticsearch import AsyncElasticsearch
import asyncio
from typing import List
from dotenv import load_dotenv
load_dotenv('.env')
from pprint import pprint
from datetime import datetime
import os
from pathlib import Path


from client.document_model import Document

class Search():
    instances = 0
    es = AsyncElasticsearch(
        hosts=[{'host': 'localhost', 'port': 9200, 'scheme': 'https'}],
        ssl_assert_hostname='es01',
        basic_auth=('elastic', os.getenv('ELASTIC_PASSWORD')),
    # cert_reqs="CERT_REQUIRED",
        ca_certs="./certifs/es/ca/ca.crt")
    
    

    __is_pdf_index = None
    
    
    def __init__(self) -> None:
        self.instances += 1
        # client_info = self.es.info()
        print("Connected to Elasticsearch !")
        # pprint(client_info)
        self.pdf_index = ""
    
    async def __create_pdf_index(self):
        is_pdf_index_exists = await self.es.indices.exists(index="pdf_files")
        if not is_pdf_index_exists :
            await self.es.indices.create(index="pdf_files")
            self.__is_pdf_index = True
        

    async def create_index(self, index_name):
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
        self.index = index_name
    
    async def __save_pdf_to_fs(self, document:Document):
        path_string = os.getenv("PDF_FILES_PATH")
        if not path_string :
            path_string = "./pdf_files" 
        pdf_folder_path = Path(path_string)
        pdf_folder_path.mkdir(parents=True, exist_ok=True) 
        pdf_file_name = document.file_name

        with open(os.path.join(pdf_folder_path, pdf_file_name), mode="wb+") as pdf_file :
            pdf_file.write(document.pdf)
        
        document.pdf_file_path = os.path.join(pdf_folder_path, pdf_file_name)


    async def __check_if_pdf_exists(self, document:Document):

        bool_query = list()

        pdf_document = document.get_pdf()

        fields = {
            "title" : {"query": pdf_document.get("title"), "fuzziness": "AUTO"},
            'issn'  : {"query": pdf_document.get("issn")},
            }
        
        for field in fields:
            if field in pdf_document:
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
        result = self.es.search(index='pdf_files', query=query_params, sort=sort_order)
        results = result['hits']['hits']
        if results :
            document.es_pdf_id = results[0]["_id"]
            return True
        else :
            return False
        
    async def __add_pdf(self, document:Document, created_on:datetime):
        self.__save_pdf_to_fs(document=document)
        pdf_doc = document.get_pdf()
        pdf_doc.update({
            "created_on"    :   created_on,
        })
        insert_result = self.es.index(index='pdf_files', document=pdf_doc)
        pdf_id = insert_result["_id"]
        if pdf_id :
            document.es_pdf_id = pdf_id
        else :
            e_text = "L'insertion du fichier PDF dans l'index pdf_files à échoué"
            raise ConnectionError(e_text)

    async def add_documents(self, query_string:str, documents:List[Document], created_on:datetime, index:str=None):
        if not self.__is_pdf_index:
            self.__create_pdf_index()

        if not index:
            index = self.index
        
        if not isinstance(index, str):
            e_text = f"L'index doit être une string"
            raise ValueError(e_text)
        
        if not isinstance(documents, list):
            e_text = f"Le document doit être une liste de Document"
            raise ValueError(e_text)

        operations = list()

        for document in documents:
            if document.doc_type == 'pdf':
                if not self.__check_if_pdf_exists(document):
                    self.__add_pdf(document=document, created_on=created_on)

            for paragraph in document():

                paragraph.update({
                    "created_on"    :   created_on
                })

                paragraph.update({
                    "user_query"    :   query_string,
                })

                doc_content = paragraph.get("content", None)
                if doc_content:
                    paragraph.update({
                        "embedding" :   self.__text_embedding.embedded(doc_content),
                    })

                operations.append({
                    'index' :   {'_index'   :   index}
                })

                operations.append(paragraph)
    
        return await self.es.bulk(operations=operations, refresh='true')
    
    def __del__(self):
        if self.instances == 1:
            self.es.close()
        self.instances += -1

es_search = Search()