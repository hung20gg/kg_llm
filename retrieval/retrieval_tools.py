from database.ChromaDB import ChromaDB
import math

def get_education_list(eduList):
    ranking = ['high school','undergraduate','certificate','bachelor','diploma','master','phd']
    min_point = 5
    for edu in eduList:
        for i, rank in enumerate(ranking):
            if rank == edu.lower():
                min_point = min(min_point, i)
    return ranking[min_point:]

def json_to_cypher(query: dict):
    match_phrases = []
    where_phrases = []
    
    for k, v in query.items():
        if k == "languageList":
            match_phrases.append(f"(a:Application)-[:SPEAK]->(l:Language)")
            where_phrases.append(f"l.name in $form.{k}") 
            
        if k == "cityList":
            match_phrases.append(f"(a:Application)-[:LIVE_IN]->(c:City)")
            where_phrases.append(f"c.name in $form.{k}")
            
        if k == "institutionList":
            match_phrases.append(f"(a:Application)-[:STUDY]->(i:Institution)")
            where_phrases.append(f"i.name in $form.{k}")
            
        if k == "eduList":
            match_phrases.append(f"(a:Application)-[e:ACADEMIC]->(edu:Academic)")
            where_phrases.append(f"edu.name in $form.{k}")
            
        if k == "GPA":
            if v >= 1:
                if "eduList" not in query:
                    match_phrases.append(f"(a:Application)-[e:ACADEMIC]->(edu)")
                where_phrases.append(f"e.GPA >= $form.{k}")
            
        if k == "roleList":
            match_phrases.append(f"(a:Application)-[r:ROLE]->(role:Role)")
            where_phrases.append(f"role.name in $form.{k}")
            
        if k == "role_exp":
            if "roleList" in query:
                if v > 0:
                    where_phrases.append(f"r.exp >= $form.{k}*0.75 - 0.25 AND r.exp <= $form.{k}*1.5 + 1 ")
            
        if k == "skillList":
            match_phrases.append(f"(a:Application)-[:SKILL]->(skill:Skill)")
            where_phrases.append(f"skill.name in $form.{k}")
                    
        if k == "programmingList":
            match_phrases.append(f"(a:Application)-[p:PROGRAMMING]->(programming:ProgrammingLanguage)")
            where_phrases.append(f"programming.name in $form.{k}")
            
        if k == "programming_exp":
            if "programmingList" in query:
                if v > 0:
                    where_phrases.append(f"p.exp >= $form.{k}*0.75 - 0.25 AND p.exp <= $form.{k}*1.5 + 2 ")
            
        if k == "majorList":
            match_phrases.append(f"(a:Application)-[:MAJOR]->(major:Major)")
            where_phrases.append(f"major.name in $form.{k}")
            
        if k == "suitableList":
            match_phrases.append(f"(a:Application)-[:SUITABLE]->(su_role:Role)")
            where_phrases.append(f"su_role.name in $form.{k}")
        
    query_string = ""
    for line in match_phrases:
        query_string += "match " + line + "\n"
    
    for i, line in enumerate(where_phrases):
        if i == 0:
            query_string += "where " + line + "\n"
        else:
            query_string += "and " + line + "\n"
    query_string += "return distinct(id(a)) as id"
    return query_string


