# test_suite.py
# Script de prueba automatizado para el TPFI de IS2
# Versión completa alineada con los 10 Casos de Prueba (CP)

import unittest
import subprocess
import os
import time
import json
import boto3
import sys
import uuid
from decimal import Decimal

# --- Configuración de Pruebas ---
SERVER_SCRIPT = os.path.join('components', 'server', 'singletonproxyobserver.py')
CLIENT_SCRIPT = os.path.join('components', 'client', 'singletonclient.py')
OBSERVER_SCRIPT = os.path.join('components', 'client', 'observerclient.py')

# Entradas
INPUT_GET = os.path.join('inputs', 'input_valid_get.json')
INPUT_SET = os.path.join('inputs', 'input_valid_set.json')
INPUT_LIST = os.path.join('inputs', 'input_valid_list.json')

# Archivos de prueba temporales
TEST_OUTPUT_DIR = 'test_outputs'
# (CP-02)
INPUT_SET_TEST_ID = os.path.join(TEST_OUTPUT_DIR, 'input_set_test.json')
# (CP-04)
OUTPUT_OBSERVER = os.path.join(TEST_OUTPUT_DIR, 'observer_output.json')
# (CP-05)
INPUT_GET_INEXISTENTE = os.path.join(TEST_OUTPUT_DIR, 'input_get_inexistente.json')
# (CP-06)
INPUT_SET_NO_ACTION = os.path.join(TEST_OUTPUT_DIR, 'input_set_no_action.json')
# (CP-07)
INPUT_MALFORMED = os.path.join(TEST_OUTPUT_DIR, 'input_malformed.json')
# (CP-08)
INPUT_GET_NO_ID = os.path.join(TEST_OUTPUT_DIR, 'input_get_no_id.json')


# Configuración del servidor
TEST_HOST = '127.0.0.1'
TEST_PORT = 8080
PYTHON_EXE = sys.executable

# --- Helper para convertir Decimal de DynamoDB ---
def json_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

