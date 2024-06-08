def fix_education(edu):
    if edu["institution"] is not None:
        edu["institution"] = edu["institution"].lower().split(',')[0]
    if edu["academic_level"] is not None:
        edu["academic_level"] = edu["academic_level"].lower()
        edu["academic_level"] = edu["academic_level"].replace('\'s', '')
        edu["academic_level"] = edu["academic_level"].strip()
        
    if 'major' in edu and edu['major'] is not None:
        major = edu['major']
        
        tags = [',','/','(']
        for tag in tags:
            if tag in major:
                major = major.split(tag)[0]
        
        major = major.lower()
        major = major.replace('specialist', '')
        major = major.replace('executive', '')
        major = major.replace('scientist', 'science')
        major = major.replace('analysis', 'analyst')
        major = major.replace('fullstack', '')
        major = major.replace('engineering', 'engineer')
        major = major.strip()   
        
        if major != '':
            edu['major'] = major
        else:
            del edu['major']
    return edu

def fix_roles(roles):
    new_roles = []
    roles_exp = dict()
    for role in roles:
        if  'role' in role and role['role'] is not None:
            name = role['role'].lower()
            name = name.replace('specialist', '').replace('intern','').replace('fresher','').replace('junior','').replace('senior','').replace('middle','')
            if 'year_of_exp' in role and role['year_of_exp'] is not None:
                exp = role['year_of_exp']
            else:
                exp = 0
            if name in roles_exp:
                roles_exp[name] = max(roles_exp[name], exp)
            else:
                roles_exp[name] = exp
    for name in roles_exp:
        new_roles.append({'role': name, 'year_of_exp': roles_exp[name]})
            
    return new_roles

# Recursive function to collect all values in JSON -> string
def collect_values(data):
    values = []
    def _collect(data):
        if isinstance(data, dict):
            for key, value in data.items():
                _collect(value)
        elif isinstance(data, list):
            for item in data:
                _collect(item)
        else:
            values.append(str(data))
    
    _collect(data)
    return ' '.join(values)



def get_summary_data(json_data, key):
    if key in json_data and json_data[key] is not None:
        return collect_values(json_data[key])
    return ''

# Fixing work experience format
def fix_work(work):
    if not work['company'] or work['company'] is None:
        return False, {}
    work['company'] = work['company'].lower()
    
    if 'duration' not in work or work['duration'] is None:
        work['duration'] = 0
    return True, work

# Fixing skills format
def fix_skills(skills):
    new_skills = []
    while len(skills)>0:
        skill = skills.pop()
        if isinstance(skill, str):
            skill = {'name': skill, 'year_of_exp': 0.25}

        if 'year_of_exp' not in skill or skill['year_of_exp'] is None:
            skill['year_of_exp'] = 0.25
            
        seps = ['/',',','-','and']
        flag = True
        for sep in seps:
            if sep in skill['name']:
                flag = False
                newskill = skill['name'].split(sep)
                for sk in newskill:
                    skills.append({'name': sk})
                
        if flag:
            skill['name'] = skill['name'].split('(')[0].lower().strip()
            new_skills.append(skill)
    return new_skills

# Fixing programming languages format
def fix_language(pls):
    new_pls = []
    while len(pls)>0:
        pl = pls.pop()
        if pl is None or pl['programming'] is None:
            return []
        if '/' in pl['programming']:
            newlang = pl['programming'].split('/')
            for lang in newlang:
                pls.append({'programming': lang, 'year_of_exp':pl['year_of_exp']})
        elif ',' in pl['programming']:
            newlang = pl['programming'].split(',')
            for lang in newlang:
                pls.append({'programming': lang, 'year_of_exp':pl['year_of_exp']})
        elif '-' in pl['programming']:
            newlang = pl['programming'].split('-')
            for lang in newlang:
                pls.append({'programming': lang, 'year_of_exp':pl['year_of_exp']})
        elif 'and' in pl['programming']:
            newlang = pl['programming'].split('and')
            for lang in newlang:
                pls.append({'programming': lang, 'year_of_exp':pl['year_of_exp']})        
        else:
            pl['programming'] = pl['programming'].split('(')[0].lower().strip()
            if pl['programming'][-2:]=='js':
                if pl['programming'][-3]!='.':
                    pl['programming'] = pl['programming'][:-2]+'.'+pl['programming'][-2:]
                pl['programming'] = pl['programming'].replace('.js','').strip()
            new_pls.append(pl)
    return new_pls

