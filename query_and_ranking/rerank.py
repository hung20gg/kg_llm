from FlagEmbedding import FlagReranker
import numpy as np

class Reranker:
    # mixedbread-ai/mxbai-embed-large-v1
    def __init__(self, model_path='BAAI/bge-reranker-v2-m3'):
        self.reranker = FlagReranker(model_path)
    
    @staticmethod
    def create_query(query, docs):
        
        if isinstance(query, list):
            query = query[0]
        if isinstance(docs, str):
            docs = [docs]
            
        pairs = []
        for doc in docs:
            pairs.append([query, doc])
        return pairs
    
    def rerank(self, query, docs, k) -> np.ndarray:
        pairs = self.create_query(query, docs)
        scores = np.array(self.reranker.compute_score(pairs))
        # print(scores)
        docs = np.array(docs)
        
        top_k_indices = np.argpartition(scores, -k)[-k:][::-1]
        #  
        # print(top_k_indices)
        
        # top_k_indices = top_k_indices[np.argsort(-top_k_elements)]
        return top_k_indices
        
        
            
if __name__ == '__main__':
    query = "Hanh is a very talented student."
    docs = [
        "Hanh is a handsome student",
        "Hanh is a smart student",
        "Hanh is a good student",
        "Hanh is a bad student",
    ]
    reranker = Reranker()
    print(reranker.rerank(query, docs, 2)) 