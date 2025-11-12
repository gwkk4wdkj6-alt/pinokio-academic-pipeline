#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import json
import re
import nltk
import docx
from PyPDF2 import PdfReader
import textwrap

# --- CONFIGURACIÓN GLOBAL ---
# Rutas a los entornos virtuales, obtenidas del CONFIG.txt
SA_VENV_PATH = "/Volumes/MainDrive/miniforge3/envs/sa-detector/bin/python"
VENV_CHECKER_PATH = "/Volumes/MainDrive/venv_checker/bin/python" # Para NLTK y otros

MODELS = {
    "superannotate": "SuperAnnotate/ai-detector"
}

BIBLIOGRAPHY_MARKERS = [
    "Referencias:", "Referencias",
    "Bibliografía:", "Bibliografía",
]

PROBLEM_THRESHOLD = 30.0
SENTENCE_DELIMITER = "|||---|||"

# --- FUNCIONES DE UTILIDAD Y EXTRACCIÓN ---

def download_nltk_resource(resource, resource_name):
    try:
        nltk.data.find(resource)
    except LookupError:
        print(f"Descargando recurso de NLTK '{resource_name}'...")
        nltk.download(resource_name, quiet=True)

def extract_text(filepath):
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    try:
        if ext == '.docx':
            doc = docx.Document(filepath)
            return '\n'.join([p.text for p in doc.paragraphs])
        elif ext == '.pdf':
            with open(filepath, 'rb') as f:
                reader = PdfReader(f)
                return '\n'.join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif ext == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"Error: Formato '{ext}' no soportado.")
            return None
    except Exception as e:
        print(f"Error leyendo el archivo: {e}")
        return None

def remove_bibliography(text):
    for marker in BIBLIOGRAPHY_MARKERS:
        if marker.lower() in text.lower():
            start_index = text.lower().find(marker.lower())
            return text[:start_index]
    return text

# --- FUNCIÓN DE ANÁLISIS POR MODELO (SUBPROCESO) ---

def analyze_sentences_superannotate(sentences):
    model_id = MODELS["superannotate"]
    python_executable = SA_VENV_PATH

    # Código que se ejecutará en el subproceso para SuperAnnotate
    runner_code = textwrap.dedent(f'''
        import sys
        import json
        import torch
        import torch.nn.functional as F
        from generated_text_detector.utils.model.roberta_classifier import RobertaClassifier
        from generated_text_detector.utils.preprocessing import preprocessing_text
        from transformers import AutoTokenizer

        def run_analysis(sentences_str, model_id):
            try:
                model = RobertaClassifier.from_pretrained(model_id)
                tokenizer = AutoTokenizer.from_pretrained(model_id)
                model.eval()
                
                sentences = sentences_str.split("{SENTENCE_DELIMITER}")
                scores = []
                
                with torch.no_grad():
                    for sentence in sentences:
                        if not sentence.strip():
                            scores.append(0.0)
                            continue
                        
                        preprocessed_text = preprocessing_text(sentence)
                        tokens = tokenizer.encode_plus(
                            preprocessed_text,
                            add_special_tokens=True,
                            max_length=512,
                            padding='longest',
                            truncation=True,
                            return_token_type_ids=True,
                            return_tensors="pt"
                        )
                        
                        _, logits = model(**tokens)
                        probability = F.sigmoid(logits).squeeze(1).item()
                        scores.append(probability * 100)
                
                print(json.dumps(scores))

            except Exception as e:
                error_message = f"ERROR: {{str(e)}}"
                print(json.dumps([error_message] * len(sentences_str.split("{SENTENCE_DELIMITER}"))), file=sys.stderr)
                sys.exit(1)

        if __name__ == "__main__":
            run_analysis(sys.argv[1], "{model_id}")
    ''')

    if not os.path.exists(python_executable):
        print(f"ADVERTENCIA: No se encontró el entorno para SuperAnnotate en {python_executable}")
        return [-1.0] * len(sentences)

    try:
        sentences_str = SENTENCE_DELIMITER.join(sentences)
        process = subprocess.run(
            [python_executable, "-c", runner_code, sentences_str],
            capture_output=True, text=True, timeout=300
        )
        
        if process.returncode != 0:
            sys.stderr.write(f"Error en subproceso de SuperAnnotate:\n{process.stderr}\n")
            return [f"ERROR_SUBPROCESS"] * len(sentences)

        return json.loads(process.stdout)

    except Exception as e:
        return [f"ERROR: {e}"] * len(sentences)

# --- FUNCIÓN PRINCIPAL ---

def main(filepath):
    print("Iniciando micro-análisis de frases (v9 Human-Centric)...")
    
    text = extract_text(filepath)
    if not text: return
        
    text = remove_bibliography(text)
    sentences = [s.strip() for s in nltk.sent_tokenize(text) if len(s.split()) >= 5]
    
    if not sentences:
        print("No se encontraron oraciones suficientemente largas para analizar.")
        return

    print(f"Analizando {len(sentences)} oraciones con SuperAnnotate...")
    
    superannotate_scores = analyze_sentences_superannotate(sentences)

    print("\n" + "="*50)
    print("  INFORME DE MICRO-ANÁLISIS (SuperAnnotate)")
    print("="*50)
    
    for i, sentence in enumerate(sentences):
        score = superannotate_scores[i]
        
        print(f"\033[1mFrase #{i+1}:\033[0m")
        print(sentence)
        
        try:
            score_val = float(score)
            if score_val < 0:
                color = "\033[31m" # Rojo para errores
                score_str = 'ERROR'
            elif score_val > PROBLEM_THRESHOLD:
                color = "\033[91m" # Rojo claro para > umbral
                score_str = f"{score_val:.2f}%"
            else:
                color = "\033[92m" # Verde para < umbral
                score_str = f"{score_val:.2f}%"
        except (ValueError, TypeError):
            color = "\033[31m" # Rojo para errores de formato
            score_str = str(score)

        print(f"  {color}- SuperAnnotate: {score_str}\033[0m")
        print("-" * 20)
            
    print("\n" + "="*50)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {VENV_CHECKER_PATH} {sys.argv[0]} \"/ruta/al/archivo.txt\"")
        sys.exit(1)
        
    # Usamos el venv principal para descargar nltk
    # ya que el entorno de 'sa-detector' podría no tenerlo
    subprocess.run([VENV_CHECKER_PATH, "-c", "import nltk; nltk.download('punkt', quiet=True)"])

    filepath = os.path.abspath(sys.argv[1])
    if not os.path.exists(filepath):
        print(f"Error: El archivo no se encuentra en la ruta: {filepath}")
        sys.exit(1)
        
    main(filepath)
