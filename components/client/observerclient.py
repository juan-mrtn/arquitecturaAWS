# observerclient.py
# Dependencias: socket, json, uuid, time, argparse [cite: 142]
import socket
import json
import uuid
import time
import argparse
import sys

class ObserverClient:
    def __init__(self, host, port, output_file, verbose):
        self.host = host
        self.port = port
        self.output_file = output_file
        self.verbose = verbose
        self.cpu_uuid = str(uuid.getnode()) # [cite: 303]
        self.sock = None
        self.retry_delay = 30 # Segundos para reintentar [cite: 79, 318]

    def v_print(self, message):
        if self.verbose:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.v_print(f"Connected to server at {self.host}:{self.port}")
                self.send_subscription()
                self.listen_for_updates()
            except socket.error as e:
                self.v_print(f"Connection lost: {e}. Retrying in {self.retry_delay} seconds...")
                if self.sock:
                    self.sock.close()
                time.sleep(self.retry_delay) # Manejo de servidor caído [cite: 318]

    def send_subscription(self):
        # Enviar solicitud de suscripción [cite: 79, 303]
        subscribe_request = {
            "UUID": self.cpu_uuid,
            "ACTION": "subscribe" 
        }
        self.sock.sendall(json.dumps(subscribe_request).encode('utf-8'))
        self.v_print("Subscription request sent.")

    def listen_for_updates(self):
        # Quedar escuchando por notificaciones (múltiples respuestas) [cite: 314]
        buffer = ""
        while True:
            data = self.sock.recv(1024)
            if not data:
                # Conexión cerrada por el servidor
                raise socket.error("Server closed connection")
            
            # Es posible que múltiples JSONs lleguen juntos o partidos
            # Este es un buffer simple; para robustez, se necesita un delimitador
            buffer += data.decode('utf-8')
            
            # Asumimos que cada JSON se envía como una unidad (esto puede fallar)
            # Una mejor implementación usaría un delimitador de mensajes
            try:
                # Intentar procesar como un JSON completo
                response_json = json.loads(buffer)
                self.handle_update(response_json)
                buffer = "" # Limpiar buffer si fue exitoso
            except json.JSONDecodeError:
                # Datos incompletos, esperar más
                self.v_print(f"Incomplete data received, buffering... Buffer: {buffer}")
                continue

    def handle_update(self, update_data):
        # Mostrar la actualización (JSON de datos de CorporateData) [cite: 315]
        output_content = json.dumps(update_data, indent=4)
        self.v_print(f"Update received: {output_content}")
        
        if self.output_file:
            # En modo observador, es mejor "append" que "write"
            try:
                with open(self.output_file, 'a') as f:
                    f.write(output_content + "\n") # Añadir nueva línea entre JSONs
            except IOError as e:
                print(f"Error appending to output file: {e}", file=sys.stderr)
        else:
            print(output_content)

if __name__ == "__main__":
    # Configurar argparse para -s, -p, -o, -v [cite: 139, 301]
    parser = argparse.ArgumentParser(description="Observer Client for TPFI IS2.")
    parser.add_argument("-s", dest="server_host", default="localhost", help="Server host (default: localhost).")
    parser.add_argument("-p", dest="server_port", type=int, default=8080, help="Server port (default: 8080).")
    parser.add_argument("-o", dest="output_file", help="Optional output file to append notifications.")
    parser.add_argument("-v", action="store_true", help="Enable verbose/debug mode.")
    
    args = parser.parse_args()

    client = ObserverClient(
        host=args.server_host,
        port=args.server_port,
        output_file=args.output_file,
        verbose=args.v
    )
    client.connect() # Iniciar el bucle de conexión/escucha