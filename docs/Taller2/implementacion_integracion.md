# Fase 3: Implementación e Integración del Código

Aquí explico cómo se conectan las piezas del sistema RAG en código real, incluyendo decisiones específicas sobre el flujo, manejo de fallback, y evaluación. Las decisiones de las fases 1 y 2 se materializan acá.

## Estructura del código

El sistema RAG agrega tres scripts nuevos al proyecto sin tocar los del Taller 1:

```
scripts/
├── order_query.py              (Taller 1, sin cambios)
├── return_query.py             (Taller 1, sin cambios)
├── build_knowledge_base.py     (Taller 2, indexa documentos)
├── rag_query.py                (Taller 2, sistema RAG principal)
└── evaluate_rag.py             (Taller 2, evaluación)
```

Mantuve los scripts del Taller 1 intactos por dos razones: primero, para no romper lo que ya funcionaba; segundo, para mostrar la evolución del sistema. Los scripts del Taller 1 son útiles para preguntas estructuradas específicas (consultar un pedido por número), mientras que el RAG cubre preguntas abiertas en lenguaje natural.

## Flujo del sistema RAG

El script principal es `rag_query.py`. Su flujo es directo pero tiene varias capas que vale la pena explicar:

### 1. Inicialización (una sola vez por sesión)

```python
# Cargar la API key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Cargar el modelo de embeddings (mismo que usamos para indexar)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

# Cargar la base vectorial
vectorstore = Chroma(
    collection_name="ecomarket_knowledge_base",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

# Inicializar Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3
)
```

**Decisión clave: temperatura baja (0.3).** Para un sistema de servicio al cliente queremos respuestas consistentes, no creativas. Una temperatura más alta podría dar respuestas variadas a la misma pregunta, lo cual es inaceptable para soporte. 0.3 es lo suficientemente bajo para consistencia, pero deja algo de variación natural en el lenguaje.

### 2. Búsqueda en la base de conocimiento

Cuando llega una pregunta del usuario, el primer paso es buscar fragmentos relevantes:

```python
results_with_scores = vectorstore.similarity_search_with_score(
    question, 
    k=4  # Recuperamos los 4 más similares
)
```

**¿Por qué 4 chunks?** Probé diferentes valores:
- Con 2 chunks, a veces faltaba contexto para preguntas más amplias
- Con 8 chunks, había mucho ruido y Gemini se distraía
- Con 4 chunks, el balance era óptimo: suficiente contexto sin saturar

**Por qué `similarity_search_with_score` y no solo `similarity_search`:** necesito el score de similitud para implementar el fallback. Sin scores, no puedo saber si los resultados son relevantes o si el sistema está "agarrándose de un clavo ardiendo".

### 3. Capa 1 de fallback: detección de baja relevancia

Aquí está una de las decisiones más importantes del sistema. ChromaDB devuelve cada resultado con un score de distancia (con embeddings normalizados, valores menores significan más similitud).

```python
best_score = results_with_scores[0][1]

if best_score > RELEVANCE_THRESHOLD:
    return get_fallback_response()
```

**¿Cómo escogí el threshold de 1.2?** Esto requirió experimentación:

1. Ejecuté preguntas que SÍ deberían tener respuesta y vi qué scores producían (típicamente entre 0.5 y 1.0)
2. Ejecuté preguntas fuera de alcance (como "¿qué es la fórmula de la coca cola?") y vi sus scores (típicamente arriba de 1.3)
3. Escogí 1.2 como punto medio, prefiriendo errar del lado de pedir información cuando no estoy seguro

Este número no es perfecto. Podría calibrarse mejor con más datos reales, pero para el taller sirve como demostración del concepto.

### 4. Construcción del prompt aumentado

Si los resultados son relevantes, formateamos el contexto y construimos el prompt:

```python
# Formatear los chunks recuperados de forma legible
context = "\n\n---\n\n".join([
    f"[Fragmento {i} - Fuente: {doc.metadata['source']}]\n{doc.page_content}"
    for i, doc in enumerate(retrieved_docs, 1)
])

# Cargar el template del prompt (desde archivo externo)
prompt = PromptTemplate.from_template(prompt_template)

# Crear la cadena: prompt → LLM → output
chain = prompt | llm | StrOutputParser()

answer = chain.invoke({
    "context": context,
    "question": question
})
```

**Decisión clave: prompt como archivo externo.** Igual que en el Taller 1, los prompts viven en `prompts/rag_query_prompt.txt`. Esto permite:
- Iterar sobre el prompt sin tocar código
- Versionar cambios del prompt en git
- Que alguien no técnico pueda mejorar el prompt
- Hacer A/B testing más fácil

### 5. Capa 2 de fallback: prompt anti-alucinación

