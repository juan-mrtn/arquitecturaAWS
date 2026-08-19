# ADR 001: Migración de Entorno AWS Cloud a Emulación Local con Floci

## 1. Estado
**Aceptado**

## 2. Contexto
El sistema original (TPFI IS2) fue diseñado con una arquitectura Cliente-Servidor mediante Sockets TCP, donde el servidor (`singletonproxyobserver.py`) se conectaba directamente a la nube de AWS utilizando `boto3` para gestionar las tablas `CorporateData` y `CorporateLog` en DynamoDB. 

Si bien esta integración demostró la viabilidad del acceso a datos en la nube, presentó fricciones significativas para el ciclo de vida del desarrollo de software (SDLC):
* **Acoplamiento fuerte:** La dependencia estricta de una conexión a internet y credenciales reales de AWS dificultaba el desarrollo offline.
* **Costos y Riesgos:** Ejecutar la suite de pruebas automatizadas (`test_suite.py`) directamente contra infraestructura productiva genera consumos innecesarios (operaciones de lectura/escritura) y riesgo de manipulación de datos reales.
* **Fricción en el Onboarding:** Cualquier nuevo colaborador (o sistema de CI/CD) debía configurar credenciales de AWS y crear tablas manualmente antes de poder ejecutar el proyecto.

## 3. Decisión
Se ha decidido **desacoplar el entorno de desarrollo y testing de la nube real de AWS**, adoptando **Floci** como emulador local de servicios de AWS.

Las acciones técnicas implementadas incluyen:
1. **Inyección de Dependencias:** Modificación del patrón Singleton en `DatabaseManager` para aceptar el parámetro `endpoint_url` a través de variables de entorno, permitiendo redirigir el tráfico de `boto3` hacia el emulador local sin alterar la lógica de negocio.
2. **Contenedorización (Docker):** Inclusión de un archivo `docker-compose.yml` que orquesta la imagen oficial de Floci, estandarizando el entorno de ejecución.
3. **Infraestructura como Código (Efímera):** Implementación de scripts de inicialización (`init-hooks` / `awslocal`) para auto-provisionar las tablas de DynamoDB cada vez que se levanta el contenedor.

## 4. Consecuencias (Trade-offs)

### Positivas:
* **Reproducibilidad:** El entorno es 100% reproducible y efímero. Con un solo comando (`docker-compose up`), cualquier desarrollador tiene la infraestructura lista.
* **Testing Aislado:** La suite de pruebas ahora se ejecuta en un entorno *sandbox*, aislando los tests de integración y eliminando latencias de red, logrando ejecuciones en milisegundos.
* **Cero Costos:** Se elimina por completo el consumo facturable de DynamoDB durante el desarrollo y las pruebas.
* **CI/CD Ready:** El proyecto ahora está preparado para integrarse fácilmente en pipelines de GitHub Actions o GitLab CI.

### Negativas:
* **Requisito de Docker:** Introduce a Docker Engine y Docker Compose como dependencias obligatorias para poder correr el servidor localmente.
* **Paridad de Emulación:** Aunque Floci es altamente compatible, existe el riesgo inherente de que el emulador no replique con 100% de exactitud comportamientos muy específicos (edge cases) de la API real de DynamoDB. Se mitigará realizando pruebas de humo (smoke tests) contra la nube real antes de cualquier pase a producción.