class CacheChromaDB:
    # This is based on the fact that these nodes are not increasing rapidly.
    def __init__(self, model, directory = 'temp'):
        self.db_cache_city = ChromaDB(data_path = f'{directory}/city.db', model=model)
        self.db_cache_role = ChromaDB(data_path = f'{directory}/role.db', model=model)
        self.db_cache_language = ChromaDB(data_path = f'{directory}/language.db', model=model)
        self.db_cache_institution = ChromaDB(data_path = f'{directory}/institution.db', model=model)
        self.db_cache_education = ChromaDB(data_path = f'{directory}/education.db', model=model)
        self.db_cache_major = ChromaDB(data_path = f'{directory}/major.db', model=model)
        self.db_cache_skills = ChromaDB(data_path = f'{directory}/skills.db', model=model)
        self.db_cache_programming = ChromaDB(data_path = f'{directory}/programming.db', model=model)
        
    # Get all the node name in the Graph and add them to the cache.
    @staticmethod
    def setup_cache_chroma(db, kg, name):
        items = kg.query(f"match (n:{name}) return n.name as name")
        items = [item['name'] for item in items]
        db.add_texts(items)
        
    def setup_cache(self, kg):
        self.setup_cache_chroma(self.db_cache_city, kg, 'City')
        self.setup_cache_chroma(self.db_cache_role, kg, 'Role')
        self.setup_cache_chroma(self.db_cache_language, kg, 'Language')
        self.setup_cache_chroma(self.db_cache_institution, kg, 'Institution')
        self.setup_cache_chroma(self.db_cache_education, kg, 'Academic')
        self.setup_cache_chroma(self.db_cache_major, kg, 'Major')
        self.setup_cache_chroma(self.db_cache_skills, kg, 'Skill')
        self.setup_cache_chroma(self.db_cache_programming, kg, 'ProgrammingLanguage')
    
    # Matching the AI generated JSON query with the database.
    def generate_query(self, request, power = 1):
        prompt = "Return the applications' id, given"

        query = dict()
        is_exp = False
        for k, v in request.items():
            if k == "languageList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    query[k] = self.db_cache_language.search_top_matches_from_list(v, threshold=0.8*min(1.05,power), top_k=2)
                    prompt += " spoken language,"   
                
            if k == "cityList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    query[k] = self.db_cache_city.search_top_matches_from_list(v, threshold=0.8*min(1.05,power), top_k=3)
                    prompt += " list of cities,"

            if k == "institutionList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    query[k] = self.db_cache_institution.search_top_matches_from_list(v, threshold=0.86*min(1.05,power), top_k=2)
                    prompt += " attending to specific institutions,"
        
            if k == "eduList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    if v == ["University"]:
                        v = ["undergraduate"]
                    query[k] = self.db_cache_education.search_top_matches_from_list(get_education_list(v), threshold=0.8*power, top_k=2)
                    prompt += " educational background,"
                    
            if k == "GPA":
                if v is not None and v >= 1:
                    try:
                        v = float(v)
                        query[k] = v*min(power,1)
                        prompt += " GPA,"
                    except:
                        pass
            
            if k == "roleList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    query[k] = self.db_cache_role.search_top_matches_from_list(v, threshold=0.7*power, top_k=math.ceil(4/(power**2)))
                    prompt += " previous role with given experience,"
            
            if k == "role_exp":
                if v is not None and v >= 0:
                    try:
                        v = float(v)
                        query[k] = v*min(power,1)  
                        is_exp = True  
                    except:
                        pass
            
            if k == "skillList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    query[k] = self.db_cache_skills.search_top_matches_from_list(v, threshold=0.6*power, top_k=math.ceil(6/(power**2)))
                    prompt += " certain skills or tech-stack,"
                    
            if k == "programmingList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    query[k] = self.db_cache_programming.search_top_matches_from_list(v, threshold=0.6*power, top_k=math.ceil(5/power))
                    prompt += " programming languages with given experience,"
            
                                
            if k == "programming_exp":
                if v is not None and v >= 0:
                    try:
                        v = float(v)
                        query[k] = v*min(power,1)
                        is_exp = True
                    except:
                        pass
                                
            if k == "majorList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    query[k] = self.db_cache_major.search_top_matches_from_list( v, threshold=0.5*power, top_k=math.ceil(8/power))
                    prompt += " study in specific major,"
            
            if k == "suitableList":
                if v is not None and len(v) > 0 and v[0] is not None:
                    query[k] = self.db_cache_role.search_top_matches_from_list(v, threshold=0.65*power, top_k=math.ceil(6/power**2))
                    prompt += " suitable roles,"                   
        print("New Query: ", query)            
                    
        prompt = prompt[:-1] + "."
        if is_exp:
            prompt += " The experience should have an upper bound and lower bound."

        query_string = json_to_cypher(query)
        
        return  prompt, query, query_string

if __name__ == "__main__":
    jd = [{'numApplication': 5, 'languageList': ['english'], 'cityList': ['Ha Noi'], 'institutionList': None, 'GPA': None, 'majorList': None, 'eduList': None, 'roleList': ['AI/ML Engineer', 'Research Scientist', 'Data Scientist', 'Software Engineer'], 'role_exp': 0, 'skillList': ['OOP', 'Python coding standards (PEP8, Google Style)', 'advanced mathematics (derivatives, integrals, multivariate data processing)', 'Git', 'REST API', 'Docker', 'image processing', 'matrix processing', 'Generative AI techniques (LLM, RAG, Diffusion)', 'Agile', 'Scrum'], 'programmingList': ['Python'], 'programming_exp': 0.5, 'suitableList': ['AI/ML Engineer', 'Research Scientist', 'Data Scientist', 'Software Engineer']}]
    print(json_to_cypher(jd[0]))