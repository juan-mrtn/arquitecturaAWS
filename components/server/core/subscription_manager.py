# subscription_manager.py
# Implementa el patrón Observer para gestionar suscripciones
import json
import logging
import threading
import socket

class SubscriptionManager:  # Este es el "Subject"
    _observers = []  # Lista de sockets de observadores
    _lock = threading.Lock()

    def attach(self, observer_socket):
        with self._lock:
            if observer_socket not in self._observers:
                self._observers.append(observer_socket)
                logging.info(f"New observer attached. Total: {len(self._observers)}")

    def detach(self, observer_socket):
        with self._lock:
            try:
                self._observers.remove(observer_socket)
                logging.info(f"Observer detached. Total: {len(self._observers)}")
            except ValueError:
                pass  # Ya no estaba en la lista

    def notify(self, message_json):  # Notificar a todos
        with self._lock:
            logging.info(f"Notifying {len(self._observers)} observers...")
            message_bytes = json.dumps(message_json).encode('utf-8')
            # Iterar sobre una copia por si la lista se modifica
            for observer in list(self._observers):
                try:
                    observer.sendall(message_bytes)
                except socket.error:
                    # El socket está roto o cerrado, eliminarlo
                    self.detach(observer)

