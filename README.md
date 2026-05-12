# EcoMarket - Atención al Cliente con IA

Sistema de atención al cliente con inteligencia artificial para EcoMarket, empresa de productos sostenibles. El proyecto cubre dos talleres y un proyecto final:

- **Taller 1:** Sistema básico con prompts directos para consultas de estado de pedidos y política de devoluciones.
- **Taller 2:** Sistema RAG (Generación Aumentada por Recuperación) que extiende las capacidades del modelo para responder cualquier consulta basándose en una base de conocimiento de la empresa.
- **Proyecto Final:** Agente de IA para gestionar devoluciones, con router RAG/agente, tools, LangSmith e interfaz Streamlit.

---

## Estructura del Proyecto

```
ai-workshop-ecomarket/
├── data/
│   ├── orders.json                    # Datos de pedidos de prueba (Taller 1)
│   ├── return_policies.json           # Políticas de devolución por producto
│   ├── faqs.json                      # Preguntas frecuentes (Taller 2)
│   ├── product_catalog.json           # Catálogo de productos (Taller 2)
│   └── shipping_policy.md             # Política de envíos (Taller 2)
├── docs/
│   ├── Taller1/
│   │   ├── FASE1.md                   # Selección del modelo de IA
│   │   └── FASE2.md                   # Análisis crítico del sistema básico
│   ├── Taller2/
│   │   ├── seleccion_componentes.md   # Selección de embeddings y base vectorial
│   │   ├── base_conocimiento.md       # Construcción de la base de conocimiento y chunking
│   │   └── implementacion_integracion.md  # Implementación, evaluación y limitaciones
│   └── ProyectoFinal/
│       ├── fase1_arquitectura_agente.md
│       ├── fase2_implementacion_conexion.md
│       ├── fase3_analisis_critico.md
│       ├── fase4_despliegue.md
│       └── langsmith_setup.md
├── prompts/
│   ├── order_query_prompt.txt         # Prompt para consultas de pedidos
│   ├── return_query_prompt.txt        # Prompt para consultas de devoluciones
│   ├── rag_query_prompt.txt           # Prompt para el sistema RAG
│   └── return_agent_prompt.txt        # Prompt del agente de devoluciones
├── scripts/
│   ├── order_query.py                 # Consulta de estado de pedido (Taller 1)
│   ├── return_query.py                # Consulta de política de devolución (Taller 1)
│   ├── build_knowledge_base.py        # Construye la base de conocimiento RAG (Taller 2)
│   ├── rag_query.py                   # Sistema RAG principal (Taller 2)
│   ├── evaluate_rag.py                # Evaluación del sistema (Taller 2)
│   ├── return_tools.py                # Tools determinísticas de devoluciones
│   ├── return_agent.py                # Agente LangChain de devoluciones
│   ├── customer_service_router.py     # Router entre RAG y agente
│   ├── langsmith_config.py            # Configuración opcional de LangSmith
│   └── evaluate_agent.py              # Evaluación del router/agente
├── evaluation/
│   ├── test_questions.json            # Preguntas de prueba para RAG
│   └── agent_test_cases.json          # Casos de prueba para router/agente
├── app.py                             # Interfaz Streamlit del proyecto final
├── chroma_db/                         # Base vectorial (generada al indexar)
├── logs/                              # Registro de preguntas sin respuesta
├── .env                               # Tu API key (no subir al repositorio)
├── .env.example                       # Plantilla de configuración
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Configuración Inicial

### 1. Clonar el Repositorio

```bash
git clone https://github.com/yourusername/ai-workshop-ecomarket.git
cd ai-workshop-ecomarket
```

### 2. Crear un Entorno Virtual

Un entorno virtual mantiene las dependencias del proyecto aisladas del Python del sistema.

**En macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**En Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

Cuando esté activado, verás `(venv)` al inicio del prompt de la terminal.

### 3. Instalar Dependencias

Con el entorno virtual activado:

```bash
pip install -r requirements.txt
```

Esto instala todas las dependencias del proyecto, incluyendo las del Taller 1 (Gemini, dotenv) y las del Taller 2 (LangChain, ChromaDB, sentence-transformers).

**Nota sobre la primera instalación:** El paquete `sentence-transformers` y sus dependencias son grandes (~500MB). La primera instalación puede tardar varios minutos.

### 4. Obtener una API Key de Google Gemini

1. Ve a [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Inicia sesión con tu cuenta de Google
3. Haz clic en "Crear API Key"
4. Copia la clave generada

La API es gratuita y no requiere tarjeta de crédito.

### 5. Configurar la API Key

Crea un archivo `.env` con tu API key. Hay dos formas:

**Opción A: Copiar desde el archivo de ejemplo (recomendado)**
```bash
cp .env.example .env
```

Luego edita `.env` y reemplaza el placeholder con tu clave real:
```
GOOGLE_API_KEY=tu-clave-api-aquí
```

Opcionalmente, para ver trazas en LangSmith:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=tu-clave-langsmith-aquí
LANGSMITH_PROJECT=ecomarket-final-agent
```