El prompt en sí es la segunda capa de protección. Le indica explícitamente a Gemini:

> "Responde la pregunta del cliente basándote EXCLUSIVAMENTE en el contexto recuperado. NUNCA inventes información sobre productos, precios, políticas, tiempos de entrega o cualquier dato específico."

Y también:

> "Si el contexto NO contiene información suficiente para responder con certeza:
> - Indica honestamente que no tienes esa información específica
> - NO intentes adivinar ni inventar datos"

Aún cuando los chunks recuperados sean técnicamente "relevantes" según el score, puede ser que no contengan la respuesta exacta. En esos casos, el prompt instruye a Gemini a reconocer la limitación en lugar de inventar.

### 6. Capa 3 de fallback: respuesta estructurada

Cuando se activa el fallback (porque el retrieval no encontró nada relevante), no devolvemos solo "no sé". Devolvemos un mensaje útil:

```python
def get_fallback_response():
    return """Lo siento, no tengo información específica sobre tu consulta...

Puedo ayudarte con:
- Estado y seguimiento de pedidos
- Políticas de devolución
- Información sobre productos
- Tiempos y costos de envío

Si tu consulta es sobre otro tema, te recomiendo:
- Visitar nuestra página web
- Escribir a soporte@ecomarket.com
- Contactarnos por WhatsApp"""
```

Esto convierte un "no sé" frustrante en una respuesta útil que: reconoce la limitación, comunica qué SÍ puede hacer el sistema, y da rutas alternativas para resolver la consulta.

### 7. Capa 4 de fallback: registro de preguntas no respondidas

Cuando se activa el fallback, registramos la pregunta:

```python
def log_unanswered_question(question, best_score):
    log_file = LOGS_DIR / "unanswered_questions.log"
    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().isoformat()
        f.write(f"{timestamp} | Score: {best_score:.4f} | Pregunta: {question}\n")
```

¿Para qué? Estas son las preguntas que nuestro sistema NO sabe responder. Revisarlas regularmente identifica gaps en la base de conocimiento. Si vemos muchas preguntas sobre un tema que no cubrimos, sabemos qué documento agregar.

En producción, esto se podría conectar a un dashboard o a Slack para alertas. Para el taller, un archivo de log demuestra el concepto.

## Cómo se conectan las piezas

Visualicemos el flujo completo:

```
Usuario hace pregunta en español
        ↓
Embeddings convierten la pregunta en vector
        ↓
ChromaDB busca los 4 chunks más similares
        ↓
¿Score < 1.2 (suficientemente relevante)?
        ↓ NO                          ↓ SÍ
   Activar fallback              Construir prompt aumentado
   Registrar pregunta             con contexto + pregunta
        ↓                              ↓
Devolver mensaje                  Enviar a Gemini
estructurado                          ↓
                                Gemini genera respuesta
                                basada solo en el contexto
                                      ↓
                              Devolver al usuario
```

Cada componente tiene una responsabilidad clara:
- **Embeddings:** Convertir texto a vectores (entender el significado)
- **ChromaDB:** Buscar por similitud (encontrar lo relevante)
- **Threshold de relevancia:** Decidir si lo encontrado es bueno suficiente
- **Prompt:** Instruir a Gemini cómo usar el contexto
- **Gemini:** Generar respuesta natural en español
- **Fallback:** Manejar casos donde no hay respuesta

## Evaluación del sistema

Para validar que todo esto funciona, escribí `evaluate_rag.py` que ejecuta 25 preguntas de prueba contra el sistema y mide tres cosas:

### Calidad del retrieval

¿El sistema está recuperando documentos de la fuente correcta? Por ejemplo, si pregunto sobre tiempos de envío, ¿está recuperando chunks de `shipping_policy` o se confunde y trae chunks de `faqs`?

**Métrica:** porcentaje de preguntas donde al menos uno de los chunks recuperados es de la fuente esperada.

### Manejo de fallback

¿El sistema reconoce cuando no tiene información? Las preguntas como "¿venden iPhones?" o "¿cuál es la receta del ajiaco?" deberían activar fallback.

**Métrica:** de las preguntas que SÍ deberían activar fallback, ¿cuántas lo activaron correctamente?

### Tiempo de respuesta

Medimos el tiempo total para cada pregunta. En producción esto importa para la experiencia del usuario.

**Métrica:** tiempo promedio de respuesta.

### Las 25 preguntas de prueba

El archivo `evaluation/test_questions.json` contiene preguntas diversas:

- 10 preguntas que deberían responderse desde la base de conocimiento (envíos, devoluciones, productos, FAQs)
- 5 preguntas que requieren combinar información de múltiples fuentes
- 5 preguntas fuera de alcance que deberían activar fallback (recetas, deportes, productos no vendidos, etc.)
- 5 preguntas con variaciones de fraseo para probar robustez

