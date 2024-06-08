from .llm.llm_utils import *
import time

with open('prompt/extract_cv_format.txt', 'r') as file:
    EXTRACT_CV_FORMAT = file.read()
    
with open('prompt/extract_jd_format.txt', 'r') as file:
    EXTRACT_JD_FORMAT = file.read()
    
with open('prompt/extract_jd_no_comment.txt', 'r') as file:
    EXTRACT_JD_FORMAT_NO_COMMENT = file.read()

def normalize_cv_prompt(llm, text, dir='', translate='English', conversation = False):

    # Summarize the data and extract for knowledge graph
    
    summarize_prompt = f"""
You have the following CV data:
File name: {dir}
Data:
{text}
The CV might be corrupted, not well-formatted or contain duplicate value. The duplicate value should be ignored.
Your task is to understand the data, clean and translate the data to {translate} if it's in different language.

Then, answer the following questions:
- What is the person's name, email, phone number, address, date, city and speaking language? (if the CV is in {translate}, he/she can speak {translate})
- What is the person's education level, institution, major, GPA, graduation date?
- What is the person's certificate, achievement and award?
- What is the person's previous and current roles, years of experience and suitable roles?
- What is the person's work experience, including role, company, start date, end date and contribution?
- What is the person's project experience, including role and contribution?
- What is the person's skills, programming languages, tech stacks and proficiency level?

Here are some tips:
- For position, Intern is 0 year of experience, Fresher is 0.5 year, Junior is 1-2 years, Middle is 3-4 years and Senior is 5 years and above.
- Role is the job title and skills/tech stacks must not any specific role.
- If you don't know any information, just leave it blank. Do not makeup any information.
Keep your response as short and concise as possible. Answer in {translate}.  No chit-chat.

Only return the requirements, no chit-chat. If you don't know the answer, just response I don't know.
"""

    messages = [
        {"role":"system", "content":"You are a helpful assistant for HR department. The current recruitment date is June 2024"},
        {"role":"user", "content":summarize_prompt}
    ]
    summarize = llm(messages)
    if conversation:
        messages.append({"role":"assistant", "content":summarize})
        json_prompt= ""
    else:
        messages.pop()
        json_prompt = f"""
You are given the following CV description from file {dir}:
{summarize} 
""" 
    
    json_prompt+=f"""You must extract the person's information from the data with the following JSON format. Every content must be in {translate}, even institution name.

```json
    {EXTRACT_CV_FORMAT} 
```

Notice on information extraction:
- JSON must not contain any comment.
- Hanoi must be Ha Noi.
- MUST NOT use abbreviation (hcmc has to be Ho Chi Minh City, DS/AI must be Data Science Artificial Intelligent).
- All the summary must not include personal name.
- Do not return a null list.
- Keep the information as concise and short as possible. If the information cannot be found or unable to conclude, return null.
- The extraction data is for Knowledge Graph so the data must be as general as possible.
- Remove any redundant or duplicated information.
- Any experience of being a teaching assistance or tutoring (except the person major is closely related to teaching) should not be included in the work experience.
- Duration and year_of_exp should up to half year (.5)
- Year of experience must be calculate only if the person has used and years of experience with them in workplace or research (not include personal projects).
You will be heavily penalize if violate any of above condition.
Return the correct format of JSON only. Each key must be in double quote. Do not include any additional text or comments. No chit-chat.
"""
    
    # Checking whether the text is a CV or not
    check_prompt = f"""
You are given the following Description:
{summarize}""" + """
Is this a CV/ Resume. Answer True/False in JSON format
```json
[{"answer":${answer}]
```"""
    messages.append({"role":"user", "content":check_prompt})
    response = llm(messages)
    messages.append({"role":"assistant", "content":response})

    try:
        print('Verify CV')
        verify = get_json_from_text_response(response)
        messages.pop()
        messages.pop()
        if verify[0]['answer'] == False:   
            return False, None
    except:
        print("Error in checking CV")
        return False, None
    
    # Self-explain the data ?
    
    # JSON the data
    messages.append({"role":"user", "content":json_prompt})
    response = llm(messages)
    
    try:
        print('Extract CV')
        data = get_json_from_text_response(response)
        data = data[0]["name"]
    except:
        print("Error in converting to JSON")
        messages.append({"role":"assistant", "content":response})
        messages.append({"role":"user", "content":"The JSON format is corrupted. Check the Json format again."})
        
        response = llm(messages)
        messages.append({"role":"assistant", "content":response})
        if isinstance(get_json_from_text_response(response)[0], str):
            print("reprompt 2")
            messages.append({"role":"user", "content":"The data is in plain text. You must extract the person's information from the data with in JSON format."})
            response = llm(messages)
    return True, get_json_from_text_response(response)