**Opción B: Crear `.env` manualmente**
```bash
echo "GOOGLE_API_KEY=tu-clave-api-aquí" > .env
```

**Importante:** Nunca subas tu archivo `.env` al repositorio. Ya está en `.gitignore` para evitar commits accidentales.

---

## Taller 1: Sistema Básico con Prompts Directos

### Consulta de Estado de Pedido

```bash
python scripts/order_query.py
```

Pedirá un número de pedido (por ejemplo, 12345, 12346) y devolverá el estado actual con información de envío.

**Ejemplo de interacción:**
```
ECOMARKET - CONSULTA DE ESTADO DE PEDIDO
Ingresa el número de pedido (ej. 12345): 12345

Buscando tu pedido...

RESPUESTA:
¡Hola! Encontré tu pedido #12345. Actualmente está en tránsito
y debería llegar el 20 de abril de 2026.
```

### Consulta de Política de Devolución

```bash
python scripts/return_query.py
```

Pedirá el nombre de un producto y dirá si puede devolverse, en cuántos días y bajo qué condiciones.

**Ejemplo de interacción:**
```
ECOMARKET - CONSULTA DE POLÍTICA DE DEVOLUCIÓN
Ingresa el nombre del producto: Botella de bambú

Verificando política de devolución...

RESPUESTA:
Buenas noticias: la botella de agua reutilizable de bambú puede devolverse
dentro de los 30 días si no ha sido usada y está en su empaque original.
```

---

## Taller 2: Sistema RAG

El sistema RAG funciona en tres pasos: indexar, consultar y evaluar.

### Paso 1: Construir la Base de Conocimiento

Antes de hacer consultas, hay que indexar los documentos en ChromaDB. Esto se hace una sola vez (o cada vez que cambien los documentos):

```bash
python scripts/build_knowledge_base.py
```

Este script:
1. Carga los documentos de la carpeta `data/` (FAQs, devoluciones, catálogo, envíos)
2. Aplica chunking específico según el tipo de documento
3. Genera embeddings con un modelo multilingüe
4. Almacena todo en ChromaDB

**Primera vez:** Descargará el modelo de embeddings (~500MB), lo cual puede tardar varios minutos.

**Veces siguientes:** Solo regenera la base de conocimiento, en unos 30 segundos.

### Paso 2: Consultar el Sistema RAG

```bash
python scripts/rag_query.py
```

Abre un prompt interactivo donde puedes hacer preguntas en español. Por ejemplo:

```
Tu pregunta: ¿Cuánto cuesta el envío a Bogotá?

[Buscando información relevante...]

RESPUESTA:
El envío estándar a Bogotá cuesta $8.000 COP y tarda entre 2 y 3 días
hábiles. También hay opción de envío express por $15.000 COP que llega
en 1 día hábil. Si tu compra supera los $150.000 COP, el envío estándar
es gratis.

¿Hay algo más en lo que pueda ayudarte?
```

