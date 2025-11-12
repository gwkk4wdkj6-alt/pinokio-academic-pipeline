#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ANTI-PLAGIO OPTIMIZER v9
Sistema inteligente de detección y parafraseo anti-Turnitin
Integra: Análisis de plagio + Generación de ecuaciones + Parafraseo ético
"""

import sys
import json
import re
from datetime import datetime
from pathlib import Path

class AntiPlagioOptimizer:
    
    def __init__(self, texto_trabajo):
        self.texto = texto_trabajo
        self.frases = self._dividir_frases()
        self.resultados = []
        
    def _dividir_frases(self):
        """Divide el texto en frases individuales"""
        frases = re.split(r'[.!?]+', self.texto)
        return [f.strip() for f in frases if f.strip()]
    
    def generar_ecuacion_busqueda(self, frase):
        """
        Genera ecuación de búsqueda estilo Mesh Master
        para encontrar la frase en bases de datos académicas
        
        Formato: 
        (palabra_clave1 OR palabra_clave2) AND (contexto1 OR contexto2)
        """
        palabras = frase.split()
        
        # Palabras clave principales (4-5 palabras más significativas)
        palabras_clave = [p for p in palabras if len(p) > 4][:4]
        
        # Contexto (palabras de 3-4 caracteres)
        palabras_contexto = [p for p in palabras if 3 <= len(p) <= 4][:3]
        
        ecuacion = f"({' OR '.join(palabras_clave)}) AND ({' OR '.join(palabras_contexto)})"
        return ecuacion
    
    def analizar_plagio_frase(self, frase_num, frase):
        """
        Analiza una frase para detectar:
        1. Potencial plagio (basado en estructura y patrones)
        2. Potencial IA (basado en fluidez y genericidad)
        3. Sugerencias de parafraseo
        """
        
        # Detectar plagio (simulado - en producción usaría API real)
        plagio_porcentaje = self._calcular_plagio(frase)
        
        # Detectar IA
        ia_porcentaje = self._calcular_ia(frase)
        
        # Generar sugerencias
        sugerencias = self._generar_sugerencias(frase, plagio_porcentaje, ia_porcentaje)
        
        resultado = {
            "numero_frase": frase_num + 1,
            "frase_original": frase,
            "plagio_detectado": plagio_porcentaje,
            "ia_detectada": ia_porcentaje,
            "ecuacion_busqueda_mesh": self.generar_ecuacion_busqueda(frase),
            "riesgo_turnitin": "ALTO" if (plagio_porcentaje > 40 or ia_porcentaje > 35) else "MEDIO" if (plagio_porcentaje > 20 or ia_porcentaje > 15) else "BAJO",
            "sugerencias_parafraseo": sugerencias
        }
        
        self.resultados.append(resultado)
        return resultado
    
    def _calcular_plagio(self, frase):
        """Heurística para detectar plagio basada en patrones"""
        plagio = 0
        
        # Patrones comunes de plagio
        patrones_plagio = [
            r'es importante',
            r'se puede observar',
            r'cabe destacar',
            r'en conclusión',
            r'por lo tanto',
        ]
        
        for patron in patrones_plagio:
            if re.search(patron, frase.lower()):
                plagio += 15
        
        # Longitud (frases muy largas son sospechosas)
        if len(frase.split()) > 30:
            plagio += 20
        
        return min(plagio, 100)
    
    def _calcular_ia(self, frase):
        """Heurística para detectar IA basada en genericidad"""
        ia = 0
        
        # Palabras genéricas típicas de IA
        palabras_genericas = [
            'significativo', 'relevante', 'importante', 'aspecto',
            'elemento', 'factor', 'proceso', 'sistema', 'estructura'
        ]
        
        for palabra in palabras_genericas:
            if palabra in frase.lower():
                ia += 8
        
        # Fluidez excesiva (sin puntuación interna)
        if len(frase) > 50 and ',' not in frase:
            ia += 15
        
        return min(ia, 100)
    
    def _generar_sugerencias(self, frase, plagio, ia):
        """Genera sugerencias específicas de parafraseo"""
        sugerencias = []
        
        if plagio > 40:
            sugerencias.append("CRÍTICO: Parafrasea completamente esta frase usando estructura diferente")
            sugerencias.append("Intenta: Dividir en 2-3 frases más cortas")
            sugerencias.append("Cambia orden de palabras y estructura sintáctica")
        
        if ia > 35:
            sugerencias.append("Detectada fluidez excesiva (posible IA). Añade ejemplos específicos o datos propios")
            sugerencias.append("Intenta: Incluir datos numéricos, casos concretos o experiencias personales")
        
        if plagio > 20 and ia > 15:
            sugerencias.append("Riesgo combinado alto. Considera reescribir desde cero con tus propias palabras")
        
        return sugerencias
    
    def generar_reporte(self):
        """Genera reporte completo del análisis"""
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        reporte = {
            "fecha_analisis": fecha,
            "total_frases": len(self.frases),
            "frases_alto_riesgo": len([r for r in self.resultados if r["riesgo_turnitin"] == "ALTO"]),
            "frases_medio_riesgo": len([r for r in self.resultados if r["riesgo_turnitin"] == "MEDIO"]),
            "frases_bajo_riesgo": len([r for r in self.resultados if r["riesgo_turnitin"] == "BAJO"]),
            "plagio_promedio": sum([r["plagio_detectado"] for r in self.resultados]) / len(self.resultados) if self.resultados else 0,
            "ia_promedio": sum([r["ia_detectada"] for r in self.resultados]) / len(self.resultados) if self.resultados else 0,
            "frases_detalladas": self.resultados,
            "recomendacion_general": self._generar_recomendacion()
        }
        
        return reporte
    
    def _generar_recomendacion(self):
        """Genera recomendación global basada en análisis"""
        if not self.resultados:
            return "Sin análisis disponible"
        
        alto = len([r for r in self.resultados if r["riesgo_turnitin"] == "ALTO"])
        porcentaje_riesgo = (alto / len(self.resultados)) * 100
        
        if porcentaje_riesgo > 50:
            return "🔴 RIESGO CRÍTICO: Reescribe al menos el 50% del trabajo. Riesgo muy alto de detección en Turnitin."
        elif porcentaje_riesgo > 30:
            return "🟠 RIESGO ALTO: Parafrasea las frases marcadas como críticas. Verifica cambios antes de entregar."
        elif porcentaje_riesgo > 10:
            return "🟡 RIESGO MEDIO: Mejora la redacción en las secciones indicadas. Generalmente aceptable."
        else:
            return "🟢 RIESGO BAJO: Trabajo presenta buena originalidad. Verifica que todas las citas estén en APA7."
    
    def guardar_reporte_json(self, ruta_salida):
        """Guarda el reporte en JSON"""
        reporte = self.generar_reporte()
        with open(ruta_salida, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        return ruta_salida

# --- MAIN ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python anti_plagio_optimizer.py <archivo_txt>")
        sys.exit(1)
    
    archivo = sys.argv[1]
    with open(archivo, 'r', encoding='utf-8') as f:
        texto = f.read()
    
    optimizer = AntiPlagioOptimizer(texto)
    
    # Analizar cada frase
    for i, frase in enumerate(optimizer.frases):
        optimizer.analizar_plagio_frase(i, frase)
    
    # Generar reporte
    reporte = optimizer.generar_reporte()
    
    # Guardar en JSON
    ruta_json = archivo.replace('.txt', '_anti_plagio_reporte.json')
    optimizer.guardar_reporte_json(ruta_json)
    
    # Mostrar resumen
    print("\n" + "="*60)
    print("ANÁLISIS ANTI-PLAGIO COMPLETADO")
    print("="*60)
    print(f"Total de frases: {reporte['total_frases']}")
    print(f"Alto riesgo: {reporte['frases_alto_riesgo']} | Medio: {reporte['frases_medio_riesgo']} | Bajo: {reporte['frases_bajo_riesgo']}")
    print(f"Plagio promedio: {reporte['plagio_promedio']:.1f}% | IA promedio: {reporte['ia_promedio']:.1f}%")
    print(f"\n📋 Recomendacion: {reporte['recomendacion_general']}")
    print(f"\n💾 Reporte guardado en: {ruta_json}")
    print("="*60)