def gemini_normalize_cv_prompt(llm, text, dir='', translate='English'):

    # Summarize the data and extract for knowledge graph
    summarize_prompt = f"""
You have the following CV data:
File name: {dir}
Data:
{text}
The CV might be corrupted, not well-formatted or contain duplicate value. The duplicate value should be ignored.
Your task is to understand the data, clean and translate the data to {translate} if it's in different language.

Answer the following questions:
- What is the person's name, email, phone number, address, date, city and speaking language? (if the CV is in {translate}, they can speak {translate})
- What is the person's education level, institution, major, GPA, graduation date?
- What is the person's certificate, achievement and award?
- What is the person's previous and current roles, years of experience and suitable roles? 
- What is the person's work experience, including role, company, start date, end date and contribution?
- What is the person's project experience, including role and contribution?
- What is the person's skills, programming languages, tech stacks and proficiency level?

Here are some rules you must follow:
- Role must not contain any ranking or level (e.g: Web Developer instead of Junior Web Developer)
- For roles, Intern is 0 year of experience, Fresher is 0.5 year, Junior is 1-2 years, Middle is 3-4 years and Senior is 5 years and above.
- Role is the job title and skills/tech stacks must not any specific role.
- If you don't know any information, just leave it blank. Do not makeup any information.
Keep your response as short and concise as possible. Answer in {translate}.  No chit-chat.

Only return the requirements, no chit-chat. If you don't know the answer, just response I don't know.
"""

    message = "You are a helpful assistant for HR department. The current recruitment date is June 2024.\n\n"+summarize_prompt
    messages = [
        {
            "role": "user","content": message
        }
    ]
    summarize = llm(messages)
    messages.append({"role":"assistant", "content":summarize})
    # print(summarize)
    json_prompt=f"""
Now you must extract the person's information from the data with the following JSON format. Every content must be in {translate}, even institution name.

```json
    {EXTRACT_CV_FORMAT} 
```

Notice on information extraction:
- JSON must not contain any comment.
- Hanoi must be Ha Noi.
- MUST NOT use abbreviation (hcmc has to be Ho Chi Minh City, DS/AI must be Data Science / Artificial Intelligent).
- For roles, Intern is 0 year of experience, Fresher is 0.5 year, Junior is 1-2 years, Middle is 3-4 years and Senior is 5 years and above.
- Role must not contain any ranking or level (e.g: Web Developer instead of Junior Web Developer)
- Each role must not overlap with each other. (e.g: Both Web developer and java developer instead of java web developer)
- All the summary must not include personal information.
- Do not return a null list.
- Keep the information as concise and short as possible. If the information cannot be found or unable to conclude, return null.
- The extraction data is for Knowledge Graph so the data must be as general as possible.
- Remove any redundant or duplicated information.
- Any experience of being a teaching assistance or tutoring (except the person major is closely related to teaching) should not be included in the work experience.
- Duration and year_of_exp should up to half year (.5)
- Year of experience must be calculate only if the person has used and years of experience with them in workplace or research (not include personal projects).
You will be heavily penalize if violate any of above condition.
Return the correct format of JSON only. Each key must be in double quote. Do not include any additional text or comments. No chit-chat.
"""
    
    messages.append({"role":"user", "content":json_prompt})

    
    # Self-explain the data ?
    
    # JSON the data
    response = llm(messages)
    messages.append({"role":"assistant", "content":response})
    # print(response)
    try:
        print('Extract CV')
        data = get_json_from_text_response(response)
        data = data[0]["name"]
    except:
        print("Error in converting to JSON")
        new_prompt = "The JSON format is corrupted. Check the Json format again."
        messages.append({"role":"user", "content":new_prompt})
        response = llm(messages)
    
        if isinstance(get_json_from_text_response(response)[0], str):
            print("reprompt 2")
            new_prompt +="The data is in plain text. You must extract the person's information from the data with in JSON format."
            messages.append({"role":"user", "content":new_prompt})
            response = llm(messages)
    return True, get_json_from_text_response(response)



def extract_data_prompt(llm):
    pass

def extract_data_response(response):
    pass

# Dont need

# 0: Normal Chat, 1: Ranking, 2: Analyzing JD.
def routing_ranking(llm, response):     
    rounting_prompt = f"""
You are an assistant at HR department. You are given the following request from a HR:

{response}

Previously, the user has given a list of suitable applications. Does the user has any intension to ranking?
Most of the time, the user will ask to rank after they have been given a list of suitable applications.

Answer in JSON format.
```json
[{{"answer":${{answer}}}}]
```
The value is only True or False. Only return JSON format.
"""
    messages = [
        {"role": "user", "content": rounting_prompt}
    ]
    response = llm(messages)
    result = get_json_from_text_response(response)
    for k,v in result[0].items():
        return v

    

