from typing import Any
from elasticsearch import AsyncElasticsearch
import os
import logging as lg

class ESHandler():

    _es = None
    
    def __init__(self) -> None:
        pass

    @property
    def es(self):
        if self._es == None :
            self._es = AsyncElasticsearch(
                hosts=[{'host': 'es01', 'port': 9200, 'scheme': 'https'}],
                ssl_assert_hostname='es01',
                basic_auth=('elastic', os.getenv('ELASTIC_PASSWORD')),
            # cert_reqs="CERT_REQUIRED",
                ca_certs=os.getenv("ES_VM_CERTIF_PATH") + "ca/ca.crt")
        return self._es
    
    @property
    def pdfs_index(self):
        return "pdf-files"
    
    @property
    def generated_paragraphs_index(self):
        return "generated-paragraphs"

    async def search_from_ids(self, ids : list[str], index : str = "") -> list[dict[str, Any]]:
        pit = await self.es.open_point_in_time(keep_alive="1m", index=index)
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
        
        resp = await self.es.search(**search_params)

        hits = list()

        if resp['hits']["total"] < 10000 :
            hits.extend(resp['hits']['hits'])

        while resp['hits']["hits"] and resp['hits']["total"] >= 10000 :
            hits.extend(resp['hits']['hits'])

            resp = self.es.search(
                search_after=resp['hits']["hits"][-1]["sort"]
                , **search_params)

        await self.es.close_point_in_time(id=pit["id"])

        return hits
    
    async def build_bibliography(self, bib_ref : dict[str, Any]):
        authors = bib_ref.get("authors", None)
        year = bib_ref.get('publication_year', None)
        article_title = bib_ref.get("title", None)
        periodic_name = bib_ref.get("journal_name", None)
        volume = bib_ref.get("volume", None)
        number = bib_ref.get("number", None)
        pages = bib_ref.get("pages", None)

        if authors :
            if len(authors) == 2 :
                authors = " & ".join([author.split()[0] for author in authors])
            
            elif len(authors) > 2 :
                authors = authors[0].split()[0] + "and col."
            
            else :
                authors = authors[0]
        
        if year :
            year = f' ({year}). '

        if article_title :
            article_title = f"{article_title}. "
        
        if volume :
            volume = f', {volume}'
        
        if number :
            number = f'({number})'

        if pages :
            pages = f', {pages}'

        ref = "".join(authors, year, article_title, periodic_name, volume, number, pages) + "."
    
        return ref
    
    async def retrieve_bibliographical_info(self, pdf_ids : list[str]) :

        if not pdf_ids :
            e_text = "Aucune donnée bibliographique n'est retoruvée pour ce paragraphe."
            lg.error(e_text)
            raise RuntimeError(e_text)
        pdf_refs = list()
        hits = await self.search_from_ids(ids=pdf_ids, index=self.pdfs_index)

        for hit in hits :
            hit_data = hit['source']
            hit_data.update({
                'id' : hit["_id"]
            })

            pdf_refs.append(await self.build_bibliography(hit_data))
        
        return pdf_refs

    async def get_generated_paragraphs_from_ids(self, ids : list[str]) -> list[dict[str, Any]] | None:

        resp = await self.search_from_ids(ids=ids, index=self.generated_paragraphs_index)

        if resp['hits']['hits'] :
            list_out = list()
            for result in resp['hits']['hits'] :
                dict_out = dict()
                dict_out.update({"id" : result["_id"]})
                dict_out.update({
                    'title'     :   result["_source"].get("title"),
                    'content'   :   result["_source"].get("generated_content"),
                    'refs'      :   await self.retrieve_bibliographical_info(result["_source"].get("pdfs_source_ids"))
                    })
                list_out.append(dict_out)

        else : 
            return None

        return list_out