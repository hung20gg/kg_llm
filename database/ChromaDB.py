from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)
import chromadb
import os

class ChromaDB(Chroma):
    def __init__(self, data_path: str, model: str = 'BAAI/bge-small-en-v1.5'):
        
        if isinstance(model, str):
            if model == "openai":
                self.embeddings_f = OpenAIEmbeddings(api_key=openai_key, model="text-embedding-3-small")
            else:
                self.embeddings_f = SentenceTransformerEmbeddings(model_name=model)
        else:
            self.embeddings_f = model
        self.data_path = data_path
        self.client_f = chromadb.PersistentClient(path=data_path)
        super().__init__(client = self.client_f, embedding_function= self.embeddings_f)
        
    def load_cypher_query(self, directory: str = 'database/cypher_query'):
        for file in os.listdir(directory):
            with open(os.path.join(directory, file), "r") as f:
                data = f.read()
            data = data.split('```')
            prompt = data[0].strip()
            query = data[1].strip()
            self.add_texts([prompt], metadatas=[{"query": query}])
        
    def search_top_matches(self, text, threshold, top_k = 5, return_doc = False):
        answer = []
        result = self.similarity_search_with_relevance_scores(text, top_k)
        top_score = result[0][1]
        if top_score < 0.7:
            threshold = max(0.7, 1.1*threshold)
        if top_score < 0.35:
            threshold = max(0.8, 1.2*threshold)
        min_score = top_score * threshold
        
        for item in result:
            if item[1] >= min_score:
                if not return_doc:
                    answer.append(item[0].page_content)
                else:
                    answer.append(item[0])
        return answer
    
    def search_top_matches_from_list(self, text_list, threshold, top_k = 5, return_doc = False):
        answers = []
        for text in text_list:
            answers.extend(self.search_top_matches(text, threshold, top_k, return_doc))
        return [*set(answers)]
