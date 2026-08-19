# simple_set_test.py
# Prueba aislada solo para la operación "SET"

import subprocess
import os
import sys
import time
import json

# --- Configuración ---
SERVER_SCRIPT = os.path.join('components', 'server', 'singletonproxyobserver.py')
CLIENT_SCRIPT = os.path.join('components', 'client', 'singletonclient.py')

# Usamos el input SET original que proveíste
INPUT_SET = os.path.join('inputs', 'input_valid_set.json') 

TEST_HOST = '127.0.0.1'
TEST_PORT = 8080
PYTHON_EXE = sys.executable # Usa tu 'python' o 'python3'

print("--- Iniciando Prueba Aislada de 'SET' ---")

# 1. Iniciar el servidor
print(f"Iniciando servidor en puerto {TEST_PORT}...")

# IMPORTANTE: No capturamos stdout/stderr para evitar el bloqueo del buffer
# Esta es la corrección clave que también faltaba en test_suite.py
server_process = subprocess.Popen(
    [PYTHON_EXE, SERVER_SCRIPT, '-p', str(TEST_PORT), '-v'],
    text=True
    # Al no poner stdout=PIPE, los logs del servidor saldrán en esta terminal
)

# Dar tiempo al servidor para que inicie
time.sleep(3)

# Verificar si el servidor falló al iniciar
if server_process.poll() is not None:
    print("\n¡ERROR! El servidor no pudo iniciarse.")
    print("Asegúrate de que el puerto 8080 esté libre.")
    sys.exit(1)

print("Servidor iniciado. Ejecutando cliente 'SET'...")

# 2. Preparar el comando del cliente
command = [
    PYTHON_EXE, CLIENT_SCRIPT,
    '-i', INPUT_SET,
    '-s', TEST_HOST,
    '-p', str(TEST_PORT)
]

# 3. Ejecutar el cliente y capturar su salida
try:
    # Le damos 15 segundos de tiempo límite
    result = subprocess.run(command, capture_output=True, text=True, timeout=15) 
    
    print("\n--- Resultado del Cliente ---")
    print("STDOUT (Salida JSON):")
    print(result.stdout)
    
    print("\nSTDERR (Errores del cliente):")
    print(result.stderr)

    # 4. Validar el resultado
    print("\n--- Validación ---")
    try:
        response_json = json.loads(result.stdout)
        if response_json.get('status') == 'OK':
            print("✅ PRUEBA 'SET' EXITOSA: El servidor respondió 'OK'.")
        else:
            print(f"❌ PRUEBA FALLIDA: El servidor respondió con error: {response_json}")
    except json.JSONDecodeError:
        print("❌ PRUEBA FALLIDA: La salida del cliente no fue un JSON válido.")
        
except subprocess.TimeoutExpired:
    print("\n❌ PRUEBA FALLIDA: TIMEOUT.")
    print("El cliente tardó más de 15 segundos. Es probable que el servidor (singletonproxyobserver.py) se haya colgado.")
except Exception as e:
    print(f"\n❌ PRUEBA FALLIDA: Ocurrió un error inesperado al ejecutar el cliente: {e}")

finally:
    # 5. Detener el servidor
    print("\nDeteniendo el servidor...")
    server_process.terminate()
    server_process.wait()
    print("Prueba finalizada.")