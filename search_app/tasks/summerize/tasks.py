from datetime import datetime
from celery import group, chain
from celery.utils.log import get_task_logger
from logging import Logger
from celery.app import task

lg : Logger = get_task_logger(__name__)

from search_app.celery_worker import app
from search_app.core.services.text_summarize.models import SummerizedParagraph

@app.task(name='summerize_paragraph', queue="tasks.search", bind=True)
def summerize_paragraph(self : task, category: str, paragraphs : dict[str, dict[str, str]], search_index : str, created_on: datetime | None =  None) -> SummerizedParagraph :
    
    lg.info("Création d'un paragraphe résumé.")
    paragraph = SummerizedParagraph(
        category=category,
        paragraphs=paragraphs,
        created_on= created_on if created_on else datetime.now(),
        search_index=search_index,
        summerizer=self.text_summerize
    )

    return paragraph

@app.task(name = 'record_to_es', queue="tasks.search", bind=True)
def record_to_es(self : task, summerized_paragraph : SummerizedParagraph) -> SummerizedParagraph:

    lg.info("Enregistrement du paragraphe résumé dans la base de données elasticsearch.")
    summerized_paragraph.put_in_es_database(es_handler=self.esh)

    return summerized_paragraph


@app.task(name='retrieve_bibliographical_info', queue="tasks.search", bind = True)
def retrieve_bibliographical_info(self : task, summerized_paragraph : SummerizedParagraph) -> SummerizedParagraph:
    
    lg.info("Récupération des données bibliographiques du paragraphe généré.")
    summerized_paragraph.retrieve_bibliographical_info(es_handler=self.esh)

    return summerized_paragraph

@app.task(name='summerization_step', queue="tasks.search")
def summerization_step(retrieved_paragrapahs_from_search : list[tuple[str, dict]], search_index: str, created_on: datetime | None = None) -> list[SummerizedParagraph] :
    
    lg.info('Start summerization step.')

    summerizing_paragraphs_list = list()

    for category, paragraphs in retrieved_paragrapahs_from_search:
        summerizing_paragraphs_list.append(
                    chain(
                summerize_paragraph.s(category=category, paragraphs=paragraphs, search_index=search_index, created_on=created_on)
                , record_to_es.s()
                , retrieve_bibliographical_info.s()
            )()
        )

    result = group(summerizing_paragraphs_list)()

    return result