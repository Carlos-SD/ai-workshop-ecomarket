# Fase 1: Selección de Componentes del Sistema RAG

Para extender el sistema del Taller 1 a un RAG completo, hay dos decisiones de arquitectura que importan más que las demás: qué modelo de embeddings usar y dónde guardar los vectores. Voy a explicar qué escogí y por qué, considerando que vamos a trabajar principalmente con documentos en español.

## Modelo de Embeddings: paraphrase-multilingual-mpnet-base-v2

Escogí este modelo de Hugging Face por tres razones principales:

**Funciona bien en español sin haberlo entrenado específicamente para eso.** Está entrenado con texto en más de 50 idiomas y aunque no es perfecto, captura suficientemente bien la semántica del español para responder preguntas de servicio al cliente. Para EcoMarket, donde las preguntas son relativamente directas ("¿cuánto cuesta el envío?", "¿puedo devolver esto?"), no necesitamos un modelo especializado en español.

**Es completamente gratis y corre local.** No paga por embedding generado (a diferencia de OpenAI o Cohere que cobran por cada llamada), no necesita API key, y no envía datos de la empresa a un tercero. Para un taller académico es lo ideal, pero también para un piloto de producción donde queremos validar el concepto antes de comprometernos con costos recurrentes.

**El balance entre velocidad y calidad es razonable.** Genera vectores de 768 dimensiones, lo cual es suficiente para nuestro caso. Modelos más grandes como `multilingual-e5-large` darían algo más de precisión pero son más lentos y pesados. Modelos más pequeños como `MiniLM` son más rápidos pero pierden bastante calidad en idiomas que no son inglés.

### Por qué no las otras opciones

**OpenAI text-embedding-3-small:** Es muy bueno y multilingüe, cuesta como $0.02 por millón de tokens (prácticamente nada). Pero requiere tarjeta de crédito y manda los datos al servidor de OpenAI. Para una empresa real con datos sensibles, esto importa. Para un taller, agrega un paso de configuración innecesario.

**Cohere embed-multilingual-v3:** A veces supera a OpenAI en español específicamente. Pero también cuesta, también requiere registro, y para nuestro caso de uso no justifica la complejidad adicional.

**hiiamsid/sentence_similarity_spanish_es:** Está entrenado puramente en español, así que en teoría debería ser mejor. En la práctica, los modelos multilingües modernos rinden muy parecido para texto general y este modelo es menos mantenido. Si EcoMarket fuera un sistema legal o médico en español puro, valdría la pena considerarlo.

**bge-m3 (BAAI):** Es uno de los mejores modelos open source de 2024-2025. Pero pesa mucho más (1.4GB vs 470MB) y para preguntas simples de servicio al cliente la diferencia de calidad no se nota.

### Lo que pierde nuestra elección

Voy a ser honesto sobre las limitaciones del modelo escogido:

- En textos largos y complejos, modelos más nuevos lo superan. Pero nuestros chunks son cortos.
- Las negaciones complicadas en español ("ningún producto que no sea retornable") pueden confundirlo. Vamos a mitigar esto con un prompt claro.
- La diferencia entre tú/usted, dialectos regionales y modismos puede no captarse bien. Para EcoMarket Colombia esto es manejable.

## Base de Datos Vectorial: ChromaDB

Para almacenar los vectores y hacer búsqueda por similitud, escogí ChromaDB. Esta decisión fue más fácil que la del modelo de embeddings.

**Cero configuración para empezar.** ChromaDB se instala con `pip` y se guarda como archivos en disco. No necesita servidor corriendo, no necesita autenticación, no necesita configurar buckets de cloud. Para un taller donde quieres ejecutar el código y que funcione, esto es invaluable.

**Open source y self-hosted.** Los datos se quedan en tu computadora o servidor. Para un piloto donde no estamos seguros del volumen ni del compromiso a largo plazo, esto reduce el riesgo de comprometernos con un servicio que después sea difícil migrar.

**Integración nativa con LangChain.** Como vamos a usar LangChain (que el taller menciona explícitamente), ChromaDB tiene un wrapper directo que hace la integración trivial. No tenemos que pelear con drivers ni APIs custom.

**Funciona bien para el volumen que necesitamos.** ChromaDB maneja sin problema hasta cientos de miles de vectores. Nosotros vamos a tener máximo unos 100-200 chunks, así que estamos lejos de los límites.

### Por qué no las otras opciones

**Pinecone:** Es un servicio gestionado muy bueno, escalable, con tier gratuito limitado. La razón principal por la que no lo escogí es que requiere registrarse, configurar API keys, y los datos viven en sus servidores. Para producción seria con millones de vectores, sí tiene sentido. Para nuestro caso, agrega complejidad sin beneficios reales.

**Weaviate:** Más poderoso que ChromaDB, soporta búsqueda híbrida nativa (BM25 + vectorial), y tiene features avanzados como filtrado complejo. La curva de aprendizaje es más empinada y para nuestras 4 fuentes de documentos no necesitamos esa potencia.

**Qdrant:** Buen middle ground entre simplicidad y poder. Para un proyecto académico ChromaDB es más conocido y tiene más documentación accesible. Para producción seria con escalamiento intenso, Qdrant sería una alternativa fuerte.

**Postgres con pgvector:** Si EcoMarket ya tuviera Postgres en producción para otras cosas, esta sería probablemente la mejor opción - reutilizar infraestructura existente. Pero asumimos que estamos empezando desde cero.

**FAISS de Facebook:** Muy rápido pero es solo una librería, no una base de datos. Para guardar los vectores y metadatos hay que escribir bastante código adicional. ChromaDB nos da todo eso sin trabajo extra.

### Lo que pierde nuestra elección

**Escalabilidad horizontal.** ChromaDB funciona en una sola máquina. Si EcoMarket creciera a millones de documentos, tendríamos que migrar. Pero para llegar a ese punto vamos a tener tiempo de planificar.

**Búsqueda híbrida nativa.** Combinar búsqueda por palabra clave (BM25) con búsqueda vectorial mejora bastante la calidad. ChromaDB no lo soporta directamente. Para preguntas de servicio al cliente, donde hay sinónimos y variaciones, podríamos perder algo de calidad. Si vemos que esto es un problema real, podemos agregar BM25 manualmente o migrar a Weaviate.

**Métricas y monitoring.** Servicios como Pinecone vienen con dashboards y alertas. ChromaDB es solo la base de datos, el monitoring tendríamos que armarlo aparte.

## Resumen de la decisión

| Componente | Elección | Costo | Complejidad |
|------------|----------|-------|-------------|
| Modelo de embeddings | paraphrase-multilingual-mpnet-base-v2 | Gratis | Baja |
| Base vectorial | ChromaDB local | Gratis | Muy baja |
| LLM (heredado del Taller 1) | Google Gemini | Gratis | Muy baja |
| Framework | LangChain | Gratis | Media |

Todo el stack es gratis, corre local en lo que es razonable, y se puede levantar en una computadora estándar sin GPU dedicada. La decisión de "lo más simple que funciona bien" guió cada elección.

Si las preguntas reales de los clientes empiezan a fallar consistentemente, el primer cambio que haría sería agregar búsqueda híbrida con BM25. Si el volumen de documentos crece a miles, migraría a Qdrant o Weaviate. Si los datos se vuelven sensibles y necesitamos auditoría profesional, Pinecone con su tier enterprise sería una opción razonable.

Pero por ahora, ChromaDB y un modelo open source de embeddings cubren lo que necesitamos.
