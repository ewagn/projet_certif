from datetime import datetime
from typing import Any
import logging as lg

from search_app.core.databases.sql_models import GeneratedParagraphs
from search_app.core.services.text_summarize.engine import TextSummerize
from search_app.core.databases.elasticsearch_backend import ESHandler

class SummerizedParagraph():

    def __init__(self, category : str, paragraphs : dict[str, dict[str, str]], created_on: datetime, search_index : str,  summerizer : TextSummerize | None = None) -> None:
        self.title = category
        self.created_on = created_on
        self.search_index = search_index
        self.source_paragraphs_ids = list(paragraphs.keys())
        self.pdfs_source_ids = [paragraphs[i]['pdf_id'] for i in self.source_paragraphs_ids]
        self.unsummerized_content = [paragraphs[i]['content'] for i in self.source_paragraphs_ids]

        if summerizer :
            self.summerize_text(summerizer=summerizer)
        else :
            self.summerized_content = None
        
        self._es_id     : str = None
        self.pdf_refs   : list[dict[str, Any]]  = None
    


    
    def summerize_text(self, summerizer : TextSummerize):
        self.summerized_content = summerizer.synthethize_paragraphs(self.unsummerized_content)
    
    def get_generated_paragraph_to_es_doc(self, es_handler : ESHandler):

        return {
            '_index' : es_handler.generated_paragraphs_index,
            'doc' : {
                'title'                 : self.title,
                'created_on'            : self.created_on.isoformat(),
                'search_index'          : self.search_index,
                'pdfs_source_ids'       : self.pdfs_source_ids,
                'paragraphs_source_ids' : self.source_paragraphs_ids,
                'generated_content'     : self.summerized_content,
            },
        }

    
    def put_in_es_database(self, es_handler : ESHandler):
        if not self.summerized_content :
            e_text = "Les paragraphes n'ont pas été résumés."
            lg.error(e_text)
            raise ValueError(e_text)

       
        
        resp = es_handler.add_document(**self.get_generated_paragraph_to_es_doc(es_handler=es_handler))
        self._es_id = resp['_id']
    
    def get_sql_model(self):
        if not self._es_id :
            e_text = "Le paragraph n'a pas été enregistré dans la base de données Elasticsearch."
            lg.error(e_text)
            raise ValueError(e_text)
        return GeneratedParagraphs(
            generated_pargraphs_es_id   = self._es_id
        )
    
    def retrieve_bibliographical_info(self, es_handler : ESHandler) :
        ref_data = ["type", "title", "authors", "volume", "journal_name", "number", "pages", "issn", "publication_year", "publisher"]

        if not self.pdf_refs :
            self.pdf_refs = list()
            hits = es_handler.search_from_ids(ids=self.pdfs_source_ids, index=es_handler.pdfs_index)

            for hit in hits :
                hit_data = hit['_source']
                d = dict()
                for data in ref_data :
                    d.update({data : hit_data.get(data, None)})
                self.pdf_refs.append(d)
        
    def build_bibliography(self, bib_ref : dict[str, Any]):
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
 
    def __call__(self, *args: Any, **kwds: Any) -> dict[str, str]:

        if self.pdf_refs :

            return {
                'title'     : self.title,
                'id'        : self._es_id,
                'content'   : self.summerized_content,
                'refs'      : [self.build_bibliography(bib_ref=ref) for ref in self.pdf_refs]
            }

        else :
            e_text = "Les données bibliographiques n'ont pas été récupérées"
            lg.error(e_text)
            raise ValueError(e_text)
