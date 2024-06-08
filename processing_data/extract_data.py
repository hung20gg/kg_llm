from agent.llm.llm_utils import *
from agent.agent_prompt import *
import os
import json
from tqdm import tqdm
import multiprocessing as mp
from agent import BedRockLLMs, Gemini

def fast_clean_and_jsonify_data(llm_agrs, raw_file = [], dir = None, end_with = '.txt', batch_size = 8, process = 10):
    texts = raw_file
    pdf_dir =[]
    json_dir = []
    json_data = []
    
    done_dirs = set()
    done_dir = dir.replace('/processed/', '/clean4.0/')
    for file in os.listdir(done_dir):
        if file.endswith('.json'):
            temp = file.replace('.json', '.txt').replace('/clean4.0/', '/processed/')   
            print(temp)
            done_dirs.add(temp)

    if isinstance(dir, str):
        for i, file in enumerate(os.listdir(dir)):
            if file.endswith(end_with):
                if file in done_dirs:
                    continue
                path = os.path.join(dir, file)
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                texts.append(text)
                pdf_dir.append(path)

    num_files = len(texts)
    print(f"Total files: {num_files}")
    dataset = []
    dataset_dir = []
    
    for i in range(0, num_files, batch_size):
        batch = texts[i:i+batch_size]
        batch_dir = pdf_dir[i:i+batch_size]
        
        dataset.append(batch)
        dataset_dir.append(batch_dir)
    

    
    with mp.Pool(process) as pool:
        results = pool.starmap(clean_and_jsonify_data, [(llm_agrs, text, dir) for text, dir in zip(dataset, dataset_dir)])
    for result in results:
        check, data = result
        if check:
            json_data.extend(data)
            json_dir.extend(check)
    


def clean_and_jsonify_data(llm, raw_file = [], dir = None, target = 'cv', end_with = '.txt'):
    
    llm_type = 'gemini'
    print("Start cleaning and converting data")
    if isinstance(llm, dict):
        # llm = Gemini()
        llm_type = 'bedrock'
        llm = BedRockLLMs(**llm)
    if isinstance(llm, str):
        llm = Gemini()
    texts = raw_file
    pdf_dir = []
    json_data = []
    json_dir = []
    num_files = len(texts)
    
    save_paths =[]
    err_paths = []
    print(llm_type)

    # Check if the dir is a list of paths
    if isinstance(dir, str):
        num_files = len(os.listdir(dir))
        for i, file in enumerate(os.listdir(dir)):
            if file.endswith(end_with):
                path = os.path.join(dir, file)
                save_path = path.replace('/processed/', '/clean4.0/').replace('.txt', '.json')
                err_path = path.replace('/processed/', '/error/')
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    
                texts.append(text)
                pdf_dir.append(path)
                save_paths.append(save_path)
                err_paths.append(err_path)
                
    if isinstance(dir, list):
        for path in dir:
            save_path = path.replace('/processed/', '/clean4.0/').replace('.txt', '.json')
            err_path = path.replace('/processed/', '/error/')
            
            pdf_dir.append(path)
            save_paths.append(save_path)
            err_paths.append(err_path)
                
    for i, text in enumerate(texts):        
        if target == 'cv':
            if llm_type == 'gemini':
                check, data = gemini_normalize_cv_prompt(llm, text, dir = pdf_dir[i])
            else:
                check, data = normalize_cv_prompt(llm, text, dir = pdf_dir[i])
        else:
            check, data,_ = extract_job_requirements_prompt(llm, text, dir = pdf_dir[i])
            
        # Save file if dir exists
        try:
            # Test if the data is in JSON format
            test = json.dumps(data, indent=4)
            
            json_data.append(data[0])
            json_dir.append(pdf_dir[i])
            if check and dir is not None:
                
                # Save file if dir exists
                with open(save_paths[i].replace('.txt', '.json'), 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                print(f"Saved ({i+1}/{num_files}) {save_paths[i]}")
        except Exception as e:
            print(f"Error ({i+1}/{num_files}) in {pdf_dir[i]}")
            print(e)
            with open(err_paths[i], 'w', encoding='utf-8') as f:
                f.write(str(data))
        
    return json_data, json_dir
                
            
