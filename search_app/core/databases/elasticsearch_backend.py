from time import sleep
from elasticsearch import Elasticsearch, helpers
import logging as lg
from typing import Generator
# from dotenv import load_dotenv
# load_dotenv('.env')
import os
from typing import Any

from search_app.core.services.vectorization.text_embedding import text_embedding
# from search_app.core.services.parsing.pdf_parsing import Document

# lg = getLogger("app")

class ESHandler():
    instances = 0
    _es : Elasticsearch = None
    __is_pdf_index = None
    __is_generated_paragraph_index = None
    __text_embedding = None
    
    def __init__(self) -> None:
        self.instances += 1
        self.es

    def create_es_engine(self):
        return Elasticsearch(
                hosts=[{'host': 'es01', 'port': 9200, 'scheme': 'https'}],
                ssl_assert_hostname='es01',
                basic_auth=('elastic', os.getenv('ELASTIC_PASSWORD')),
            # cert_reqs="CERT_REQUIRED",
                ca_certs=os.getenv("ES_VM_CERTIF_PATH") + "ca/ca.crt")
    
    def put_licence(self):
        licence_info = self._es.license.get().raw
        is_licence = False
        if licence_info :
            licence_elements = licence_info.get('license', None)
            if licence_elements :
                licence_status = licence_elements.get('status', None)
                if licence_status and licence_status == 'active':
                    if licence_elements['type'] == 'trial':
                        is_licence = True
        
        if not is_licence :
            self._es.license.post_start_trial(acknowledge = True)
    
    @property
    def es(self) -> Elasticsearch:
        """Instance de l'API ElasticSearch."""
        if self._es == None :
        
            self._es = self.create_es_engine()

            # self.put_licence()

            if not self.__check_if_elser_model_install():
                self.__setup_elser_model()
                self.__create_elser_pipeline()

            self._es.info()
            lg.info("La connexion à la base de données ElasticSearch est établie.")
        if not self._es.ping():
            self._es = self.create_es_engine()
        
        return self._es

    @es.deleter
    def es(self):
        if self._es != None:
            self._es.close()
            self._es = None
    
    @property
    def text_embedding(self):
        if not self.__text_embedding :
            self.__text_embedding = text_embedding

    def __check_if_elser_model_install(self):
        is_install = False
        models_installed = self.es.ml.get_trained_models()
        for model in models_installed['trained_model_configs']:
            if '.elser_model_2' in model['model_id']:
                status = self.es.ml.get_trained_models_stats(
                    model_id=".elser_model_2",
                )
                if status["trained_model_stats"]:
                    if status["trained_model_stats"][0].get("deployment_stats", None):
                        if status["trained_model_stats"][0]["deployment_stats"].get("state", None):
                            if status["trained_model_stats"][0]["deployment_stats"]["state"] == "started":
                                is_install = True
                if not is_install :
                    self.es.ml.delete_trained_model(model_id=".elser_model_2", force=True)
                    sleep(30)

        return is_install
    
    def __create_elser_pipeline(self):
        self.es.ingest.put_pipeline(
            id="elser-ingest-pipeline",
            description="Ingest pipeline for ELSER",
            processors=[
                {
                    "inference": {
                        "model_id": ".elser_model_2",
                        "input_output": [
                            {"input_field": "content",
                             "output_field": "content_embedding"}
                        ],
                    }
                }
            ],
        )

    def __setup_elser_model(self):
        self.es.ml.put_trained_model(
            model_id=".elser_model_2"
            , input={"field_names" : ["text_field"]}
        )
        # sleep(5)
        model_downloaded = False
        while not model_downloaded :
            status = self.es.ml.get_trained_models(
                model_id=".elser_model_2"
                , include="definition_status"
            )
            if status["trained_model_configs"][0]["fully_defined"] :
                model_downloaded = True
            else :
                sleep(5)
        
        self.es.ml.start_trained_model_deployment(
            model_id='.elser_model_2'
            , number_of_allocations=1
            , threads_per_allocation=8
            , wait_for="started"
            ,timeout="10m")
        while True:
            status = self.es.ml.get_trained_models_stats(
                model_id=".elser_model_2",
            )
            if status["trained_model_stats"][0]["deployment_stats"]["state"] == "started":
                return True
            else:
                sleep(5)

    
    @property
    def pdfs_index(self):
        if not self.__is_pdf_index:
            is_pdf_index_exists = self.es.indices.exists(index="pdf-files")
            if not is_pdf_index_exists :
                mappings = {
                    "properties": {
                        "database": {
                            'type' : "keyword"
                        } ,
                        "type": {
                            'type' : "keyword"
                        } ,
                        "title": {
                            'type' : "keyword"
                        },
                        "authors": {
                            'type' : "keyword"
                        },
                        "volume": {
                            'type' : "integer"
                        },
                        "journal_name": {
                            'type' : "keyword"
                        },
                        "number": {
                            'type' : "integer"
                        },
                        "pages": {
                            'type' : "text"
                        },
                        'issn': {
                            'type' : "keyword"
                        },
                        "publication_year": {
                            'type' : "integer"
                        },
                        "publisher": {
                            'type' : "keyword"
                        },
                        'pdf_file_path': {
                            'type' : "text"
                        },
                        "created_on": {
                            'type' : "date"
                        },
                    }
                }
                self.es.indices.create(index="pdf-files", mappings=mappings)
            self.__is_pdf_index = True

            lg.info("L'index de 'pdf_files' a été crée.")

        return "pdf-files"

    @property
    def generated_paragraphs_index(self):
        if not self.__is_generated_paragraph_index:
            is_pdf_index_exists = self.es.indices.exists(index="generated-paragraphs")
            if not is_pdf_index_exists :
                mappings = {
                    "properties": {
                        'title': {
                            'type': 'keyword'
                        },
                        'created_on': {
                            'type': 'date'
                        },
                        'search_index': {
                            'type': "keyword",
                        },
                        'pdfs_source_ids': {
                            'type' : "keyword",
                        },
                        'paragraphs_source_ids': {
                            'type' : 'keyword',
                        },
                        'generated_content': {
                            'type' : 'text',
                        }
                    }
                }
                self.es.indices.create(index="generated-paragraphs", mappings=mappings)
            self.__is_generated_paragraph_index = True

            lg.info("L'index de 'pdf_files' a été crée.")

        return "generated-paragraphs"


    def create_index(self, index_name:str, *args, **kwargs):
        self.es.indices.delete(index=index_name, ignore_unavailable=True)
        settings={"index": {"default_pipeline": "elser-ingest-pipeline"}}
        mappings={
            'properties': {
                "database": {
                    'type': "keyword"
                },
                'es_pdf_id': {
                    'type' : 'keyword'
                },
                'created_on': {
                    'type': 'date'
                },
                "pdf_page": {
                    'type' : "integer"
                },
                "part_title": {
                    'type' : 'keyword'
                },
                "sub_title": {
                    'type' : 'keyword'
                },
                "content": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "content_embedding": {
                    "type": "sparse_vector",
                },
                # "content_vector" : {
                #     "type": {'dense_vector'},
                #     "dims": 256,
                #     "index": True,
                #     "similarity": "cosine"
                # },
            },
        }
        self.es.indices.create(index=index_name, settings=settings, mappings=mappings)
        lg.info(f"L'index {index_name} a été crée.")

    def check_if_pdf_exists_in_db(self, document):

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
        result = self.es.search(index=self.pdfs_index, query=query_params, sort=sort_order)
        results = result['hits']['hits']
        if results :
            document.es_pdf_id = results[0]["_id"]
        else :
            lg.debug("Le PDF n'a pas été retrouvé dans la base de donnée")
            return False
    
    def add_document(self, _index : str,  doc : dict ) -> dict:
        resp =  self.es.index(
            index=_index,
            document=doc
        )

        return resp
    
    def add_documents(self, documents:Generator):
        self.pdfs_index
        self.generated_paragraphs_index
    
        return  helpers.bulk(client=self.es, operations=documents, refresh='true')
    
    def search_from_query(self, query_promt : str) -> dict[str, Any]:

        # query = {
        #     # "sub_searches" : [
        #     #     {
        #     #         'knn' : {
        #     #             'filed' : 'content_vector',
        #     #             'query_vector' : text_embedding.embedded(query_promt),
        #     #             'num_candidates' : 50,
        #     #             'k' : 5
        #     #         },
        #     #     },
        #     #     {
        #     #         'query' : {
                        
        #     #         }
        #     #     }

        #     # ],
        #     # "rank" : {
        #     #     'rrf' : {}
        #     # }
        #     'query' : {
        #         'text_expansion' : {
        #             'content_embedding' : {
        #                 "model_id": ".elser_model_2",
        #                 "model_text": query_promt,
        #             }
        #         }
        #     }
        # }
        aggs = {
            'selected_paragraphs' : {
                'sampler' : {
                    'shard_size' : 100,
                },
                'aggs' : {
                    'keywords' : {
                        "significant_text" : {
                            'field' : "content",
                            'size' : 5,
                            'min_doc_count' : 3,
                            'filter_duplicate_text' : True,
                            },
                        'aggs' : {
                            'docs' : {
                                "top_hits" : {
                                    "size" : 5,
                                    "_source" : {
                                        'includes' : ["es_pdf_id", 'content']
                                    }
                                },
                            },
                        },
                    },
                },          
            },
        }

        result = self.es.search(
            index="search-index-*",
            query={
                'text_expansion' : {
                    'content_embedding' : {
                        "model_id": ".elser_model_2",
                        "model_text": query_promt,
                    }
                }
            },
            aggs=aggs,
            size=0
        )
        return result
    
    def search_from_ids(self, ids : list[str], index : str = "") -> list[dict[str, Any]]:
        pit = self.es.open_point_in_time(keep_alive="1m", index=index)
        if pit :
            pit["keep_alive"] = "1m"
        else :
            e_text = "Impossible de créer un PIT pour la recherche sur ID"
            lg.error(e_text)
            raise ConnectionError(e_text)
        
        search_params = {
            "pit"   : pit,
            'sort'  : [{"_shard_doc" : "desc"}],
            'size'  : 10000,
        }

        if index :
            search_params.update({
                "query": {
                    "terms": {
                    "_id": ids 
                    }
                },
                "index" : index
            })
        else:
            search_params.update({
                "query": {
                    "ids" : {
                    "values" : ids
                    }
                }
            })
        
        resp = self.es.search(**search_params)

        hits = list()

        if resp['hits']["total"] < 10000 :
            hits.extend(resp['hits']['hits'])

        while resp['hits']["hits"] and resp['hits']["total"] >= 10000 :
            hits.extend(resp['hits']['hits'])

            resp = self.es.search(
                search_after=resp['hits']["hits"][-1]["sort"]
                , **search_params)

        self.es.close_point_in_time(id=pit["id"])

        return hits
    
    def __del__(self):
        if self.instances == 1:
            self.close()
        self.instances += -1

    def close(self):
       del self.es
