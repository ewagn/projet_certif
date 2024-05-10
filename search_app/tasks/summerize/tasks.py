from datetime import datetime

from search_app.celery import app, lg
from search_app.core.services.text_summarize.models import SummerizedParagraph

@app.task(bind=True)
def summerize_paragraph(self, category: str, paragraphs : dict[str, dict[str, str]], search_index : str, created_on: datetime | None =  None) -> SummerizedParagraph :
    
    lg.info("Création d'un paragraphe résumé.")
    paragraph = SummerizedParagraph(
        category=category,
        paragraphs=paragraphs,
        created_on= created_on if created_on else datetime.now(),
        search_index=search_index,
        summerizer=self.text_summerize
    )

    return paragraph

@app.task(bind=True)
def record_to_es(self, summerized_paragraph : SummerizedParagraph) -> SummerizedParagraph:

    lg.info("Enregistrement du paragraphe résumé dans la base de données elasticsearch.")
    summerized_paragraph.put_in_es_database(es_handler=self.esh)

    return summerized_paragraph