def fetch_application_details(kg, id):
    # query = """
    #    MATCH (a:Application)-[:SKILL]->(s:Skill)
    #    MATCH (a)-[:STUDY]->(i:Institution)
    #    MATCH (a)-[edu:ACADEMIC]->(ac:Academic)
    #    MATCH (a)-[mj: MAJOR]->(m:Major)
    #    MATCH (a)-[:SUITABLE]->(r:Role)
    #    MATCH (a)-[:LIVE_IN]->(ci:City)
    #    WHERE id(a) = $id
    #    RETURN 
    #    id(a),collect(distinct {name: s.name}) as skills,
    #    collect(distinct {name: i.name}) as institutions, 
    #    collect(distinct {name: ac.name, gpa: edu.GPA, is_gpa:edu.is_GPA}) as academics, 
    #    collect(distinct {name: m.name, level: mj.level}) as majors, 
    #    collect(distinct {name: r.name}) as suitable_roles, 
    #    collect(distinct {name: ci.name}) as cities
    # """
    query_city = """
    MATCH (a:Application)-[:LIVE_IN]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name}) as cities
    """
    
    query_skill = """
    MATCH (a:Application)-[rela:SKILL]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name}) as skills
    """
    
    query_major = """
    MATCH (a:Application)-[rela:MAJOR]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name, level: rela.level}) as majors
    """
    
    query_institution = """
    MATCH (a:Application)-[rela:STUDY]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name}) as institutions
    """
    
    query_academic = """
    MATCH (a:Application)-[rela:ACADEMIC]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name, gpa: rela.GPA, is_gpa:rela.is_GPA}) as academics
    """
    
    query_suitable_role = """
    MATCH (a:Application)-[rela:SUITABLE]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name}) as suitable_roles
    """
    
    query_role = """
    MATCH (a:Application)-[rela:ROLE]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name, exp:rela.exp}) as roles
    """
    query_company = """
    MATCH (a:Application)-[rela:WORK]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name, duration:rela.duration}) as companies
    """
    query_programming_language = """
    MATCH (a:Application)-[rela:PROGRAMMING]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct {name: node.name, exp:rela.exp}) as programming_languages
    """
    query_language = """
    MATCH (a:Application)-[rela:SPEAK]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct node) as languages
    """
    query_certification = """
    MATCH (a:Application)-[rela:CERTIFICATION]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct node) as certifications
    """
    query_award = """
    MATCH (a:Application)-[rela:AWARD]->(node)
    WHERE id(a) = $id
    RETURN id(a), collect(distinct node) as awards
    """
    
    result = dict()
    result_city = kg.query(query_city, params={"id": id})
    result_skill = kg.query(query_skill
                            , params={"id": id})
    result_major = kg.query(query_major, params={"id": id})
    result_institution = kg.query(query_institution, params={"id": id})
    result_academic = kg.query(query_academic, params={"id": id})
    result_suitable_role = kg.query(query_suitable_role, params={"id": id})
    
    result_role = kg.query(query_role, params={"id": id})
    result_company = kg.query(query_company, params={"id": id})
    result_programming_language = kg.query(query_programming_language, params={"id": id})
    result_language = kg.query(query_language, params={"id": id})
    result_certification = kg.query(query_certification, params={"id": id})
    result_award = kg.query(query_award, params={"id": id})
    
    if len(result_city)>0:
        result["cities"] = result_city[0]["cities"]
    if len(result_skill)>0:
        result["skills"] = result_skill[0]["skills"]
    if len(result_major)>0:
        result["majors"] = result_major[0]["majors"]
    if len(result_institution)>0:
        result["institutions"] = result_institution[0]["institutions"]
    if len(result_academic)>0:
        result["academics"] = result_academic[0]["academics"]
    if len(result_suitable_role)>0:
        result["suitable_roles"] = result_suitable_role[0]["suitable_roles"]
    
    if len(result_role)>0:
        result["roles"] = result_role[0]["roles"]
    if len(result_company)>0:
        result["companies"] = result_company[0]["companies"]
    if len(result_programming_language)>0:
        result["programming_languages"] = result_programming_language[0]["programming_languages"]
    if len(result_language)>0:
        result["languages"] = result_language[0]["languages"]
    if len(result_certification)>0:
        result["certifications"] = result_certification[0]["certifications"]
    if len(result_award)>0:
        result["awards"] = result_award[0]["awards"]

    return result


def format_application_details(details):
    graph_text = ""
    
    if "languages" in details:
        graph_text += "Languages:\n"
        languages = "- "+"\n- ".join([language["name"] for language in details["languages"]])
        graph_text += languages + "\n"
    
    try:
        if "majors" in details:
            graph_text += "Majors:\n"
            majors = "- "+"\n- ".join([f"{major['level']}, {major['name']}, {institution['name']}, (GPA: {academic['gpa']})" for major, institution, academic in zip(details["majors"],details["institutions"],details["academics"])])
            
            graph_text += majors + "\n"
    except:
        pass
        
    if "roles" not in details:
        graph_text += "Suitable roles:\n"
        suitable_roles = "- "+"\n- ".join([role["name"] for role in details["suitable_roles"]])
        graph_text += suitable_roles + "\n"
        
    try:
        if "companies" in details:
            graph_text += "Work:\n"
            companies = "- "+"\n- ".join([f"{company['name']} ({company['duration']} years)" for company in details["companies"]])
            graph_text += companies + "\n"
    except:
        pass
        
    if "roles" in details:
        graph_text += "Roles:\n"
        roles = "- "+"\n- ".join([f"{role['name']} ({role['exp']} years)" for role in details["roles"]])
        graph_text += roles + "\n"

    if "skills" in details:
        graph_text += "Skills:\n"
        skills = "- "+"\n- ".join([skill["name"] for skill in details["skills"]])
        graph_text += skills + "\n"
    
    if "programming_languages" in details:
        graph_text += "Programming languages:\n"
        programming_languages = "- "+"\n- ".join([f"{pl['name']} ({pl['exp']} years)" for pl in details["programming_languages"]])
        graph_text += programming_languages + "\n"
    
    if "cities" in details:
        graph_text += "Cities:\n"
        cities = "- "+"\n- ".join([city["name"] for city in details["cities"]])
        graph_text += cities + "\n"
    
    if "certifications" in details:
        graph_text += "Certifications:\n"
        certifications = "- "+"\n- ".join([cert["name"] for cert in details["certifications"]])
        graph_text += certifications + "\n"
    
    if "awards" in details:
        graph_text += "Awards:\n"
        awards = "- "+"\n- ".join([award["name"] for award in details["awards"]])
        graph_text += awards + "\n"
    
    return graph_text
    

def graph_to_text(kg, id):
    details = fetch_application_details(kg, id)
    return format_application_details(details)
