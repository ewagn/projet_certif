from sentence_transformers import SentenceTransformer

class TextEmbedding():

    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    def __init__(self) -> None:
        pass
    
    async def embedded(self, text:str):
        enc_text = self.model.encode(text)
        return enc_text

text_embedding = TextEmbedding()