Para salir del modo interactivo, escribe `salir` (o `exit` / `quit`).

### Paso 3: Evaluar el Sistema

```bash
python scripts/evaluate_rag.py
```

Este script ejecuta 25 preguntas de prueba (definidas en `evaluation/test_questions.json`) y mide:

- **Calidad del retrieval:** ¿Está recuperando los documentos correctos?
- **Manejo de fallback:** ¿Reconoce cuándo no tiene información?
- **Tiempo de respuesta:** ¿Cuánto tarda en promedio?

Los resultados se guardan en `evaluation/results.json`.

---

## Proyecto Final: Agente de Devoluciones

El proyecto final agrega un router de atención al cliente. Las preguntas informativas siguen usando el RAG del Taller 2, mientras que las solicitudes accionables de devolución se envían a un agente LangChain.

### Probar las tools determinísticas

```bash
python scripts/return_tools.py eligibility --order-id 12345 --product botella de bambu
python scripts/return_tools.py label --order-id 12345 --product botella de bambu
```

### Probar el agente directamente

```bash
python scripts/return_agent.py \
  --message "Quiero devolver la botella de bambu del pedido 12345" \
  --json
```

### Probar el router RAG/agente

```bash
python scripts/customer_service_router.py \
  --message "Quiero devolver la botella de bambu del pedido 12345" \
  --json
```

Para revisar solo la ruta sin llamar a Gemini:

```bash
python scripts/customer_service_router.py \
  --message "Cuanto cuesta el envio a Medellin?" \
  --classify-only
```

### Evaluar el router/agente

Modo seguro, sin llamadas al modelo:

```bash
python scripts/evaluate_agent.py --no-save
```

Modo completo, con Gemini:

```bash
python scripts/evaluate_agent.py --live
```

### Ver trazas en LangSmith

Configura `.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=tu-clave-langsmith-aquí
LANGSMITH_PROJECT=ecomarket-final-agent
```

Luego ejecuta el router o el agente. Las trazas aparecerán en el proyecto `ecomarket-final-agent`.

Más detalle en `docs/ProyectoFinal/langsmith_setup.md`.

### Ejecutar la interfaz web

```bash
streamlit run app.py
```

Con el entorno virtual del proyecto:

```bash
venv/bin/streamlit run app.py
```

URL local esperada:

```text
http://localhost:8501
```

Prompts recomendados para la sustentación:

- `Quiero devolver la botella de bambu del pedido 12345`
- `Quiero devolver el champu solido del pedido 12347`
- `Quiero devolver el panel solar del pedido 12351`
- `Cuanto cuesta el envio a Medellin?`

---

## Preguntas que Puede Responder el Sistema RAG

### Envíos

- ¿Cuánto cuesta el envío a Bogotá?
- ¿Cuánto tarda un envío a Medellín?
- ¿Cuánto tarda el envío express a Cali?
- ¿Qué transportadora usan para los envíos?
- ¿Hacen envíos a otros países?
- ¿Hay envío gratis? ¿Desde qué monto?
- ¿Hacen envíos a municipios pequeños?
- ¿Qué pasa si no hay nadie para recibir el pedido?
- ¿Puedo cambiar la dirección de envío después de hacer el pedido?
- ¿Cuándo no hacen despachos?

### Devoluciones

- ¿Puedo devolver el champú sólido?
- ¿Puedo devolver la botella de bambú?
- ¿Puedo devolver el cepillo de dientes de bambú?
- ¿Cuánto tiempo tengo para devolver un producto?
- ¿Quién paga el envío de la devolución?
- ¿Cuáles productos no se pueden devolver?

### Productos

- ¿Cuánto cuesta el panel solar portátil?
- ¿En qué fragancias viene el champú sólido?
- ¿En qué fragancias viene el jabón natural?
- ¿Qué características tiene la botella de bambú?
- ¿De qué material está hecha la bolsa tote?
- ¿El compostador funciona para apartamentos?
- ¿Qué garantía tiene el panel solar?
- ¿Cuántos litros filtra el filtro de carbón activado?
- ¿Los recipientes de vidrio son aptos para microondas?
- ¿En qué colores vienen las toallas de bambú?
- ¿Qué certificaciones tienen sus productos?

