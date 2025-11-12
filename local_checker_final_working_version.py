import os
import docx
import PyPDF2
import time
import sys
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel, AutoConfig, PreTrainedModel, AutoModelForSequenceClassification
import json
import nltk

os.environ['TOKENIZERS_PARALLELISM'] = 'false'

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

class DesklibAIDetectionModel(PreTrainedModel):
    config_class = AutoConfig
    def __init__(self, config):
        super().__init__(config)
        self.model = AutoModel.from_config(config)
        self.classifier = nn.Linear(config.hidden_size, 1)
        self.init_weights()

    def forward(self, input_ids, attention_mask=None, labels=None, **kwargs):
        outputs = self.model(input_ids, attention_mask=attention_mask)
        last_hidden_state = outputs[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, dim=1)
        sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
        pooled_output = sum_embeddings / sum_mask
        logits = self.classifier(pooled_output)
        return {"logits": logits}

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

def get_ensemble_verdict(scores):
    if any(s < 0 for s in scores):
        return "ERROR EN ANÁLISIS", "Uno o más modelos de IA fallaron."
    if all(s < 40.0 for s in scores):
        return "PROBABLEMENTE HUMANO", "Todos los modelos coinciden en una baja probabilidad."
    if all(s > 60.0 for s in scores):
        return "PROBABLEMENTE IA", "Todos los modelos coinciden en una alta probabilidad."
    return "RESULTADO AMBIGUO (Revisión Manual Sugerida)", "Los modelos ofrecen resultados contradictorios o intermedios."

def analyze_chunk_subprocess(chunk_text):
    scores = {}
    # Desklib
    try:
        temp_script_path = "_temp_runner.py"
        with open(temp_script_path, "w", encoding="utf-8") as f:
            f.write('''
import sys, torch, torch.nn as nn
from transformers import AutoTokenizer, AutoModel, AutoConfig, PreTrainedModel
class D(PreTrainedModel):
    config_class=AutoConfig
    def __init__(self,c):super().__init__(c);self.model=AutoModel.from_config(c);self.classifier=nn.Linear(c.hidden_size,1);self.init_weights()
    def forward(self,input_ids,attention_mask=None,**kwargs):o=self.model(input_ids,attention_mask=attention_mask);lhs=o[0];ime=attention_mask.unsqueeze(-1).expand(lhs.size()).float();se=torch.sum(lhs*ime,dim=1);sm=torch.clamp(ime.sum(dim=1),min=1e-9);po=se/sm;l=self.classifier(po);return{"logits":l}
model_name="desklib/ai-text-detector-v1.01";text=sys.argv[1]
try:
    tok=AutoTokenizer.from_pretrained(model_name);conf=AutoConfig.from_pretrained(model_name);model=D.from_pretrained(model_name,config=conf);model.eval()
    inputs=tok(text,return_tensors="pt",truncation=True,max_length=512,padding="max_length")
    with torch.no_grad():p=torch.sigmoid(model(**inputs)["logits"]).item()
    print(p*100)
except Exception:print(-1)
''')
        desklib_python_path = "/Volumes/MainDrive/miniforge3/envs/desklib-detector/bin/python"
        import subprocess
        process = subprocess.run([desklib_python_path, temp_script_path, chunk_text], capture_output=True, text=True, encoding="utf-8")
        scores['desklib'] = float(process.stdout.strip()) if process.returncode == 0 and process.stdout.strip() else -1
    except Exception:
        scores['desklib'] = -1
    
    # SuperAnnotate
    try:
        temp_script_path = "_temp_runner.py"
        with open(temp_script_path, "w", encoding="utf-8") as f:
            f.write('''
import sys, torch, torch.nn.functional as F
from generated_text_detector.utils.model.roberta_classifier import RobertaClassifier
from generated_text_detector.utils.preprocessing import preprocessing_text
from transformers import AutoTokenizer
text=sys.argv[1];model_name="SuperAnnotate/ai-detector"
try:
    model=RobertaClassifier.from_pretrained(model_name);tok=AutoTokenizer.from_pretrained(model_name);model.eval()
    pt=preprocessing_text(text);tokens=tok.encode_plus(pt,add_special_tokens=True,max_length=512,padding='longest',truncation=True,return_token_type_ids=True,return_tensors="pt")
    with torch.no_grad():_,l=model(**tokens);p=F.sigmoid(l).squeeze(1).item()
    print(p*100)
except Exception:print(-1)
''')
        conda_python_path = "/Volumes/MainDrive/miniforge3/envs/sa-detector/bin/python"
        import subprocess
        process = subprocess.run([conda_python_path, temp_script_path, chunk_text], capture_output=True, text=True, encoding="utf-8")
        scores['superannotate'] = float(process.stdout.strip()) if process.returncode == 0 and process.stdout.strip() else -1
    except Exception:
        scores['superannotate'] = -1
    
    if os.path.exists("_temp_runner.py"): os.remove("_temp_runner.py")
    return scores

