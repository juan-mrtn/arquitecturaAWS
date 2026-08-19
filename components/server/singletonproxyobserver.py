# singletonproxyobserver.py
# Servidor principal que implementa Singleton, Proxy y Observer
# Dependencias: socket, json, uuid, platform, boto3, logging, argparse
import socket
import json
import uuid
import platform
import logging
import argparse
import threading
import sys
from datetime import datetime
from core.db_manager import DatabaseManager
from core.subscription_manager import SubscriptionManager
from decimal import Decimal

# --- Servidor Principal (que usa los patrones) ---
class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Evitar error "Address already in use"
        # Obtener la instancia Singleton del manejador de DB
        self.db_manager = DatabaseManager()
        # Instanciar el manejador de observers
        self.subscription_manager = SubscriptionManager()

        if self.db_manager is None:
            logging.critical("Failed to initialize DatabaseManager. Server cannot start.")
            sys.exit(1)

    @staticmethod
    def _json_default(obj):
        # Convertir Decimal de DynamoDB a tipos JSON nativos
        if isinstance(obj, Decimal):
            # Si es entero, devolver int; si no, float
            return int(obj) if obj % 1 == 0 else float(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def start(self):
        try:
            self.sock.bind((self.host, self.port))
            self.sock.listen()
            logging.info(f"Server listening on {self.host}:{self.port}")
            while True:
                conn, addr = self.sock.accept()
                logging.info(f"Accepted connection from {addr}")
                # Manejar cada cliente en un hilo separado
                client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                client_thread.daemon = True  # Hilos mueren si el principal muere
                client_thread.start()
        except socket.error as e:
            logging.error(f"Socket error: {e}")
        except KeyboardInterrupt:
            logging.info("Server shutting down.")
        finally:
            self.sock.close()

    def handle_client(self, conn, addr):
        # Generar un ID de sesión para este cliente
        session_id = str(uuid.uuid4())
        is_observer = False
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break  # Cliente desconectado
                
                request = json.loads(data.decode('utf-8'))
                logging.info(f"Received request from {addr}: {request}")
                
                client_uuid = request.get("UUID")
                action = request.get("ACTION")

                if not client_uuid or not action:
                    conn.sendall(json.dumps({"status": "Error", "message": "Missing UUID or ACTION"}).encode('utf-8'))
                    break

                response = None
                # --- Patrón Proxy (lógica de 'set') ---
                # El servidor actúa como proxy: intercepta 'set', actualiza DB, y *luego* notifica
                if action == "set":
                    response = self.handle_set(request, session_id)
                    if response.get("status") == "OK":
                        # Notificar a todos los observadores
                        self.subscription_manager.notify(response.get("data"))
                
                elif action == "get":
                    response = self.handle_get(request, session_id)
                elif action == "list":
                    response = self.handle_list(request, session_id)
                elif action == "subscribe":
                    response = self.handle_subscribe(request, conn, session_id)
                    is_observer = True
                else:
                    response = {"status": "Error", "message": "Unknown ACTION"}

                # Enviar respuesta al cliente (si no es un observador que se queda)
                if response and not is_observer:
                    conn.sendall(json.dumps(response, default=self._json_default).encode('utf-8'))
                
                if not is_observer:
                    break  # Terminar conexión para get/set/list
                # Si es observador, el bucle sigue y el socket se queda abierto
            
        except json.JSONDecodeError:
            logging.warning(f"Invalid JSON received from {addr}")
            conn.sendall(json.dumps({"status": "Error", "message": "Invalid JSON"}).encode('utf-8'))
        except socket.error as e:
            logging.warning(f"Socket error with {addr}: {e}")
        except Exception as e:
            logging.error(f"Error handling client {addr}: {e}", exc_info=True)
        finally:
            if is_observer:
                self.subscription_manager.detach(conn)
            conn.close()
            logging.info(f"Connection closed for {addr}")

    def handle_get(self, request, session_id):
        item_id = request.get("ID")
        self.db_manager.log_action(request["UUID"], session_id, "get", f"ID: {item_id}")
        data = self.db_manager.get_corporate_data(item_id)
        if data:
            return {"status": "OK", "data": data}
        else:
            return {"status": "Error", "message": "Item not found"}

    def handle_list(self, request, session_id):
        self.db_manager.log_action(request["UUID"], session_id, "list")
        data = self.db_manager.list_corporate_data()
        return {"status": "OK", "data": data}

    def handle_set(self, request, session_id):
        # Los datos para 'set' vienen en el request
        item_data = request.copy()
        # Remover 'ACTION' y 'UUID' para que sea un 'Item' limpio de DynamoDB
        item_id = item_data.pop("ID", None)
        if not item_id:
             return {"status": "Error", "message": "Missing ID for set operation"}
        
        item_data.pop("ACTION", None)
        item_data.pop("UUID", None)
        item_data['id'] = item_id  # Asegurar que la clave primaria 'id' esté

        self.db_manager.log_action(request["UUID"], session_id, "set", f"ID: {item_id}")
        updated_data = self.db_manager.set_corporate_data(item_data)
        
        if updated_data:
            return {"status": "OK", "data": updated_data}
        else:
            return {"status": "Error", "message": "Failed to set item"}

    def handle_subscribe(self, request, conn, session_id):
        self.db_manager.log_action(request["UUID"], session_id, "subscribe")
        self.subscription_manager.attach(conn)
        # No se envía respuesta, solo se mantiene el socket abierto
        return None 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Singleton Proxy Observer Server for TPFI IS2.")
    parser.add_argument("-p", dest="server_port", type=int, default=8080, help="Server port to listen on (default: 8080).")
    parser.add_argument("-v", action="store_true", help="Enable verbose/debug mode.")
    args = parser.parse_args()

    # Configurar logging
    log_level = logging.DEBUG if args.v else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)

    server = Server(host="0.0.0.0", port=args.server_port)  # Escuchar en todas las interfaces
    server.start()

