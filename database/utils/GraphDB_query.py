CREATE_USER = """
    CREATE (n:Application)
        SET n.name = $formInfoParam.name
        SET n.email = $formInfoParam.email
        SET n.phone = $formInfoParam.phone
        SET n.address = $formInfoParam.address
        SET n.summary = $formInfoParam.summary
        SET n.work_summary = $formInfoParam.work_summary
        SET n.education_summary = $formInfoParam.education_summary
        SET n.project_summary = $formInfoParam.project_summary
        SET n.birth = $formInfoParam.birth_year
        SET n.file = $formInfoParam.file
    return id(n) as id
"""
MATCH_CITY = """
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (l:City {name: $city})
        ON CREATE SET l.name = $city
    CREATE (n)-[:LIVE_IN]->(l)
"""
MATCH_LANGUAGE = """
    
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (l:Language {name: $language})
        ON CREATE SET l.name = $language
    CREATE (n)-[:SPEAK]->(l)
"""

MATCH_INSTITUTION = """
    
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (i:Institution {name: $institution})
        ON CREATE SET i.name = $institution
    CREATE (n)-[:STUDY]->(i)
"""

MATCH_ACADEMIC = """
    
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (a:Academic {name: $academic})
        ON CREATE SET a.name = $academic
    CREATE (n)-[:ACADEMIC {GPA: $GPA, is_GPA: $is_GPA}]->(a)
"""

MATCH_MAJOR = """
    
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (m:Major {name: $major})
        ON CREATE SET m.name = $major
    CREATE (n)-[:MAJOR {level: $academic}]->(m)
"""

MATCH_SUITABLE_ROLE = """
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (r:Role {name: $role})
        ON CREATE SET r.name = $role
    CREATE (n)-[:SUITABLE]->(r)
"""

MATCH_WORK_EXPERIENCE = """
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (c:Company {name: $work.company})
        ON CREATE SET c.name = $work.company
    CREATE (n)-[:WORK {duration: $work.duration}]->(c)
"""

MATCH_ROLE = """
    
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (r:Role {name: $role.role})
        ON CREATE SET r.name = $role.role
    CREATE (n)-[:ROLE {exp:$role.year_of_exp}]->(r)
"""

MATCH_SKILL = """
    
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (s:Skill {name: $skill})
        ON CREATE SET s.name = $skill
    CREATE (n)-[:SKILL]->(s)
"""

MATCH_PROGRAMMING_LANGUAGE = """
    
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (p:ProgrammingLanguage {name: $programming_language.programming})
        ON CREATE SET p.name = $programming_language.programming
    CREATE (n)-[:PROGRAMMING {exp:$programming_language.year_of_exp}]->(p)
"""

MATCH_TECH_STACK = """
    
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (t:Skill {name: $tech_stack})
        ON CREATE SET t.name = $tech_stack
    CREATE (n)-[:SKILL]->(t)
"""

MATCH_CERTIFICATION = """
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (c:Certification {name: $certification})
        ON CREATE SET c.name = $certification
    CREATE (n)-[:CERTIFICATION]->(c)
"""

MATCH_AWARD = """
    MATCH (n:Application)
    WHERE id(n) = $id
    MERGE (a:Award {name: $award})
    ON CREATE SET a.name = $award
    CREATE (n)-[:AWARD]->(a)
"""

APPLICATION_QUERY = """
    MATCH (a:Application)-[:SKILL]->(s:Skill)
    MATCH (a:Application)-[:SPEAK]->(l:Language)
    MATCH (a:Application)-[:STUDY]->(i:Institution)
    MATCH (a:Application)-[:ACADEMIC]->(a:Academic)
    MATCH (a:Application)-[:MAJOR]->(m:Major)
    MATCH (a:Application)-[:SUITABLE]->(sr:Role)
    MATCH (a:Application)-[:WORK]->(com:Company)
    MATCH (a:Application)-[:ROLE]->(r:Role)
    MATCH (a:Application)-[:PROGRAMMING]->(p:ProgrammingLanguage)
    MATCH (a:Application)-[:LIVE_IN]->(c:City)
    WHERE id(a) = $id
    RETURN a, s, l, i, a, m, sr, com, r, p, c
"""