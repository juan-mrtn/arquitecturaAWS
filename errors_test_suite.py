# other_tests_test_suite.py
# Script de prueba automatizado para el TPFI de IS2 - Resto de Casos
# Versión con los casos de prueba restantes (CP-05 a CP-10)

import unittest
import subprocess
import os
import time
import json
import boto3
import sys
import uuid
import signal
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

# (CP-01..CP-09) archivos de salida
OUTPUT_CP01_GET = os.path.join(TEST_OUTPUT_DIR, 'output_cp01_get.json')
OUTPUT_CP02_SET = os.path.join(TEST_OUTPUT_DIR, 'output_cp02_set.json')
OUTPUT_CP03_LIST = os.path.join(TEST_OUTPUT_DIR, 'output_cp03_list.json')
OUTPUT_CP04_SET = os.path.join(TEST_OUTPUT_DIR, 'output_cp04_set.json')  # además del observer_output.json existente
OUTPUT_CP05_GET_INEX = os.path.join(TEST_OUTPUT_DIR, 'output_cp05_get_inexistente.json')
OUTPUT_CP06_NO_MIN = os.path.join(TEST_OUTPUT_DIR, 'output_cp06_sin_datos_minimos.json')
OUTPUT_CP07_MALFORM = os.path.join(TEST_OUTPUT_DIR, 'output_cp07_json_malformado.json')
OUTPUT_CP08_GET_SIN_ID = os.path.join(TEST_OUTPUT_DIR, 'output_cp08_get_sin_id.json')
OUTPUT_CP09_SERVER_DOWN = os.path.join(TEST_OUTPUT_DIR, 'output_cp09_servidor_caido.json')

def save_output(path, obj):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(obj, f, indent=4, default=json_default)
    except Exception as e:
        print(f"Warning: no se pudo guardar el output en {path}: {e}")



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
    
    @staticmethod
    def kill_port_processes(port):
        """Busca y mata todos los procesos que usan el puerto especificado"""
        try:
            # Usar lsof para encontrar procesos que usen el puerto
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid_str in pids:
                    try:
                        pid = int(pid_str)
                        print(f"  Matando proceso {pid} que usa el puerto {port}...")
                        os.kill(pid, signal.SIGTERM)
                        time.sleep(0.5)
                        try:
                            os.kill(pid, 0)  # Verificar si sigue vivo
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # lsof no disponible o timeout, intentar con fuser
            try:
                subprocess.run(
                    ['fuser', '-k', f'{port}/tcp'],
                    capture_output=True,
                    timeout=2
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

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
            text=True,
            start_new_session=True
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
            
            # Intentar terminación normal del proceso principal
            cls.server_process.terminate()
            try:
                cls.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Plan B: matar grupo de procesos
                try:
                    pgid = os.getpgid(cls.server_process.pid)
                    os.killpg(pgid, signal.SIGTERM)
                    time.sleep(1)
                    if cls.server_process.poll() is None:
                        os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    pass
                finally:
                    cls.server_process.kill()
                    cls.server_process.wait()
            
            # Plan C: buscar y matar todos los procesos que usen el puerto 8080
            cls.kill_port_processes(TEST_PORT)
            
            # Asegurar que el proceso principal esté muerto
            try:
                if cls.server_process.poll() is None:
                    cls.server_process.kill()
                    cls.server_process.wait(timeout=2)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                pass
            
            time.sleep(0.5)  # dar tiempo al SO a liberar el puerto
            
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

    def test_cp05_get_inexistente(self):
        """ CP-05: get con ID inexistente (Error). """
        print("\nEjecutando: test_cp05_get_inexistente")
        result = self.run_client(INPUT_GET_INEXISTENTE)
        self.assertEqual(result.get('status'), 'Error', f"Resultado: {result}")
        self.assertIn("Item not found", result.get('message', ''), f"Resultado: {result}")
        save_output(OUTPUT_CP05_GET_INEX, result)

    def test_cp06_requerimiento_sin_datos_minimos(self):
        """ CP-06: set con JSON sin datos (Requerimiento sin datos mínimos). """
        print("\nEjecutando: test_cp06_requerimiento_sin_datos_minimos")
        result = self.run_client(INPUT_SET_NO_ACTION) # Este JSON no tiene "ACTION"
        self.assertEqual(result.get('status'), 'Error', f"Resultado: {result}")
        self.assertIn("Missing UUID or ACTION", result.get('message', ''), f"Resultado: {result}")
        save_output(OUTPUT_CP06_NO_MIN, result)

    def test_cp07_json_malformado(self):
        """ CP-07: singletonclient con JSON malformado (Argumentos malformados). """
        print("\nEjecutando: test_cp07_json_malformado")
        result = self.run_client(INPUT_MALFORMED)
        # El servidor (con el buffer fix) detectará el JSON roto y enviará un error
        self.assertEqual(result.get('status'), 'INVALID_JSON_OUTPUT', f"Resultado: {result}")
        self.assertIn("not valid JSON", result.get('error', ''), "El mensaje de error no indica JSON no válido.")
        save_output(OUTPUT_CP07_MALFORM, result)

    def test_cp08_get_sin_id(self):
        """ CP-08: singletonclient con ID faltante en get (Argumentos malformados). """
        print("\nEjecutando: test_cp08_get_sin_id")
        result = self.run_client(INPUT_GET_NO_ID) # Este JSON no tiene "ID"
        # La lógica de handle_get() espera un "ID" que será None
        self.assertEqual(result.get('status'), 'Error', f"Resultado: {result}")
        self.assertIn("Item not found", result.get('message', ''), f"Resultado: {result}")
        save_output(OUTPUT_CP08_GET_SIN_ID, result)

    def test_cp09_servidor_caido_cliente_singleton(self):
        """ CP-09: Manejo en clientes (singleton) de server aplicativo caido. """
        print("\nEjecutando: test_cp09_servidor_caido_cliente_singleton")
        
        # 1. Detener el servidor temporalmente
        print("... (deteniendo servidor temporalmente)")
        self.server_process.terminate()
        try:
            self.server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Forzar terminación si no responde
            try:
                pgid = os.getpgid(self.server_process.pid)
                os.killpg(pgid, signal.SIGTERM)
                time.sleep(0.5)
                if self.server_process.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)
            except Exception:
                pass
            finally:
                self.server_process.kill()
                self.server_process.wait()
        
        # Asegurar que el puerto esté libre antes de continuar
        self.kill_port_processes(TEST_PORT)
        time.sleep(0.5)
        
        # 2. Intentar conectar (debe fallar rápido)
        result = self.run_client(INPUT_GET)
        self.assertEqual(result.get('status'), 'SERVER_DOWN', f"Resultado: {result}")
        save_output(OUTPUT_CP09_SERVER_DOWN, result)
        
        # 3. Reiniciar el servidor para las pruebas restantes y tearDownClass
        print("... (reiniciando servidor)")
        self.server_process = subprocess.Popen(
            [PYTHON_EXE, SERVER_SCRIPT, '-p', str(TEST_PORT)],
            text=True,
            start_new_session=True
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
    print("Iniciando Suite de Pruebas para TPFI IS2 (Singleton/Proxy/Observer) - Resto de Casos")
    print(f"Servidor: {SERVER_SCRIPT}")
    print(f"Cliente: {CLIENT_SCRIPT}")
    print("==================================================")
    unittest.main()