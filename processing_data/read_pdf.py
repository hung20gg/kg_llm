from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
import os
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

import easyocr
from pdf2image import convert_from_path
import numpy as np
from PIL import Image

reader = easyocr.Reader(['en', 'vi'], gpu=True)

def pdf_to_images(pdf_path: str):

    # Convert PDF to images
    images = convert_from_path(pdf_path)

    return images

def ocr_images(images):
    """
    Perform OCR on a list of images using EasyOCR.

    Parameters:
        image_paths (List[str]): List of image file paths.
        lang (str): Language to use for OCR. Default is 'en'.

    Returns:
        List[str]: List of extracted text from each image.
    """
    # Initialize EasyOCR reader with CUDA support
    
    texts = []
    for image in images:
        image = np.array(image)
        # Perform OCR on the image
        result = reader.readtext(image)
        # Concatenate text results
        text = '\n'.join([item[1] for item in result])
        texts.append(text)

    return texts

def ocr_pdf_with_easyocr(pdf_path: str):

    # Convert PDF to images
    image_paths = pdf_to_images(pdf_path)
    # Perform OCR on images
    texts = ocr_images(image_paths)
    return texts

def process_pdf_batch(files, is_split = False, is_save = True):

        batch_docs = []
        return_docs = []
        for pdf_file_path in files:
            if pdf_file_path.endswith('.pdf'):
                pdf_loader = PyPDFLoader(pdf_file_path)
                contents = pdf_loader.load()
                if is_split:
                    batch_docs.extend(pdf_loader.load_and_split(
                        text_splitter=RecursiveCharacterTextSplitter(
                            chunk_size=int(os.environ.get("CHUNK_SIZE", 1000)),
                            chunk_overlap=int(os.environ.get("CHUNK_OVERLAP", 10)),
                        )
                    ))
                    
                else:
                    batch_docs.extend(contents)
                
                # print(content)
                texts = ''
                for content in contents:
                    texts += content.page_content + '\n'
                    
                if len(texts.strip()) <10: # No text found
                    texts = ocr_pdf_with_easyocr(pdf_file_path)
                    texts = '\n'.join(texts)
                return_docs.append(texts)
                if is_save:
                    save_path = pdf_file_path.replace('raw', 'processed')   
                    f = open(save_path.replace('.pdf', '.txt'), 'w', encoding='utf-8')
                    f.write(texts)
                    f.close()
            
            else:
                try:
                    image = Image.open(pdf_file_path)
                    result = reader.readtext(image)
                    texts = '\n'.join([item[1] for item in result])
                    file_name = pdf_file_path.split('/')[-1]
                    file_format = file_name.split('.')[-1]
                    save_path = pdf_file_path.replace('raw', 'processed').replace(file_format, 'txt')
                    if is_save:
                        f = open(save_path, 'w', encoding='utf-8')
                        f.write(texts)
                        f.close()
                    return_docs.append(texts)
                except:
                    print(f"Cannot process {pdf_file_path}")
        return return_docs

def load_docs(root_directory: str, is_split: bool = False):

    # Set the batch size (number of files to process in each batch)
    batch_size = 10

    # Initialize an empty list to store loaded documents
    docs = []

    # Function to process a batch of PDF files
    

    # Get the list of PDF files to process
    pdf_files_to_process = []
    for root, dirs, files in os.walk(root_directory):
        pdf_files_to_process.extend([os.path.join(root, file) for file in files if file.lower().endswith(".pdf")])

    # Create a ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor() as executor:
        total_files = len(pdf_files_to_process)
        processed_files = 0

        # Iterate through the PDF files in batches
        for i in tqdm(range(0, total_files, batch_size)):
            batch = pdf_files_to_process[i:i+batch_size]
            batch_docs = list(executor.map(process_pdf_batch, [batch]))
            for batch_result in batch_docs:
                docs.extend(batch_result)
                processed_files += len(batch)
    return docs


if __name__ == "__main__":
    # Load the PDF documents from the specified directory
    
    # for dir in os.listdir('data/raw'):
    #     print(dir)
    docs = load_docs(f"data/raw/", is_split=False)
    print(f"Loaded {len(docs)} documents")
    # Save the loaded documents to a file
    # print(docs)
    
    # with open(f"data/processed/{dir}.txt", "w") as f:
    #     for doc in docs:
    #         f.write(str(doc))
    #         f.write("\n")
    # print(f"Saved the loaded documents to data/processed/{dir}.txt")