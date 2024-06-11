from processing_data.extract_data import *
from processing_data.read_pdf import *
from agent.agent_prompt import *
from database.GraphDB import KnowledgeGraphDB
from retrieval.retrieval_hub import RetrievalHub
from query_and_ranking.query import Query
from query_and_ranking.rerank import Reranker

from agent import BedRockLLMs
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

access_key = os.getenv('ACCESS_KEY')
secret_key = os.getenv('SECRET_KEY') 
# secret_token = os.getenv('SECRET_TOKEN')
model_name_cv = os.getenv('MODEL_NAME_CV')
model_name_jd = os.getenv('MODEL_NAME_JD')
model_name = os.getenv('MODEL_NAME')
region_name = os.getenv('REGION_NAME')

# Quang Hung

neo4j_uri = os.getenv('NEO4J_URI')
neo4j_user = os.getenv('NEO4J_USER')
neo4j_password = os.getenv('NEO4J_PASSWORD')

# Using 3 types of LLM
# CV Extraction, Ranking: Sonet
# JD Extraction, code and normal conversation: Haiku
# Routing: mistral

llm_args = {
    "model_name": model_name,
    "access_key": access_key,
    "secret_key": secret_key,
    # "secret_token": secret_token,
    "region_name": region_name
}

llm_cv_extraction_args = {
    "model_name": model_name_cv,
    "access_key": access_key,
    "secret_key": secret_key,
    # "secret_token": secret_token,
    "region_name": region_name
}

llm_jd_extraction_args = {
    "model_name": model_name_cv,
    "access_key": access_key,
    "secret_key": secret_key,
    # "secret_token": secret_token,
    "region_name": region_name
}

print("Loading DB")
llm = BedRockLLMs(**llm_cv_extraction_args)
chatllm = BedRockLLMs(**llm_args)
kg = KnowledgeGraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
retrieval_hub = RetrievalHub(kg)
reranker = Reranker()

cv_query = Query(kg, retrieval_hub)
print("Finish Loading DB")

is_loaded = False
is_cleaned = False
is_setup = False
is_setupkg = False
directory = 'processed'
process = 4
JD_PATH = 'jd_ai_eng.txt'

args = sys.argv
for i in range(1, len(args)):
    if args[i] == '-l':
        is_loaded = True
    elif args[i] == '-c':
        is_cleaned = True
    elif args[i] == '-d':
        directory = args[i+1]
    elif args[i] == '-p':
        process = int(args[i+1])
    elif args[i] == '-s':
        is_setup = True
    elif args[i] == '-j':
        JD_PATH = args[i+1]
    elif args[i] == '-sk':
        is_setupkg = True
        is_setup = True
        
if is_setup:
    if is_setupkg:
        print("Setup Knowledge Graph")
        kg.setup('data/clean4.0/')
    
    print("Setup Retrival Hub")
    retrieval_hub.setup()
    
    print("Finish Setup")

if is_loaded:
    load_docs(f"data/raw/", is_split=False)

if is_cleaned:
    fast_clean_and_jsonify_data("gemini", dir=f'data/{directory}/', process=process)
