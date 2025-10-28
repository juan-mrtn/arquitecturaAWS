# TPFI IS2 - Arquitectura AWS Python

Proyecto que implementa patrones de diseño (Singleton, Observer, Proxy) en un servidor Python con AWS DynamoDB.

## Estructura del Proyecto

```
TPFI_IS2/
├── components/
│   ├── client/
│   │   ├── __init__.py
│   │   ├── singletonclient.py     # Cliente Singleton para operaciones get/set/list
│   │   └── observerclient.py      # Cliente Observer para recibir notificaciones
│   └── server/
│       ├── __init__.py
│       ├── singletonproxyobserver.py  # Servidor principal (main)
│       └── core/                  # Módulo para las clases de patrones
│           ├── __init__.py
│           ├── db_manager.py      # Implementa el patrón Singleton
│           └── subscription_manager.py # Implementa el patrón Observer
├── inputs/
│   ├── input_valid_get.json
│   ├── input_valid_set.json
│   └── input_valid_list.json
├── .gitignore                     # Ignora logs, outputs y credenciales
└── requirements.txt               # Dependencias (boto3, etc.)
```

## Instalación

1. Crear un entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate  # En Linux/Mac
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar AWS CLI con tus credenciales:
```bash
aws configure
```

## Uso

### Iniciar el Servidor

```bash
cd components/server
python singletonproxyobserver.py -p 8080 -v
```

### Ejecutar Cliente Singleton

#### Operación GET:
```bash
cd components/client
python singletonclient.py -i ../../inputs/input_valid_get.json -v
```

#### Operación SET:
```bash
python singletonclient.py -i ../../inputs/input_valid_set.json -o output_set.json -v
```

#### Operación LIST:
```bash
python singletonclient.py -i ../../inputs/input_valid_list.json -v
```

### Ejecutar Cliente Observer

```bash
python observerclient.py -s localhost -p 8080 -o observer_output.json -v
```

## Descripción de Componentes

### Servidor (singletonproxyobserver.py)
- Implementa tres patrones de diseño:
  - **Singleton**: Una única instancia de `DatabaseManager` para acceder a DynamoDB
  - **Observer**: Gestión de suscripciones y notificaciones
  - **Proxy**: Intercepta operaciones SET y notifica a observadores

### Clientes
- **SingletonClient**: Opera con AWS DynamoDB mediante operaciones get/set/list
- **ObserverClient**: Se suscribe a notificaciones de cambios en la base de datos

### Tablas DynamoDB
- `CorporateData`: Almacena los datos corporativos
- `CorporateLog`: Registra todas las acciones realizadas

## Patrones de Diseño Implementados

1. **Singleton**: `DatabaseManager` asegura una única conexión a DynamoDB
2. **Observer**: `SubscriptionManager` gestiona suscripciones y notificaciones
3. **Proxy**: El servidor intercepta operaciones SET y propagan cambios

## Requisitos
- Python 3.7+
- AWS Account con DynamoDB habilitado
- Tablas `CorporateData` y `CorporateLog` creadas en DynamoDB


# arquitecturaAWS