class TestIntegracionServidor(unittest.TestCase):
    
    server_process = None
    log_table = None
    data_table = None
    test_session_uuid = str(uuid.uuid4())
    test_set_id = f"test-item-{test_session_uuid}"

    @classmethod
    def setUpClass(cls):
        """
        Se ejecuta una vez antes de todas las pruebas.
        Crea los JSON de prueba e inicia el servidor principal.
        """
        print(f"Iniciando el servidor ({SERVER_SCRIPT}) en el puerto {TEST_PORT}...")
        
        # Crear directorio de salidas de prueba
        os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

        # --- Crear archivos JSON para los casos de prueba ---
        with open(INPUT_SET_TEST_ID, 'w') as f: # CP-02
            json.dump({"ACTION": "set", "ID": cls.test_set_id, "data": "Dato de prueba de integracion"}, f)
        
        with open(INPUT_GET_INEXISTENTE, 'w') as f: # CP-05
            json.dump({"ACTION": "get", "ID": f"ID-INEXISTENTE-{cls.test_session_uuid}"}, f)

        with open(INPUT_SET_NO_ACTION, 'w') as f: # CP-06
            json.dump({"ID": "test-id", "UUID": "test-uuid"}, f) # JSON sin "ACTION"
            
        with open(INPUT_MALFORMED, 'w') as f: # CP-07
            f.write('{"esto": "no es json",')

        with open(INPUT_GET_NO_ID, 'w') as f: # CP-08
            json.dump({"ACTION": "get", "UUID": "test-uuid"}, f) # JSON sin "ID"

        # --- Iniciar el servidor (Corrección: Sin -v y sin pipes) ---
        cls.server_process = subprocess.Popen(
            [PYTHON_EXE, SERVER_SCRIPT, '-p', str(TEST_PORT)], # Quitamos -v
            text=True
            # No capturamos stdout/stderr para evitar bloqueo de buffer
        )
        
        time.sleep(3) 
        
        if cls.server_process.poll() is not None:
            raise Exception("El servidor no pudo iniciarse. ¿El puerto 8080 está ocupado?")

        print("Servidor iniciado. Conectando a DynamoDB...")
        try:
            dynamodb = boto3.resource('dynamodb')
            cls.log_table = dynamodb.Table('CorporateLog')
            cls.data_table = dynamodb.Table('CorporateData')
            cls.log_table.scan()
        except Exception as e:
            cls.server_process.terminate()
            raise Exception(f"Error al conectar con DynamoDB. Asegúrate que AWS CLI esté configurado. Error: {e}")

        print("Configuración completada.")

    @classmethod
    def tearDownClass(cls):
        """
        Se ejecuta una vez después de todas las pruebas.
        Detiene el servidor y limpia los datos de prueba.
        """
        if cls.server_process:
            print("\nDeteniendo el servidor...")
            cls.server_process.terminate()
            cls.server_process.wait()
            
            try:
                cls.data_table.delete_item(Key={'id': cls.test_set_id})
                print(f"Item de prueba '{cls.test_set_id}' eliminado.")
            except Exception:
                pass
            
            print("Servidor detenido.")

    def run_client(self, input_file):
        """ Helper para ejecutar singletonclient.py """
        command = [PYTHON_EXE, CLIENT_SCRIPT, '-i', input_file, '-s', TEST_HOST, '-p', str(TEST_PORT)]
        
        try:
            # Aumentamos el timeout por si AWS está lento, pero 10s es usualmente suficiente
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
            
            if "Socket Error" in result.stderr or "Connection refused" in result.stderr:
                return {"status": "SERVER_DOWN", "error": result.stderr}

            try:
                response_json = json.loads(result.stdout)
                return response_json
            except json.JSONDecodeError:
                return {"status": "INVALID_JSON_OUTPUT", "output": result.stdout, "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "error": "El cliente tardó demasiado en responder."}
        except Exception as e:
            return {"status": "CLIENT_CRASH", "error": str(e)}

    # --- INICIO DE CASOS DE PRUEBA (Ordenados por CP) ---

    def test_cp01_get_exitoso(self):
        """ CP-01: get exitoso (Camino feliz). """
        print("\nEjecutando: test_cp01_get_exitoso")
        result = self.run_client(INPUT_GET)
        self.assertEqual(result.get('status'), 'OK', f"Resultado: {result}")
        self.assertEqual(result['data'].get('id'), 'UADER-FCYT-IS2', f"Resultado: {result}")

    def test_cp02_set_exitoso(self):
        """ CP-02: set exitoso (Camino feliz). """
        print("\nEjecutando: test_cp02_set_exitoso")
        result = self.run_client(INPUT_SET_TEST_ID) 
        self.assertEqual(result.get('status'), 'OK', f"Resultado: {result}")
        self.assertEqual(result['data'].get('id'), self.test_set_id, f"Resultado: {result}")

    def test_cp03_list_exitoso(self):
        """ CP-03: list exitoso (Camino feliz). """
        print("\nEjecutando: test_cp03_list_exitoso")
        result = self.run_client(INPUT_LIST)
        self.assertEqual(result.get('status'), 'OK', f"Resultado: {result}")
        self.assertIsInstance(result['data'], list, f"Resultado: {result}")

# (Asegúrate de que las constantes como OUTPUT_OBSERVER, PYTHON_EXE,
# OBSERVER_SCRIPT, TEST_HOST, TEST_PORT, INPUT_SET, etc., estén definidas
# y accesibles dentro de la clase de prueba.)

    def test_cp04_observer_exitoso(self):
        """ CP-04: subscribe exitoso y recepción de notificación set (Camino feliz Observer). """
        print("\nEjecutando: test_cp04_observer_exitoso")
        
        # 1. Limpieza
        if os.path.exists(OUTPUT_OBSERVER):
            os.remove(OUTPUT_OBSERVER)
            
        # 2. Comando para iniciar el observador
        observer_command = [PYTHON_EXE, OBSERVER_SCRIPT, '-o', OUTPUT_OBSERVER, '-s', TEST_HOST, '-p', str(TEST_PORT)]
        
        # Inicia el proceso del observador
        observer_process = subprocess.Popen(observer_command, text=True)
        
        try:
            # 3. Espera inicial (suscripción)
            time.sleep(6) # Aumentamos ligeramente a 4s por seguridad de timing
            print("... (Observer conectado, enviando SET)")
            
            # 4. Ejecuta el SET
            set_result = self.run_client(INPUT_SET)
            self.assertEqual(set_result.get('status'), 'OK', f"La operación SET falló: {set_result}")
            
            # 5. Espera a que la notificación llegue y se escriba en disco
            time.sleep(6) # Aumentamos ligeramente a 4s por seguridad de timing
        finally:
            # 6. Termina el observador
            observer_process.terminate()
            observer_process.wait()

        # 7. Verificación de archivo
        self.assertTrue(os.path.exists(OUTPUT_OBSERVER), "El cliente observador no creó el archivo de salida.")
        
        # --- Nueva lógica de parsing: Extraer múltiples JSONs del contenido completo ---
        with open(OUTPUT_OBSERVER, 'r') as f:
            content = f.read()

        # Función helper para extraer todos los JSON objects
        def extract_jsons(s):
            decoder = json.JSONDecoder()
            jsons = []
            idx = 0
            while idx < len(s):
                try:
                    obj, end = decoder.raw_decode(s, idx)
                    jsons.append(obj)
                    idx = end
                except json.JSONDecodeError:
                    idx += 1  # Avanza si hay caracteres no válidos (e.g., extra newlines)
            return jsons

        observer_jsons = extract_jsons(content)
        
        self.assertGreater(len(observer_jsons), 0, "El archivo de salida del observador no contiene JSON válido.")
        
        # Seleccionamos el último JSON (la notificación del SET)
        observer_json = observer_jsons[-1]
        
        # Validación
        expected_id = "UADER-FCYT-IS2" 
        self.assertEqual(observer_json.get('id'), expected_id, "El observador no recibió los datos correctos.")
        print("... (Notificación de observador recibida y validada)")
            



    def test_cp05_get_inexistente(self):
        """ CP-05: get con ID inexistente (Error). """
        print("\nEjecutando: test_cp05_get_inexistente")
        result = self.run_client(INPUT_GET_INEXISTENTE)
        self.assertEqual(result.get('status'), 'Error', f"Resultado: {result}")
        self.assertIn("Item not found", result.get('message', ''), f"Resultado: {result}")

    def test_cp06_requerimiento_sin_datos_minimos(self):
        """ CP-06: set con JSON sin datos (Requerimiento sin datos mínimos). """
        print("\nEjecutando: test_cp06_requerimiento_sin_datos_minimos")
        result = self.run_client(INPUT_SET_NO_ACTION) # Este JSON no tiene "ACTION"
        self.assertEqual(result.get('status'), 'Error', f"Resultado: {result}")
        self.assertIn("Missing UUID or ACTION", result.get('message', ''), f"Resultado: {result}")

    def test_cp07_json_malformado(self):
        """ CP-07: singletonclient con JSON malformado (Argumentos malformados). """
        print("\nEjecutando: test_cp07_json_malformado")
        result = self.run_client(INPUT_MALFORMED)
        # El servidor (con el buffer fix) detectará el JSON roto y enviará un error
        self.assertEqual(result.get('status'), 'INVALID_JSON_OUTPUT', f"Resultado: {result}")
        self.assertIn("not valid JSON", result.get('error', ''), "El mensaje de error no indica JSON no válido.")

    def test_cp08_get_sin_id(self):
        """ CP-08: singletonclient con ID faltante en get (Argumentos malformados). """
        print("\nEjecutando: test_cp08_get_sin_id")
        result = self.run_client(INPUT_GET_NO_ID) # Este JSON no tiene "ID"
        # La lógica de handle_get() espera un "ID" que será None
        self.assertEqual(result.get('status'), 'Error', f"Resultado: {result}")
        self.assertIn("Item not found", result.get('message', ''), f"Resultado: {result}")

    def test_cp09_servidor_caido_cliente_singleton(self):
        """ CP-09: Manejo en clientes (singleton) de server aplicativo caido. """
        print("\nEjecutando: test_cp09_servidor_caido_cliente_singleton")
        
        # 1. Detener el servidor temporalmente
        print("... (deteniendo servidor temporalmente)")
        self.server_process.terminate()
        self.server_process.wait()
        
        # 2. Intentar conectar (debe fallar rápido)
        result = self.run_client(INPUT_GET)
        self.assertEqual(result.get('status'), 'SERVER_DOWN', f"Resultado: {result}")
        
        # 3. Reiniciar el servidor para las pruebas restantes y tearDownClass
        print("... (reiniciando servidor)")
        self.server_process = subprocess.Popen(
            [PYTHON_EXE, SERVER_SCRIPT, '-p', str(TEST_PORT)],
            text=True
        )
        time.sleep(3) # Darle tiempo para reiniciar
        self.assertIsNone(self.server_process.poll(), "El servidor no pudo reiniciarse después de la prueba de caída.")

    def test_cp10_puerto_ocupado(self):
        """ CP-10: singletonproxyobserver no inicia en puerto ocupado (Levantar dos veces). """
        print("\nEjecutando: test_cp10_puerto_ocupado")
        # El primer servidor (self.server_process) ya está corriendo
        
        # Corrección: No usar pipes
        second_server_process = subprocess.Popen(
            [PYTHON_EXE, SERVER_SCRIPT, '-p', str(TEST_PORT)],
            stderr=subprocess.PIPE, # Capturamos solo stderr para leer el error
            text=True
        )
        
        time.sleep(2)
        _, stderr = second_server_process.communicate()
        
        self.assertIn("Address already in use", stderr, "El segundo servidor no falló como se esperaba.")
        print("... (El segundo servidor falló correctamente: Address already in use)")


# --- Ejecutar las pruebas ---
if __name__ == "__main__":
    print("==================================================")
    print("Iniciando Suite de Pruebas para TPFI IS2 (Singleton/Proxy/Observer)")
    print(f"Servidor: {SERVER_SCRIPT}")
    print(f"Cliente: {CLIENT_SCRIPT}")
    print("==================================================")
    unittest.main()