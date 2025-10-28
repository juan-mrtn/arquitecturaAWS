# db_manager.py
# Implementa el patrón Singleton para gestionar el acceso a DynamoDB
import boto3
import logging
import uuid
from datetime import datetime

class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            try:
                # Configurar Boto3. Asume que AWS CLI ya está configurado
                cls._instance.dynamodb = boto3.resource('dynamodb')
                cls._instance.corporate_data_table = cls._instance.dynamodb.Table('CorporateData')
                cls._instance.corporate_log_table = cls._instance.dynamodb.Table('CorporateLog')
                logging.info("Singleton DatabaseManager instance created. Connected to DynamoDB.")
            except Exception as e:
                logging.error(f"Failed to connect to DynamoDB: {e}")
                cls._instance = None
        return cls._instance

    def get_corporate_data(self, item_id):
        try:
            response = self.corporate_data_table.get_item(Key={'id': item_id})
            return response.get('Item')
        except Exception as e:
            logging.error(f"Error getting item {item_id} from CorporateData: {e}")
            return None

    def list_corporate_data(self):
        try:
            response = self.corporate_data_table.scan()
            return response.get('Items', [])
        except Exception as e:
            logging.error(f"Error scanning CorporateData: {e}")
            return []

    def set_corporate_data(self, item_data):
        # Esto crea o actualiza el item
        try:
            # Asumimos que item_data es un dict que incluye la 'id'
            self.corporate_data_table.put_item(Item=item_data)
            logging.info(f"Item set in CorporateData: {item_data.get('id')}")
            return item_data
        except Exception as e:
            logging.error(f"Error setting item in CorporateData: {e}")
            return None
    
    def log_action(self, client_uuid, session_id, action, details=""):
        # Registrar en CorporateLog
        try:
            log_entry = {
                'id': str(uuid.uuid4()),  # ID único para el log
                'UUID': client_uuid,
                'session': session_id,
                'action': action,
                'timestamp': datetime.now().isoformat(),
                'details': details
            }
            self.corporate_log_table.put_item(Item=log_entry)
            logging.info(f"Action logged: {action} by {client_uuid}")
        except Exception as e:
            logging.error(f"Error writing to CorporateLog: {e}")