# Routing for Job Description / CV or normal chatting
def routing_response(llm, response):
    rounting_prompt = f"""
You are an assistant at HR department. You are given the following message from a HR:
{response}
Is any of the message this related to a Job Description or is the user have any intension to looking for some applications based on their request? 
Answer in JSON format.
```json
[{{"answer":${{answer}}}}]
```
Tips:
- Most of the time, the user will ask you to find the suitable applications that fit with the request, so you are more likely to say yes.
- The value is only True or False. Only return JSON format. No chit-chat. 
"""
    messages = [
        {"role": "user", "content": rounting_prompt}
    ]
    response = llm(messages)
    result = get_json_from_text_response(response)
    for k,v in result[0].items():
        return v

def ranking_cv_prompt(llm, cvs, jd, request):
    ranking_prompt = f"""
In the final stage of recruitment process, you are given the following CV detail with their id:
{cvs}
And here is the Job Description:
{jd}
Here is the request from HR:
{request}
Based on the candidate CV and the Job Description,you have to rank the CVs that fit with JD and have the most relevant experience.
Some criteria for ranking:
- Current location: If the job only recruit in a specific location, the closer the candidate's location, the higher the rank. If the job is remote or having no restriction on location, the location is not important.
- Work experience: The more experience, the higher the rank. However, some candidates might overqualified (e.g: 10 years of experience for a junior position), so make sure to consider the job level. If the applicant has more than double the experience required, that should be a heavy penalty. 
- Skills, tech stacks and/or programming language: The more relevant skills, the higher the rank. (e.g: Natural Language Processing is more relevant than ETL Pipeline for a Data Science position. Skills and tech stacks must not contain programming language or library)
- Education: The higher the education level, the higher the rank.
- Certificate, achievement and award: The higher the value, the higher the rank. (e.g A national award is more valuable than local awards)
- And any relevant information that you think is important.
Explain your ranking base on the criteria and return the ranking in JSON format. 
```json
[
    {{
        "id": 1,
        "rank": 1,
        "explanation": "The candidate has 5 years of experience in Data Science, which is the most relevant experience for the job. The candidate also has a Master degree in Data Science and has a national award in Data Science competition. The candidate has a good proficiency in Python and R, which is the most relevant programming language for the job."
    }},
    {{
        "id": 2,
        "rank": 2,
        "explanation": "The candidate has 3 years of experience in Data Science, which is the second most relevant experience for the job. The candidate also has a Bachelor degree in Data Science and has a local award in Data Science competition. The candidate has a good proficiency in Python and R, which is the most relevant programming language for the job."
    }}
]
```
"""
    messages = [
        {"role":"system", "content":"You are a helpful assistant for HR department. The current recruitment date is May 2024"},
        {"role":"user", "content":ranking_prompt}
    ]
    response = llm(messages)
    # print(response)
    messages.append({"role":"assistant", "content":response})
    try:
        ranking = get_json_from_text_response(response)
        first_candidate = ranking[0]['id']
    except:
        print("Error in ranking")
        messages.append({"role":"user", "content":"The JSON format is corrupted. Check the Json format again."})
        response = llm(messages)
        ranking = get_json_from_text_response(response)
    return ranking


def select_suitable_cv_prompt(llm, cvs, jd, num_selection):
    picking_cvs = ''
    for cv in cvs:
        picking_cvs += f"**ID: {cv['id']}**\n{cv['text']}\n\n"
    
    select_prompt = f"""
You are given the following CV detail with their id:
{picking_cvs}
And here is the Job Description:
{jd}
You are requested to select the {num_selection} most suitable CVs that fit with JD and have the most relevant experience. The number of CVs that you need to select is {num_selection}.

Return your selection in JSON format.
```json
[
    {{
        "selected_ids": [1, 2, 3]
    }}
]
```
"""
    messages = [
      {
        "role": "system","content":"You are a helpful assistant for HR department. The current recruitment date is June 2024"
      },
      {
        "role": "user","content":select_prompt
      }
    ]
    
    response = llm(messages)
    messages.append({"role":"assistant", "content":response})
    
    # Check the output format
    try:
        ans = get_json_from_text_response(response)
        if isinstance(ans,list):
            ranking = ans[0]['selected_ids']
        else:
            ranking = ans['selected_ids']

    except:
        print("Error in ranking")
        messages.append({"role":"user", "content":"The JSON format is corrupted. Check the Json format again."})
        response = llm(messages)
        
        ans = get_json_from_text_response(response)
        if isinstance(ans,list):
            ranking = ans[0]['selected_ids']
        else:
            ranking = ans['selected_ids']
    return ranking
    
