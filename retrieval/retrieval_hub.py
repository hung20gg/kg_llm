from database.ChromaDB import ChromaDB
from retrieval.retrieval_tools import CacheChromaDB
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

class RetrivalHub:
    def __init__(self, kg, model_name = 'BAAI/bge-small-en-v1.5'):
        
        self.kg = kg
        self.embeddings_f = SentenceTransformerEmbeddings(model_name=model_name)
        self.cache = CacheChromaDB(model=self.embeddings_f, directory='temp')
        self.cypher = ChromaDB(data_path='temp/cypher.db', model=self.embeddings_f)
        
    def retrieve_cypher_query(self, response, power = 1): # Generated JD in JSON
        prompt, data, query_string = self.cache.generate_query(response, power=power)
        # examples = self.cypher.search_top_matches(prompt, threshold=0.5, top_k=2, return_doc=True)
        # examples = [{"prompt":doc.page_content, "cypher":doc.metadata['query']} for doc in examples]
        # return examples, prompt, data, query_string
        return data, query_string
    
    def setup(self):
        self.cypher.load_cypher_query()
        self.cache.setup_cache(self.kg)
    
    def retrieve_summary_jd(self, jd, top_k): # sematic search jd with summary db
        pass

    def retrieval_application_graph(self, query): # Generated cypher query
    
        pass