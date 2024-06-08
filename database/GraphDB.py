from langchain_community.vectorstores import Neo4jVector
from langchain_community.graphs import Neo4jGraph
from database.ChromaDB import ChromaDB
from database.utils.GraphDB_query import *
from database.utils.GraphDB_tools import *
from langchain_community.embeddings.sentence_transformer import (
    HuggingFaceEmbeddings,
)
import os
import json
import torch

class KnowledgeGraphDB:
    def __init__(self, uri: str, user: str, password: str, embedding: str = "Alibaba-NLP/gte-large-en-v1.5"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_args = {
            "device": self.device,
            "trust_remote_code": True,
        }
        self.embeddings = HuggingFaceEmbeddings(model_name = embedding, model_kwargs=model_args)
        self.kg = Neo4jGraph(uri, user, password)
        self.summary_db = ChromaDB("temp/summary.db", self.embeddings)
        self.text_db = ChromaDB("temp/graph_text.db", self.embeddings)
        
    def query(self, query, args = None):
        if args:
            return self.kg.query(query, params=args)
        return self.kg.query(query)
    
    def encode(self, text):
        return self.summary_db.embeddings_f.embed(text)
    
    def graph_to_text(self, id):
        return graph_to_text(self.kg, id)
    
    def setup(self, directory: str = 'data/clean2.2/'):
        try:
            text_indexs = [
                'CREATE FULLTEXT INDEX applicationIndex FOR (a:Application) ON EACH [a.email, a.name, a.phone, a.file, a.summary, a.address];',
                'CREATE FULLTEXT INDEX languageIndex FOR (l:Language) ON EACH [l.name];',
                'CREATE FULLTEXT INDEX institutionIndex FOR (i:Institution) ON EACH [i.name];',
                'CREATE FULLTEXT INDEX academicIndex FOR (a:Academic) ON EACH [a.name];',
                'CREATE FULLTEXT INDEX majorIndex FOR (m:Major) ON EACH [m.name];',
                'CREATE FULLTEXT INDEX roleIndex FOR (r:Role) ON EACH [r.name];',
                'CREATE FULLTEXT INDEX awardIndex FOR (a:Award) ON EACH [a.name];',
                'CREATE FULLTEXT INDEX companyIndex FOR (c:Company) ON EACH [c.name];',
                'CREATE FULLTEXT INDEX skillIndex FOR (s:Skill) ON EACH [s.name];',
                'CREATE FULLTEXT INDEX programmingLanguageIndex FOR (p:ProgrammingLanguage) ON EACH [p.name];',
                'CREATE FULLTEXT INDEX techStackIndex FOR (t:TechStack) ON EACH [t.name];',
                'CREATE FULLTEXT INDEX certificationIndex FOR (c:Certification) ON EACH [c.name];',
                'CREATE FULLTEXT INDEX cityIndex FOR (c:City) ON EACH [c.name];'
            ]
            for text_index in text_indexs:
                self.kg.query(text_index)
        except:
            print("Already created indexes")
            
        num_file = len(os.listdir(directory))
            
        for i, file in enumerate(os.listdir(directory)):
            print(f"Adding ({i+1}/{num_file}) :", file)
            dir = directory + file
            with open(dir, 'r') as f:
                json_data = json.load(f)
            if json_data:
                json_data = json_data[0]
                self.add_new_application(json_data, directory=dir)

    
    def get_application_graph(self, id):
        return self.query(APPLICATION_QUERY, {"id": id})
    
    
    def add_new_application(self, json_data, directory = None):
        if not isinstance(json_data,dict):
            return
        if 'birth_year' not in json_data:
            json_data['birth_year'] = None
        
        if directory is not None:
            json_data['file'] = directory.replace('.json','.pdf')
        
        # Get the summary of the application
        if 'summary' in json_data and json_data['summary'] is not None:
            summary = get_summary_data(json_data, 'summary')
        else:
            summary = ''
            
        if 'work_summary' in json_data and json_data['work_summary'] is not None:
            work_summary = get_summary_data(json_data, 'work_summary')
        else:
            work_summary = ''
            
        if 'education_summary' in json_data and json_data['education_summary'] is not None:
            education_summary = get_summary_data(json_data, 'education_summary')
        else:
            education_summary = ''
            
        if 'projects' in json_data and json_data['projects'] is not None:
            project_summary = get_summary_data(json_data, 'projects')
        else:
            project_summary = ''

        json_data['summary'] = summary
        json_data['work_summary'] = work_summary
        json_data['education_summary'] = education_summary
        json_data['project_summary'] = project_summary

        # json_data['summaryEmbedding'] = embeddings.embed_query(json_data['summary'])
        data = self.kg.query(CREATE_USER, params={'formInfoParam':json_data})
        id = data[0]['id']
        # print("Pass General")
        # Store the summary in ChromaDB
        self.summary_db.add_texts(texts=[summary, work_summary, education_summary, project_summary], metadatas=[{"id":id}]*4)
        
        if 'city' in json_data and json_data['city'] is not None:
            json_data['city'] = json_data['city'].lower().split(',')[-1].replace('city','').strip()
            if json_data['city'] == 'hanoi':
                json_data['city'] = 'ha noi'
            self.kg.query(MATCH_CITY, params={"id":id, "city":json_data['city']})
        
        # print("Pass City")
        
        if 'language' in json_data and json_data['language'] is not None:
            for language in json_data['language']:
                # Check if language is None
                if language is None:
                    continue
                self.kg.query(MATCH_LANGUAGE, params={"id":id, "language":language.split()[0]})
        
        # print("Pass Language")
        
        if 'education' in json_data and json_data['education'] is not None: 
            for edu in json_data["education"]:
                edu = fix_education(edu)
                if edu["institution"] is not None:
                    self.kg.query(MATCH_INSTITUTION, params={"id":id, "institution":edu["institution"]})
                if edu["academic_level"] is not None:
                    if 'GPA' not in edu or edu['GPA'] is None:
                        gpa = 3.6
                        is_gpa = False
                    else:
                        gpa = edu['GPA']
                        is_gpa = True
                    self.kg.query(MATCH_ACADEMIC, params={"id":id, "academic":edu["academic_level"], "GPA":gpa, "is_GPA":is_gpa})
                if 'major' in edu and edu['major'] is not None:
                    self.kg.query(MATCH_MAJOR, params={"id":id, "major":edu["major"], "academic":edu["academic_level"]})
            
        # print("Pass Education")
        
        if 'suitable_role' in json_data and json_data['suitable_role'] is not None:
            for role in json_data["suitable_role"]:
                role = role.lower().replace('intern','').strip()
                self.kg.query(MATCH_SUITABLE_ROLE, params={"id":id, "role":role})
        
        # print("Pass Suitable Role")
        
        if 'achievements_awards' in json_data and json_data['achievements_awards'] is not None:
            for achievement in json_data["achievements_awards"]:
                if achievement is None:
                    continue
                self.kg.query(MATCH_AWARD, params={"id":id, "award":str(achievement)})
            
        # print("Pass Award")
        
        if 'certification' in json_data and json_data['certification'] is not None:
            for certification in json_data["certification"]:
                if certification is None:
                    continue
                self.kg.query(MATCH_CERTIFICATION, params={"id":id, "certification":str(certification)})
        
        # print("Pass Certification")
            
        if 'work_experience' in json_data and json_data['work_experience'] is not None:
            for work in json_data["work_experience"]:
                status, work = fix_work(work)
                if status:
                    self.kg.query(MATCH_WORK_EXPERIENCE, params={"id":id, "work":work})
        

        
        if 'roles' in json_data and json_data['roles'] is not None:
            new_roles = fix_roles(json_data["roles"])
            for role in new_roles:
                if isinstance(role, str):
                    role = {"role":role, "year_of_exp":0.5}
                else:
                    self.kg.query(MATCH_ROLE, params={"id":id, "role":role})
                
        

            
        if 'skills' in json_data and    json_data['skills'] is not None:
            skills = fix_skills(json_data["skills"])
            for skill in skills:
                if isinstance(skill, str):
                    skill = {"name":skill, "level":0.5}
                self.kg.query(MATCH_SKILL, params={"id":id, "skill":skill['name'].lower()})

        if 'programming_language' in json_data and json_data['programming_language'] is not None:
            pl_data = fix_language(json_data["programming_language"])
            for programming_language in pl_data:
                if isinstance(programming_language, str):
                    programming_language = {"programming":programming_language, "year_of_exp":0.5}
                self.kg.query(MATCH_PROGRAMMING_LANGUAGE, params={"id":id, "programming_language":programming_language})
        # print("Pass All")
        graph_text = graph_to_text(self.kg, id)
        string_id = 'id'+str(id)
        self.text_db.add_texts(texts=[graph_text], ids=[string_id], metadatas=[{"id":id}])     
        
        # if 'technical_field' in json_data and json_data['technical_field'] is not None:
        #     for tech_stack in json_data["technical_field"]:
        #         if tech_stack is None:
        #             continue
        #         self.kg.query(MATCH_TECH_STACK, params={"id":id, "tech_stack":tech_stack.lower().replace('-','')})
    
    def sematic_search(self, query, top_k = 10):
        result = self.summary_db.search_top_matches(query, top_k=top_k)
        return result
    
    def get_application_summary(self, id):
        query = "Match (n:Application) where id(n) = $id return n.summary as summary, n.work_summary as work_summary, n.education_summary as education_summary, n.project_summary as project_summary"
        result = self.query(query, {"id": id})
        return result[0]
        
    def delete_application(self, id):
        # Delete on Summary DB
        
        records = self.summary_db.search_documents(metadata={"id": id})
        for document in records:
            self.summary_db.delete_document(document_id=document['id'])
        
        # Delete on KnowLedge Graph
        query = """
            MATCH (p:Application)
            WHERE p.id = $id
            DETACH DELETE p
        """
        self.kg.query(query, params={"id": id})