### Cuenta y Pagos

- ¿Cómo creo una cuenta en EcoMarket?
- ¿Cómo recupero mi contraseña?
- ¿Cómo cambio mi dirección de envío?
- ¿Qué métodos de pago aceptan?
- ¿Es seguro pagar en EcoMarket?
- ¿Puedo pagar en cuotas?

### Pedidos

- ¿Cómo hago seguimiento a mi pedido?
- ¿Puedo modificar mi pedido después de realizarlo?
- ¿Puedo cancelar mi pedido?

### Sostenibilidad y Soporte

- ¿Sus productos son realmente sostenibles?
- ¿Qué hago si recibo un producto defectuoso?
- ¿Tienen tienda física?
- ¿Tienen programa de reciclaje?
- ¿Qué tipo de empaque usan?
- ¿Cuál es el horario de atención?
- ¿Cómo puedo contactarlos?

Para preguntas fuera del alcance del sistema (recetas, deportes, productos que no vende EcoMarket, etc.), el sistema activa un mensaje de fallback que sugiere alternativas.

---

## Documentación Detallada

### Taller 1
- [docs/Taller1/FASE1.md](docs/Taller1/FASE1.md) — Por qué Google Gemini Pro
- [docs/Taller1/FASE2.md](docs/Taller1/FASE2.md) — Análisis crítico del sistema básico

### Taller 2 (Sistema RAG)
- [docs/Taller2/seleccion_componentes.md](docs/Taller2/seleccion_componentes.md) — Selección del modelo de embeddings y base de datos vectorial
- [docs/Taller2/base_conocimiento.md](docs/Taller2/base_conocimiento.md) — Construcción de la base de conocimiento y estrategias de chunking
- [docs/Taller2/implementacion_integracion.md](docs/Taller2/implementacion_integracion.md) — Implementación, integración del código, evaluación y limitaciones

---

## Stack Tecnológico

| Componente | Tecnología | Costo |
|------------|-----------|-------|
| LLM | Google Gemini 2.5 Flash | Gratis |
| Modelo de embeddings | sentence-transformers/paraphrase-multilingual-mpnet-base-v2 | Gratis (corre local) |
| Base de datos vectorial | ChromaDB | Gratis |
| Framework | LangChain | Gratis |
| Lenguaje | Python 3.9+ | Gratis |

Todo el stack es gratuito y corre localmente. No se requiere infraestructura ni servicios pagos.

---

## Solución de Problemas

### "GOOGLE_API_KEY not found"

Verifica que tienes el archivo `.env` con tu API key:

```bash
cat .env  # Debería mostrar GOOGLE_API_KEY=AIza...
```

Si no existe, créalo: `cp .env.example .env` y edítalo.

### "La base de conocimiento no existe"

Si ejecutas `rag_query.py` sin haber indexado primero, obtendrás este error. Solución:

```bash
python scripts/build_knowledge_base.py
```

### El modelo de embeddings tarda mucho en descargar

Esto es normal en la primera ejecución. El modelo pesa ~500MB. Las ejecuciones siguientes usan la caché local.

### Errores al instalar dependencias

Si tienes problemas instalando `sentence-transformers` o `chromadb`, verifica que tienes Python 3.9 o superior:

```bash
python --version
```

### Problemas con el Entorno Virtual

**Para desactivar:**
```bash
deactivate
```

**Para reiniciar completamente:**
```bash
deactivate  # si está activo
rm -rf venv
python3 -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt
```

---

## Al Terminar

Desactiva el entorno virtual:

```bash
deactivate
```

La próxima vez que trabajes en el proyecto:

```bash
cd ai-workshop-ecomarket
source venv/bin/activate  # macOS/Linux
# o
venv\Scripts\activate     # Windows
```