# From job requirements to JSON
def extract_job_requirements_prompt(llm, text, translate='English', lm = None):
    
    extract_prompt = f"""
Your task is to understand and extract the requirements from the following text:
{text}
Try to normalize it and give short answer on the following questions:
- How many applications are required for the job? all match, specific number or not mentioned.
- What is the location, academic level, institution, GPA, speaking language does the job require? If the academic level is not mentioned, the candidate can just be an undergraduate.
- What is the roles, skills, programming languages and tech stacks does the job require? What is the experience level required for each of them?
- Is there any other requirements that the job requires?
- What is the benefit for the candidate if they get the job?
- What is the suitable roles for this job? Suitable roles might have roles similar but not required in the job description. If the actual role is not mentioned, Skip.

Some tips:
- For position, Intern is 0 year of experience, Fresher is 0.5 year, Junior is 1-2 years, Middle is 3-4 years and Senior is 5 years and above.
- Role is the job title and skills/tech stacks must not any specific role
- Some time the requirement are not focusing on jobs, so only answer the question about jobs that is clearly mentioned in the text.
- If the role or suitable role is not clearly mentioned, leave it blank.
- If you don't know any information, just leave it blank. Do not makeup any information.
Keep your response as short and concise as possible. Answer in {translate}.  No chit-chat.
"""
    
    # Extract the job requirements
    messages = [
        {"role":"system", "content":"You are a helpful assistant for HR department, specialize in normalizing job description. You must process everything in English. The current recruitment date is May 2024"},
        {"role":"user", "content":extract_prompt}
    ]
    
    jd_extraction = llm(messages)
    messages.append({"role":"assistant", "content":jd_extraction})

    # Summarize the job requirements
    summarize_prompt = f"""
You are given a Job requirements from the following text:
{jd_extraction}
Summarize the text at maximum 100 words in {translate}. Only return the summary, no chit-chat.
"""

    summarize_message = [
        {"role":"system", "content":"You are a helpful assistant for HR department, specialize in normalizing job description. You must process everything in English."},
        {"role":"user", "content":summarize_prompt}
    ]    

    if lm is not None:
        jd_summarize = lm(summarize_message)
    else:
        jd_summarize = llm(summarize_message)
    
    # print(jd_extraction)
    # For Vietnamese Market only
    json_prompt = f"""
{jd_extraction}
Please extract the job requirements from the text with the following JSON format:
```json
{EXTRACT_JD_FORMAT}
```
Some tips for the information extraction:
- `roleList` is the job title and `skillList` must not contain any value in `roleList`.
- For position, Intern is 0 year of experience, Fresher is 0.5 year, Junior is 1-2 years, Middle is 3-4 years and Senior is 5 years and above.
- If you cannot find the information, return null.
- Suitable role is only for jobs that require less than 2 years of experience.
- If number of application is not mentioned, return 3. Only if the request specially asks for find all match, return -1.
- Do not use abbreviation (hcmc has to be Ho Chi Minh City)
- If role is not mentioned, the suitable role must be left blank.
- Keep the information as concise and short as possible. 
- Language should not include Vietnamese.
- Hanoi must be Ha Noi.
- For internship, the experience value must be 0.
- If there are 2-3 requirements of experience at the same time, return mean value (e.g Junior/Middle is 2.5 yoe, Fresher/Junior is 1 yoe). If there are more than 3, return null.
- If the experience of any role/skills is not mentioned, the value must be null.

Return the correct format of JSON only. Each key must be in double quote. Do not include any additional text or comments. No chit-chat.
You can return multiple job requirements more than 1 role is recruited, but each role must have significant differences in the requirements. (e.g :Year of experience) Each role must be a different JD in a separate object in a list.
""" 
    messages.append({"role":"user", "content":json_prompt})
    response = llm(messages)

    jd = get_json_from_text_response(response)
    for i in range(len(jd)):
        if 'numApplication' not in jd[i] or jd[i]['numApplication'] is None:
            jd[i]['numApplication'] = 3
        if 'cityList' in jd[i] and jd[i]['cityList'] is not None and 'numApplication' in jd[i]:
            if len(jd[i]['cityList']) >1 and jd[i]['numApplication'] ==3:
                jd[i]['numApplication'] = 5
    return jd_extraction, jd_summarize, jd