def perform_full_analysis(text_for_ai):
    tokenizer = AutoTokenizer.from_pretrained("openai-community/roberta-base-openai-detector")
    max_length = 512
    sentences = nltk.sent_tokenize(text_for_ai)
    chunks = []
    current_chunk_text = ""
    for sentence in sentences:
        test_chunk = current_chunk_text + " " + sentence if current_chunk_text else sentence
        if len(tokenizer.encode(test_chunk, truncation=False)) <= max_length - 2:
            current_chunk_text = test_chunk
        else:
            if current_chunk_text:
                chunks.append(current_chunk_text)
            current_chunk_text = sentence
    if current_chunk_text:
        chunks.append(current_chunk_text)

    all_models_results = {
        "desklib/ai-text-detector-v1.01": {'scores_by_chunk': {}},
        "SuperAnnotate/ai-detector": {'scores_by_chunk': {}}
    }

    print(f"\n[DEBUG] Texto dividido en {len(chunks)} trozos. Analizando...")

    for i, chunk in enumerate(chunks):
        print(f"---\n[DEBUG] Procesando Trozo {i+1}/{len(chunks)}")
        try:
            sub_scores = analyze_chunk_subprocess(chunk)
            all_models_results["desklib/ai-text-detector-v1.01"]['scores_by_chunk'][chunk] = sub_scores.get('desklib', -1)
            all_models_results["SuperAnnotate/ai-detector"]['scores_by_chunk'][chunk] = sub_scores.get('superannotate', -1)
        except Exception as e:
            print(f"Error en subprocesos: {e}")
            all_models_results["desklib/ai-text-detector-v1.01"]['scores_by_chunk'][chunk] = -1
            all_models_results["SuperAnnotate/ai-detector"]['scores_by_chunk'][chunk] = -1

    print("\n[DEBUG] Análisis completo de todos los trozos finalizado.")
    return all_models_results

def display_report(file_path, analysis_results):
    print("\n" + "="*40)
    print("  INFORME DE ANÁLISIS DE ORIGINALIDAD")
    print("="*40)
    print(f"Archivo: {os.path.basename(file_path)}\n")
    print("----------------------------------------")
    print("ANÁLISIS DE DETECCIÓN IA (ENSAMBLE)")
    print("----------------------------------------")
    
    final_scores = []
    for name, data in analysis_results.items():
        if data['scores_by_chunk']:
            max_score = max(data['scores_by_chunk'].values())
        else:
            max_score = -1
        final_scores.append(max_score)

    verdict, explanation = get_ensemble_verdict(final_scores)
    print(f"VEREDICTO FINAL: {verdict}")
    print(f"Justificación: {explanation}\n")
    print("--- Puntuaciones Individuales ---")
    for name, data in analysis_results.items():
        if data['scores_by_chunk']:
            max_score = max(data['scores_by_chunk'].values())
            max_chunk = [k for k, v in data['scores_by_chunk'].items() if v == max_score][0]
        else:
            max_score = -1
            max_chunk = ""
        score_str = 'ERROR' if max_score < 0 else f"{max_score:.2f}% de prob. IA"
        print(f"- Modelo '{name}': {score_str}")
        if max_chunk and max_score > 30:
            print(f"    Trozo con Mayor Probabilidad de IA:")
            print('      "' + max_chunk.strip() + '"')
        print()
    print("\n" + "="*40)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 local_checker.py \"/ruta/al/archivo.txt\"")
        sys.exit(1)
    file_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(file_path):
        print(f"Error: El archivo no se encuentra en la ruta: {file_path}")
        sys.exit(1)
    text_content = extract_text(file_path)
    if text_content:
        print("\nTexto extraído con éxito. Iniciando análisis completo...")
        text_for_ai = text_content
        text_lower = text_content.lower()
        for marker in BIBLIOGRAPHY_MARKERS:
            marker_lower = marker.lower()
            if marker_lower in text_lower:
                print(f"\n--- Bibliografía detectada con marcador '{marker}'. Analizando solo el cuerpo del texto para la IA. ---")
                start_index = text_lower.find(marker_lower)
                text_for_ai = text_content[:start_index]
                break
        initial_results = perform_full_analysis(text_for_ai)
        print("\n\n--- DIAGNÓSTICO INICIAL COMPLETADO ---")
        display_report(file_path, initial_results)
    else:
        print("No se pudo extraer contenido del archivo para analizar.")