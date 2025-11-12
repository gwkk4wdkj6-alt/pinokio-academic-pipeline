#!/usr/bin/env python3
"""
Crear citas en Zotero con número de página específico
Compatible con Mac M4 + Gemini CLI
"""

from pyzotero import zotero
import os

# Credenciales
library_id = os.getenv("ZOTERO_USER_ID") or "18642371"
api_key = os.getenv("ZOTERO_API_KEY") or "DSNYsHOsNXAx5YRPfYGN36zM"
library_type = 'user'

# Inicializa conexión
zot = zotero.Zotero(library_id, library_type, api_key)

def crear_item_con_pagina(titulo, autores, paginas, tipo="journalArticle", publicacion=""):
    """
    Crea item en Zotero con información de página específica
    
    Args:
        titulo: Título del artículo/libro
        autores: Lista de autores ["Apellido, Nombre", ...]
        paginas: Número de página o rango (ej: "45", "45-47", "p. 123")
        tipo: Tipo de item (journalArticle, book, bookSection, etc.)
        publicacion: Nombre de la publicación
    """
    
    # Crea estructura del item
    template = zot.item_template(tipo)
    
    template['title'] = titulo
    template['publicationTitle'] = publicacion
    
    # Añade autores
    template['creators'] = []
    for autor in autores:
        partes = autor.split(", ")
        if len(partes) == 2:
            template['creators'].append({
                'creatorType': 'author',
                'lastName': partes[0],
                'firstName': partes[1]
            })
    
    # CRÍTICO: Añade el locator (página) en el campo "extra"
    # Este campo es flexible y acepta metadatos personalizados
    template['extra'] = f"Cited page(s): {paginas}"
    
    # Crea el item
    resp = zot.create_items([template])
    
    print(f"✅ Item creado: {titulo}")
    print(f"   Página citada: {paginas}")
    print(f"   Item key: {resp['successful']['0']['key']}")
    
    return resp

def generar_cita_apa_con_pagina(item_key, paginas):
    """
    Genera cita APA con número de página específico
    
    Args:
        item_key: Clave del item en Zotero
        paginas: Página(s) a citar
    """
    
    # Obtiene el item
    item = zot.item(item_key)
    
    # Obtiene la cita base en formato APA
    # Nota: La API de Zotero no soporta directamente añadir locators
    # Hay que construir la cita manualmente
    
    autores = item['data']['creators']
    autor_texto = autores[0]['lastName'] if autores else "Autor Desconocido"
    año = item['data']['date'][:4] if 'date' in item['data'] else "s.f."
    
    # Construye cita APA con página
    if "-" in str(paginas) or "," in str(paginas):
        cita = f"({autor_texto}, {año}, pp. {paginas})"
    else:
        cita = f"({autor_texto}, {año}, p. {paginas})"
    
    print(f"\n📝 Cita APA generada:")
    print(f"   {cita}\n")
    
    return cita

def exportar_bibliografia_con_paginas(archivo_salida="bibliografia_con_paginas.txt"):
    """
    Exporta todas las referencias con sus páginas citadas
    """
    
    items = zot.top(limit=100)
    
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write("BIBLIOGRAFÍA CON PÁGINAS CITADAS\n")
        f.write("="*70 + "\n\n")
        
        for item in items:
            titulo = item['data'].get('title', 'Sin título')
            extra = item['data'].get('extra', '')
            
            f.write(f"Título: {titulo}\n")
            
            if "Cited page" in extra:
                f.write(f"{extra}\n")
            
            f.write("-"*70 + "\n\n")
    
    print(f"✅ Bibliografía exportada: {archivo_salida}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generar citas APA con número de página desde Zotero.")
    parser.add_argument('--item_id', required=True, help='La clave del ítem en Zotero.')
    parser.add_argument('--paginas', required=False, default=None, help='El número de página o rango a citar.')
    args = parser.parse_args()
    
    if args.paginas:
        generar_cita_apa_con_pagina(args.item_id, args.paginas)
    else:
        # Si no se proporcionan páginas, simplemente obtenemos la bibliografía del ítem
        zot.add_parameters(content='bib', style='apa')
        bib = zot.item(args.item_id)
        # La salida es una lista de strings HTML, así que las unimos
        print("\n".join(bib))
