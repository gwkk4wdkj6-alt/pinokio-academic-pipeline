#!/usr/bin/env python3
"""
Script simple para enviar un prompt a Comet.app en macOS.

Uso:
    python gemini_sender.py --prompt-file ruta/al/prompt.txt

El script:
1. Lee el prompt desde un archivo.
2. Lo coloca en el portapapeles.
3. Ejecuta AppleScript para activar Comet, pegar el prompt y presionar Enter.
4. Termina inmediatamente después de enviar.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

def put_on_clipboard(text: str) -> bool:
    try:
        process = subprocess.Popen(
            ['pbcopy'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.communicate(text.encode('utf-8'))
        return process.returncode == 0
    except Exception as e:
        print(f"✗ Error al colocar texto en el portapapeles: {e}", file=sys.stderr)
        return False

def run_applescript(script: str) -> bool:
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            print(f"✗ Error al ejecutar AppleScript: {result.stderr.strip()}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"✗ Error inesperado con AppleScript: {e}", file=sys.stderr)
        return False

def send_prompt_to_comet(prompt_file_path: str) -> bool:
    try:
        prompt_path = Path(prompt_file_path)
        if not prompt_path.exists():
            print(f"✗ Error: El archivo '{prompt_file_path}' no existe", file=sys.stderr)
            return False

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_text = f.read().strip()

        if not prompt_text:
            print(f"✗ Error: El archivo '{prompt_file_path}' está vacío", file=sys.stderr)
            return False

        print(f"✓ Prompt cargado: {len(prompt_text)} caracteres")

        print("\n⚙️  Colocando prompt en el portapapeles...")
        if not put_on_clipboard(prompt_text):
            return False
        print("✓ Prompt en el portapapeles")
        time.sleep(0.5)

        sequence = [
            ("Activando Comet.app...", 'tell application "/Applications/Comet.app" to activate'),
            ("Creando nueva pestaña...", 'tell application "System Events" to keystroke "t" using command down'),
            ("Activando campo de entrada...", 'tell application "System Events" to keystroke "a" using {option down}'),
            ("Pegando prompt...", 'tell application "System Events" to keystroke "v" using command down'),
            ("Enviando prompt...", 'tell application "System Events" to keystroke return')
        ]

        for msg, cmd in sequence:
            print(f"⚙️  {msg}")
            if not run_applescript(cmd):
                print(f"✗ Falló en el paso: {msg}", file=sys.stderr)
                return False
            time.sleep(1) # Pequeña pausa entre comandos

        print("\n✓ Prompt enviado a Comet.app exitosamente.")
        print("Ahora, por favor, espera la respuesta en Comet, cópiala y pégala en el chat.")
        return True

    except Exception as e:
        print(f"\n✗ Error inesperado en el proceso: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Envía un prompt a Comet.app en macOS.',
        epilog='Ejemplo: python gemini_sender.py --prompt-file prompt.txt'
    )
    parser.add_argument(
        '--prompt-file',
        type=str,
        required=True,
        metavar='PATH',
        help='Ruta al archivo de texto con el prompt.'
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  Script de Envío de Prompt para Comet.app")
    print("=" * 50)

    if send_prompt_to_comet(args.prompt_file):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
