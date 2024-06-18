from processing_data.extract_data import *
from processing_data.read_pdf import *
import agent.agent_prompt as agent_prompt
from agent import BedRockLLMs, LLMChat, CoreLLMs, Gemini

import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

access_key = os.getenv('ACCESS_KEY')
secret_key = os.getenv('SECRET_KEY') 
secret_token = os.getenv('SECRET_TOKEN')
model_name_cv = os.getenv('MODEL_NAME_CV')
model_name_jd = os.getenv('MODEL_NAME_JD')
model_name_routing = os.getenv('MODEL_NAME_ROUTING')
model_name = os.getenv('MODEL_NAME')
region_name = os.getenv('REGION_NAME')


def ranking_to_text(ranking):
    text = 'Here are the ranking order of the CVs:\n\n'
    for rank in ranking:
        text += f"**{rank[0]+1}. ID: {rank[1]}**\n"
        text += f"Explanation: {rank[2]}\n\n"
        
    return text

class Agent:
    def __init__(self, kg,
                retrieval_hub,
                reranker,
                query,
                routing = 'local',
                jd_extraction = 'aws'):
        self.llm_args = {
            "model_name": model_name,
            "access_key": access_key,
            "secret_key": secret_key,
            "secret_token": secret_token,
            "region_name": region_name
        }
        
        self.llm_routing_args ={
            "model_name": model_name_routing,
            "access_key": access_key,
            "secret_key": secret_key,
            "secret_token": secret_token,
            "region_name": region_name
        }
        
        # self.llm_cv_extraction_args = {
        #     "model_name": model_name_cv,
        #     "access_key": access_key,
        #     "secret_key": secret_key,
        #     "secret_token": secret_token,
        #     "region_name": region_name
        # }
        
        self.llm_jd_extraction_args = {
            "model_name": model_name_jd,
            "access_key": access_key,
            "secret_key": secret_key,
            "secret_token": secret_token,
            "region_name": region_name
        }
        
        self.kg = kg
        self.retrieval_hub = retrieval_hub
        self.reranker = reranker
        self.chatbot = LLMChat(**self.llm_args)
        # self.llm_cv_extraction = BedRockLLMs(**self.llm_cv_extraction_args)
        
        if jd_extraction == 'local':
            self.llm_jd_extraction = CoreLLMs()
        elif jd_extraction == 'aws':
            self.llm_jd_extraction = BedRockLLMs(**self.llm_jd_extraction_args)
        elif jd_extraction == 'gemini':
            self.llm_jd_extraction = Gemini()
        else:
            self.llm_jd_extraction = CoreLLMs(model_name=jd_extraction)
            
        if routing == 'local':
            self.llm_routing = CoreLLMs(model_name='microsoft/Phi-3-mini-4k-instruct')
        else:
            self.llm_routing = BedRockLLMs(**self.llm_routing_args)
            
        self.query = query
        self.system_message = {"role":"system", 
                                "content":"""You are an helpful assistant for HR department. You should provide high quality and precise response to HR. If you are not sure about anything, feel free to ask for clarity. If you don't know about the answer, just response I don't know. The current recruitment date is May 2024"""}
        self.messages = [self.system_message]
        self.ids = []
        self.extraction_process = False
        self.JD = ''
        
    def routing_response(self, message):
        routing_response = agent_prompt.routing_response(self.llm_routing, message)

        return routing_response
    
    def routing_ranking_response(self, message):
        routing_response = agent_prompt.routing_ranking(self.llm_routing, message)

        return routing_response
        
    def chat(self, message):
        # Normal Chat
        self.messages.append({"role":"user", "content":message})
        # Routing for ranking
        if self.extraction_process:
            routing_ranking_response = self.routing_ranking_response(message)
            
            # Need to end or create more process
            # if routing_ranking_response['answer'] == 1:
            #     return self.ranking_cv_prompt(message)
            
            # if routing_ranking_response['answer'] == 2:
            #     return self.analyze(message)
            if routing_ranking_response:
                response = self.ranking_cv_prompt(message)
                self.messages.append({"role":"assistant", "content":response['text']})
                return response
            
        self.extraction_process = False
        
        # Routing for JD Extraction
        routing_response = self.routing_response(message)
        if routing_response:
            self.extraction_process = True
            response = self.get_cv_from_jd(message)
            ids = response['id']
            response_message = self.summarize_cv(ids)
            
            response_message['text'] = self.jd_out + '\n\n' + response_message['text']
            self.summary_cv = response_message['summary_cv']
            
            
            self.messages.append({"role":"assistant", "content":response_message['summary_cv']})
            return {'text':response_message['text'], 'files':response['files']}
        
        # Normal Chat
        response = self.chatbot.chat(self.messages)
        self.messages.append({"role":"assistant", "content":response})
        return {'text':response}
    
    def ranking_cv_prompt(self, message):
        begin = time.time()
        ranking_text = ''

        for id, doc in zip(self.ids, self.docs):
            ranking_text += f"**ID: {id}**\n"
            ranking_text += doc + '\n'

        
        ranking = ranking_cv_prompt(self.llm_jd_extraction, ranking_text, self.JD, message)
        
        rank_ids = []
        for rank in ranking:
            rank_ids.append((rank['rank']-1 ,rank["id"], rank['explanation']))
        
        rank_ids.sort(key=lambda x: x[0])
        ids = [id for _, id,_ in rank_ids]
        
        query = "Match (n:Application) where id(n) IN $id return n.file as file"
        files = self.kg.query(query, args = {'id':ids})
        
        url_files = ['data/raw/'+f['file'] for f in files]
        
        response = ranking_to_text(rank_ids)

        end = time.time()
        print(f"Time: {end - begin}")
        return {'text':response, 'files':url_files, 'time':end-begin}
    
    def analyze(self, message):
        pass
    
    def get_cv_from_jd(self, message, llm_ranking = False):
        print("Extracting Job Description")
        JD = message
        begin = time.time()
        data, jd_summarize, jd_out = self.query.get_cv(self.llm_jd_extraction, JD, self.llm_routing, llm_ranking)
        
        self.jd_out = jd_out
        # yield jd_out
        self.JD = jd_summarize
        
        # Temp only find 1 positions
        ids = data['job_0']
        
        # Reranking
        print("Rerank")
        
        num_application = data['numApplication']
        graph_text = self.kg.text_db.get(ids=[f"id{d}" for d in ids])
        
        graph_text_ids = graph_text['ids']
        graph_text_docs = graph_text['documents']
        
        self.ids = []
        self.docs = []
        
        for id, doc in zip(graph_text_ids, graph_text_docs):
            id = id.replace('id', '')
            id = int(id)
            self.ids.append(id)
            self.docs.append(doc)
        
        
        num_application = data['numApplication']
        if len(ids) > num_application and num_application != -1:
            print("Reranking")
                    
            # Keep data from graph
            
            
            if "graph" in data:
                from_graph = data["graph"]
                
                # If original data from graph is less than sematic search
                if from_graph <= num_application:
                    num_application = from_graph
                    save_ids = self.ids[:from_graph]
                    save_docs = self.docs[:from_graph]
                    
                    rank_docs = self.docs[from_graph:]
                    rank_ids = self.ids[from_graph:]
                    
                    num_rank = num_application - from_graph
                    docs = self.kg.text_db.get(ids=[f"id{d}" for d in rank_ids])['documents']
                    top_indices = self.reranker.rerank(jd_summarize, docs, num_rank)
                    save_ids.extend([rank_ids[i] for i in top_indices])
                    save_docs.extend([rank_docs[i] for i in top_indices])
                    
                    self.ids = save_ids
                    self.docs = save_docs
                
                else:
                # More data from graph than sematic search
                    docs = self.kg.text_db.get(ids=[f"id{d}" for d in self.ids])['documents']
                    top_indices = self.reranker.rerank(jd_summarize, docs, num_application)
                    self.ids = [self.ids[i] for i in top_indices]
                    self.docs = [self.docs[i] for i in top_indices]
                
            else:
                # More data from graph than sematic search
                docs = self.kg.text_db.get(ids=[f"id{d}" for d in self.ids])['documents']
                top_indices = self.reranker.rerank(jd_summarize, docs, num_application)
                self.ids = [self.ids[i] for i in top_indices]
                self.docs = [self.docs[i] for i in top_indices]
        
        print(self.ids)
            
        query = "Match (n:Application) where id(n) = $id return n.file as file"
        
        files = []
        
        for id in self.ids:
            files.append(self.kg.query(query, args = {'id':id})[0])
        
        url_files = ['data/raw/'+f['file'] for f in files]
        end = time.time()
        print(f"Time: {end - begin}")
        
        return {'text':jd_summarize, 'id':self.ids, 'files':url_files, 'time':end-begin}
    
    def summarize_cv(self, ids):
        query = """Match (n:Application) 
        where id(n) IN $id 
        return id(n) as id, n.summary as summary,
        n.work_summary as work_summary,
        n.project_summary as project_summary,
        n.education_summary as education_summary
        """
        
        summaries = self.kg.query(query, args = {'id':ids})
        
        summary_text = ''
        summary_messages = 'Here are the CVs that match the job description:\n\n'
        
        for summary in summaries:
            summary_text += f"**ID: {summary['id']}**:{summary['summary']}"
        if len(ids) <= 7:
            # summary_messages += "|ID | Summary | Education | Work and Project |\n"
            # summary_messages += "|-- | ------- | --------- | ---------------- |\n"
            summary_messages += "|ID | Education | Work and Project |\n"
            summary_messages += "|-- | --------- | ---------------- |\n"
            for summary in summaries:
                
                if summary['education_summary'] is None or len(summary['education_summary'])<10:
                    summary['education_summary'] = "No education summary"
                    
                # Work and education
                work_edu_summary = ''
                if summary['work_summary'] is None or len(summary['work_summary'])<10:
                    if summary['project_summary'] is None or len(summary['project_summary'])<10:
                        work_edu_summary = "No work and project summary"
                    else:
                        work_edu_summary = summary['project_summary']
                else:
                    work_edu_summary = summary['work_summary']

                # summary_messages += f"|**ID: {summary['id']}** | {summary['summary']} | {summary['education_summary']} | {work_edu_summary} |\n"
                summary_messages += f"|**ID: {summary['id']}** | {summary['education_summary']} | {work_edu_summary} |\n"

        else:
            summary_messages = "Too many CVs to display"
        return {'summary_cv':summary_text, 'text':summary_messages}
