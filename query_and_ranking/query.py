from retrieval.retrieval_hub import RetrivalHub
from database.GraphDB import KnowledgeGraphDB
from database.ChromaDB import ChromaDB
from agent.agent_prompt import *
import numpy as np
from scipy.spatial.distance import cdist
import math

def cosine_similarity_search(query, data, top_k=5):
    """
    Perform cosine similarity search on the given data.
    
    Args:
        query (np.ndarray): The query vector.
        data (np.ndarray): The data array.
        top_k (int, optional): The number of top similar vectors to return. Default is 5.
    
    Returns:
        np.ndarray: The indices of the top_k most similar vectors in the data.
    """
    # Expand dimensions if necessary
    if query.ndim == 1:
        query = query.reshape(1, -1)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    
    # Compute cosine distances
    cosine_distances = cdist(query, data, metric='cosine')
    
    # Get the top_k indices
    top_k_indices = np.argsort(cosine_distances, axis=1)[:, :top_k]
    if top_k_indices.shape[0] == 1:
        top_k_indices = top_k_indices[0]
    return top_k_indices

class Query:
    def __init__(self, kg: KnowledgeGraphDB, retrieval_hub : RetrivalHub):
        self.kg = kg
        self.retrieval_hub = retrieval_hub
        
    def get_cv(self, llm, JD, lm=None, llm_ranking = False):
        jd_summarize, jd_out, jd_extraction = extract_job_requirements_prompt(llm, JD, lm=lm)
        print("End LLM")
        
        # Cyhper Query (chuaw fix education)
        result = dict()
        for i,jd in enumerate(jd_extraction):
           
            data, query_string = self.retrieval_hub.retrieve_cypher_query(jd)

            try:
                num_application = jd['numApplication']
            except:
                num_application = 3
            
            extended_num_application = int(min(num_application*1.5,num_application*1.15+2))
            print("Extended Num Application: ", extended_num_application)
            
            data = self.kg.query(query_string, args ={'form':data})
            ids = [d['id'] for d in data]
            
            from_graph = len(ids)
            
            # Routing:
            if num_application != -1:
                is_risk = False
                if len(ids) > extended_num_application:
                    print("Reduce CV ",len(ids), " -> ", extended_num_application, " CV")
                    # More Condition
                    is_risk = True
                    ids = self.get_more_cv_from_graph(jd, 1.15)
                    
                    # Still more than extended_num_application
                    
                    if len(ids) > extended_num_application:
                        print("Still more -> Reduce CV")
                        ids = self.reduce_cv(jd_summarize, ids, extended_num_application)
                    from_graph = len(ids)
                    print("Risk: ", is_risk)
                # A Gap between extended_num_application and num_application is allowed

                if len(ids) < num_application:
                    print("Not enough application")
                    threshold = 0.9
                    
                    # Drop risky features
                    if is_risk:
                        print("Reduce Risk -> Get more CV")
                        threshold = 1.05

                    big_ids = self.get_more_cv_from_graph(jd, threshold)
                    new_ids = []

                    for idx in big_ids:
                        if idx not in ids:
                            new_ids.append(idx)
                            
                            from_graph = len(new_ids)
                    print(big_ids)
                    if len(big_ids) > extended_num_application:
                        print("More -> Reduce CV")
                        
                        # Using LLMs to get less CV
                        if llm_ranking:
                            print("Using LLMs")
                            num_selection = num_application
                            docs_selection = []
                            get_text, get_id = self.get_graph_text(big_ids)
                            for doc, id in zip(get_text, get_id):
                                docs_selection.append({"text":doc, "id":id})
                                
                            selected_ids = select_suitable_cv_prompt(llm, docs_selection, jd_summarize, num_selection)
                            ids = selected_ids
                            
                        # Using sematic Search
                        else:
                            keep_top_k = extended_num_application - len(ids)
                            keep_ids = self.reduce_cv(jd_summarize, new_ids, keep_top_k)
                            for x in keep_ids:
                                if x not in ids:
                                    ids.append(x)
                            from_graph = len(ids)
                    # A Gap between extended_num_application and num_application is allowed
                                            
                    elif len(big_ids) < num_application:
                        print("Less -> Sematic Search")
                        docs = self.kg.text_db.similarity_search_with_relevance_scores(jd_summarize, extended_num_application)
                        
                        # Using LLMs to get more CV
                        if llm_ranking:
                            print("Using LLMs")
                            num_selection = num_application - len(big_ids)
                            docs_selection = []
                            for doc in docs:
                                id = doc[0].metadata['id']
                                if id not in big_ids:
                                    docs_selection.append({"text":doc[0].page_content, "id":id})
                                
                            selected_ids = select_suitable_cv_prompt(llm, docs_selection, jd_summarize, num_selection)
                            for id in selected_ids:
                                big_ids.append(id)
                                
                        # Using sematic search to get more CV  
                        # For LLMs in case bug occurs  
                        print("Using Sematic Search")
                        for doc in docs:
                            if len(big_ids) == num_application:
                                break
                            id = doc[0].metadata['id']
                            if id not in big_ids:
                                big_ids.append(id)
                        ids = big_ids
                        
                    else:
                        ids = big_ids
                print("Num CV ok: ", len(ids))
            
            else:
                # Try to get more CV
                big_ids = self.get_more_cv_from_graph(jd, 0.85)
                
                # If get to much CV, reduce
                if len(big_ids) > 15:
                    big_ids = self.get_more_cv_from_graph(jd, 1)
                ids = big_ids
            if not llm_ranking or num_application != -1:
                result["graph"] = from_graph
            result[f"job_{i}"] = ids
            result['numApplication'] = num_application
            
        return result, jd_summarize, jd_out
    
    def get_graph_text(self, ids):
        string_ids = [f"id{d}" for d in ids]
        
        query = self.kg.text_db.get(ids = string_ids)
        cv_text = query['documents']  
        cv_text_ids = query['ids']
        ids = [int(id.replace('id','')) for id in cv_text_ids]
        
        return cv_text, ids
        
    
    def reduce_cv(self, jd, ids, top_k):
        string_ids = [f"id{d}" for d in ids]
        query = self.kg.text_db.get(ids = string_ids, include = ['embeddings'])
        cv_embeddings = query['embeddings']  
        cv_text_ids = query['ids']
        
        ids = [int(id.replace('id','')) for id in cv_text_ids]
        
        cv_embeddings = np.array(cv_embeddings)
        id_np = np.array(ids)
        jd_embedding = self.kg.text_db.embeddings_f.embed_query(jd)
        jd_embedding = np.array(jd_embedding)
        idx = cosine_similarity_search(jd_embedding, cv_embeddings, top_k)
        return id_np[idx].tolist()
    
    
    def get_cv_summary(self, id):
        summary = self.kg.get_application_summary(id)
        text_summary = summary['summary']
        text_summary += '\n'+ summary['work_summary']
        text_summary += '\n'+ summary['education_summary']
        text_summary += '\n'+ summary['project_summary']
        return text_summary
                
    def get_more_cv_from_graph(self, jd, threshold = 0.9):
        new_jd = jd.copy()
        # del new_jd['skillList']
        if threshold < 1:
            del new_jd['languageList']
            if 'role_exp' not in jd or new_jd['role_exp'] is None or jd['role_exp'] < 0.5:
                if 'suitableList' in jd and jd['suitableList'] is not None and len(jd['suitableList']) > 0 and jd['suitableList'][0] is not None:
                    del new_jd['roleList']
                    if 'role_exp' in jd:
                        del new_jd['role_exp']
            if 'eduList' in jd:
                del new_jd['eduList']
            if 'majorList' in jd:
                del new_jd['majorList']
        # print(new_jd)
        
        data, query_string = self.retrieval_hub.retrieve_cypher_query(new_jd, threshold)
        data = self.kg.query(query_string, args ={'form':data})
        return [d['id'] for d in data]
        
if __name__ == "__main__":
    query = np.array([1, 2, 3])
    data = np.array([[1, 2, 3], [4, 5, 6], [1, 2, 3.4]]) 
    ids = np.array(['id1', 'id2', 'id3'])
    idx = cosine_similarity_search(query, data, top_k=2)
    print(ids[idx])