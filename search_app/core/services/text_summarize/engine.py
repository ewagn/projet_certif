from transformers import pipeline
from transformers import PegasusForConditionalGeneration, PegasusTokenizer
import string

from search_app.core.services.text_summarize.models import SummerizedParagraph

class TextSummerize():
    _model_name = None
    _tokenizer = None
    _model = None


    def __init__(self, model : str = "google/pegasus-xsum") -> None:
        model

    @property
    def model(self) :

        if not self._model_name:
            e_text = "Aucun model n'est spécifié."
            # lg.error(e_text)
            raise ValueError(e_text)
        
        return self._model
    
    @model.setter
    def model(self, value : str):
        if value != self._model_name :
            self._model_name = value
            self._tokenizer = PegasusTokenizer.from_pretrained(self._model_name)
            self._model = PegasusForConditionalGeneration.from_pretrained(self._model_name)
        
        return self._model

    @property
    def tokenizer(self):
        if not self._model_name :
            e_text = "Aucun model n'est spécifié."
            # lg.error(e_text)
            raise ValueError(e_text)
        
        if not self._tokenizer :
            self._tokenizer = PegasusTokenizer.from_pretrained(self._model_name)
        
        return self._tokenizer
    
    def count_words(self, text : str) -> int:
        
        nb_words = sum([word.strip(string.punctuation).isalpha() for word in text.split()])

        return nb_words
    
    def _get_out_paragraph_lengths (self, paragraphs : list[str]) -> dict[str, int]:

        lengths = list()

        for paragraph in paragraphs :
            lengths.append(self.count_words(paragraph))
        
        return {
            "min_length" : min(lengths),
            "max_length" : sum(lengths) // len(lengths)
        }
    
    def synthethize_paragraphs(self, paragraphs : list[str] | str) -> str :
        
        if isinstance(paragraphs, str) :
            paragraphs = [paragraphs]

        tokens = self.tokenizer(" ".join(paragraphs), truncation=True, padding="longest", return_tensors="pt")
        encoded_summary = self.model.generate(**tokens, **self._get_out_paragraph_lengths(paragraphs=paragraphs))
        summary = self.tokenizer.decode(encoded_summary[0], skip_special_tokens=True)
        
        return summary
        
        