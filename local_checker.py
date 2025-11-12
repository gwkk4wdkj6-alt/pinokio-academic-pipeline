import os
import docx
import PyPDF2
import sys
import nltk

BIBLIOGRAPHY_MARKERS = [
    'Referencias:', 'Referencias',
    'Bibliografía:', 'Bibliografía',
    'References:', 'References'
]

def download_nltk_resource(resource):
    try:
        nltk.data.find(resource)
    except LookupError:
        print(f"Descargando el recurso '{resource.split('/')[-1]}' de NLTK...")
        nltk.download(resource.split('/')[-1], quiet=True)

download_nltk_resource('tokenizers/punkt')

def extract_text(filepath):
    print(f"Extrayendo texto de: {filepath}")
    _, file_extension = os.path.splitext(filepath)
    file_extension = file_extension.lower()
    try:
        if file_extension == '.docx':
            doc = docx.Document(filepath)
            return '\n'.join([para.text for para in doc.paragraphs])
        elif file_extension == '.pdf':
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return '\n'.join([page.extract_text() for page in pdf_reader.pages])
        elif file_extension == '.txt':
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        else: return None
    except Exception as e:
        print(f"Error al leer el archivo {file_extension.upper()}: {e}")
        return None

def remove_bibliography(text):
    text_lower = text.lower()
    for marker in BIBLIOGRAPHY_MARKERS:
        marker_lower = marker.lower()
        if marker_lower in text_lower:
            start_index = text_lower.find(marker_lower)
            return text[:start_index]
    return text


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 local_checker_clean.py \"/ruta/al/archivo.txt\"")
        sys.exit(1)
    file_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(file_path):
        print(f"Error: El archivo no se encuentra en la ruta: {file_path}")
        sys.exit(1)
    text_content = extract_text(file_path)
    if text_content:
        print("\nTexto extraído con éxito. Eliminando bibliografía...")
        cleaned_text = remove_bibliography(text_content)
        print("\n--- Texto Limpio (sin bibliografía) ---")
        print(cleaned_text)
        print("\n--- Fin del Texto Limpio ---")
    else:
        print("No se pudo extraer contenido del archivo para analizar.")