Estas categorías están diseñadas para probar diferentes capacidades del sistema.

## Limitaciones y suposiciones

Como pide el taller, voy a ser explícito sobre las limitaciones del sistema actual:

**Suposición 1: Volumen pequeño.** El sistema funciona perfecto con 60-80 chunks. Si EcoMarket creciera a miles de productos y políticas, ChromaDB podría empezar a sentirse lenta. La solución sería migrar a un servicio gestionado como Pinecone o Qdrant.

**Suposición 2: Documentos en español.** El modelo de embeddings funciona en muchos idiomas, pero está optimizado para textos relativamente formales. Si los clientes usan mucho slang colombiano o regionalismos fuertes, el retrieval puede fallar. En producción habría que probar y posiblemente ajustar.

**Suposición 3: Documentos relativamente estáticos.** Construir la base toma 30-60 segundos (depende de la velocidad del modelo de embeddings). Para documentos que cambian todo el tiempo, esto sería problemático. Para EcoMarket, donde las políticas se actualizan máximo una vez al mes, está bien.

**Limitación 1: No hay reranking.** Después del retrieval inicial, podríamos agregar un paso de reranking con un modelo más especializado para reordenar los resultados. Esto mejoraría la calidad del retrieval pero agrega latencia. Decidí no incluirlo para mantener simplicidad.

**Limitación 2: Sin búsqueda híbrida.** Combinar BM25 (palabras clave) con búsqueda vectorial mejoraría la robustez, especialmente para términos específicos como nombres de productos o códigos. ChromaDB no lo soporta nativamente y agregarlo manualmente complicaría el código.

**Limitación 3: El threshold es estático.** Idealmente, el threshold para activar fallback se ajustaría dinámicamente según el tipo de pregunta o aprendería de feedback de usuarios. Por ahora es un número fijo basado en experimentación.

**Limitación 4: No hay memoria conversacional.** Si un usuario hace una pregunta de seguimiento ("¿y cuánto cuesta ese?"), el sistema no recuerda la conversación previa. Para este alcance, cada pregunta es independiente. LangChain tiene módulos de memoria que podríamos agregar.

**Limitación 5: Solo un idioma a la vez.** Si un cliente escribe parte en español y parte en inglés, el sistema puede confundirse. Aunque el modelo es multilingüe, los chunks están en español, lo cual sesga el retrieval.

**Limitación de recursos del taller:** Como esto es un proyecto académico, no tenemos infraestructura de monitoreo en producción, no tenemos datos reales de clientes para entrenar o evaluar mejor, y no tenemos un equipo humano de respaldo para escalación. Lo que sí podemos demostrar es que la arquitectura está pensada para integrarse a esos sistemas cuando existan.

## Cómo probar el sistema

El flujo para probar todo:

```bash
# 1. Activar el venv y instalar dependencias nuevas
source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt

# 2. Construir la base de conocimiento (una sola vez)
python scripts/build_knowledge_base.py

# 3. Probar interactivamente
python scripts/rag_query.py

# 4. Evaluar el sistema
python scripts/evaluate_rag.py
```

Si todo funciona, deberías poder hacer preguntas como:
- "¿Cuánto cuesta el envío a Bogotá?"
- "¿Puedo devolver un cepillo de bambú?"
- "¿En qué fragancias viene el champú sólido?"

Y deberías recibir respuestas en español natural, basadas en los documentos de la base de conocimiento. Si preguntas algo fuera de alcance, debería activarse el fallback.

## Cómo modificar el sistema

Una de las ventajas de tener cada pieza separada es que puedes experimentar fácilmente:

**Para probar otros prompts:** edita `prompts/rag_query_prompt.txt`, no necesitas tocar código.

**Para cambiar el modelo de embeddings:** modifica `EMBEDDING_MODEL` en ambos scripts (`build_knowledge_base.py` y `rag_query.py`). Necesitas reconstruir la base.

**Para ajustar el threshold de fallback:** cambia `RELEVANCE_THRESHOLD` en `rag_query.py`. No necesitas reconstruir nada.

**Para agregar nuevos documentos:** agrega el archivo en `data/`, escribe una función `load_X()` en `build_knowledge_base.py`, llámala en `build_knowledge_base()`, y ejecuta el script.

**Para cambiar a otro LLM:** modifica la inicialización de `llm` en `rag_query.py`. Por ejemplo, podrías cambiar a Claude o GPT-4 cambiando el provider de LangChain.

Esta modularidad fue intencional. Un sistema RAG en producción se ajusta constantemente, así que hacer las decisiones fáciles de cambiar es importante.
