# singletonclient.py
# Dependencias que listaste: socket, json, uuid, platform, argparse [cite: 133]
import socket
import json
import uuid
import platform
import argparse
import sys

class SingletonClient:
    def __init__(self, host, port, input_file, output_file, verbose):
        self.host = host
        self.port = port
        self.input_file = input_file
        self.output_file = output_file
        self.verbose = verbose
        # Obtener el UUID de la CPU como se pide [cite: 385]
        self.cpu_uuid = str(uuid.getnode()) 

    def v_print(self, message):
        # Imprimir mensajes de debug si -v está activado [cite: 276, 400]
        if self.verbose:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def load_request(self):
        # Cargar el archivo JSON de entrada [cite: 162, 279]
        try:
            with open(self.input_file, 'r') as f:
                request_data = json.load(f)
            
            # Insertar el UUID de la CPU en la solicitud [cite: 282, 287]
            request_data['UUID'] = self.cpu_uuid
            
            self.v_print(f"Request data loaded: {request_data}")
            return request_data
        except FileNotFoundError:
            print(f"Error: Input file '{self.input_file}' not found.", file=sys.stderr)
            return None
        except json.JSONDecodeError:
            print(f"Error: Input file '{self.input_file}' is not valid JSON.", file=sys.stderr)
            return None

    def send_request(self):
        request_json = self.load_request()
        if request_json is None:
            return

        try:
            # Conectar al servidor vía socket TCP [cite: 74, 297]
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                self.v_print(f"Connected to server at {self.host}:{self.port}")
                
                # Enviar la solicitud JSON
                s.sendall(json.dumps(request_json).encode('utf-8'))
                self.v_print("Request sent.")

                # Recibir la respuesta (leer hasta que el servidor cierre la conexión)
                chunks = []
                try:
                    s.shutdown(socket.SHUT_WR)  # Indicar que no enviaremos más datos
                except OSError:
                    pass
                while True:
                    data_chunk = s.recv(4096)
                    if not data_chunk:
                        break
                    chunks.append(data_chunk)
                response_data = b"".join(chunks)
                response_str = response_data.decode('utf-8')
                self.v_print(f"Raw response received: {response_str}")

                try:
                    response_json = json.loads(response_str)
                    self.handle_response(response_json)
                except json.JSONDecodeError:
                    self.v_print("Failed to decode JSON response. Printing raw.")
                    self.handle_response(response_str) # Mostrar error o texto plano

        except socket.error as e:
            print(f"Socket Error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)

    def handle_response(self, response):
        # Manejar la respuesta: guardar en archivo -o o imprimir en salida estándar [cite: 76, 285]
        output_content = json.dumps(response, indent=4)
        
        if self.output_file:
            try:
                with open(self.output_file, 'w') as f:
                    f.write(output_content)
                self.v_print(f"Response saved to {self.output_file}")
            except IOError as e:
                print(f"Error writing to output file: {e}", file=sys.stderr)
        else:
            # Imprimir a salida estándar
            print(output_content)

if __name__ == "__main__":
    # Configurar argparse para los argumentos -i, -o, -v [cite: 131, 276]
    # (También agregué -s y -p para la dirección del servidor)
    parser = argparse.ArgumentParser(description="Singleton Client for TPFI IS2.")
    parser.add_argument("-i", dest="input_file", required=True, help="Input JSON file with the request.")
    parser.add_argument("-o", dest="output_file", help="Optional output JSON file to store the response.")
    parser.add_argument("-v", action="store_true", help="Enable verbose/debug mode.")
    parser.add_argument("-s", dest="server_host", default="localhost", help="Server host (default: localhost).")
    parser.add_argument("-p", dest="server_port", type=int, default=8080, help="Server port (default: 8080).")
    
    args = parser.parse_args()

    client = SingletonClient(
        host=args.server_host,
        port=args.server_port,
        input_file=args.input_file,
        output_file=args.output_file,
        verbose=args.v
    )
    client.send_request()