# Fase 2: Construcción de la Base de Conocimiento

El éxito de un sistema RAG depende mucho más de qué documentos tienes y cómo los partes que del modelo de embeddings o la base vectorial. Esta fase es donde decidimos qué información va a poder responder el sistema y cómo la organizamos para que el retrieval funcione bien.

## Documentos identificados

Después de revisar el caso de EcoMarket, identifiqué cuatro tipos de documentos cruciales para responder consultas comunes de servicio al cliente.

### 1. FAQs generales (faqs.json)

Es el documento más importante para cobertura amplia. Incluí 20 preguntas frecuentes organizadas en seis categorías: cuenta, pagos, pedidos, envíos, productos, devoluciones, sostenibilidad y soporte.

¿Por qué este documento? Porque la mayoría de clientes hacen preguntas predecibles: "¿cómo creo una cuenta?", "¿qué métodos de pago aceptan?", "¿hay envío gratis?". Tener estas respuestas estructuradas es la forma más eficiente de cubrir el 60-70% de consultas reales.

Un detalle importante: cada FAQ ya viene en formato pregunta-respuesta, lo cual es ideal para la búsqueda vectorial. Cuando un usuario pregunta algo, su pregunta probablemente se parece mucho a una de las preguntas almacenadas.

### 2. Políticas de devoluciones (return_policies.json)

Este documento ya existía del Taller 1. Lo traduje al español y lo mantuve como referencia para preguntas específicas de devoluciones por producto. Tiene 14 productos, mezcla de retornables y no retornables.

¿Por qué mantenerlo? Porque las preguntas sobre devoluciones son específicas de cada producto. "¿Puedo devolver el champú sólido?" tiene una respuesta diferente a "¿Puedo devolver la botella de bambú?". Necesitamos que el sistema pueda recuperar la política exacta para cada producto.

### 3. Catálogo de productos (product_catalog.json)

Catálogo expandido con 14 productos, cada uno con descripción detallada, precio, características, certificaciones, stock disponible, garantía y opciones (colores, fragancias, etc).

¿Por qué este documento? Porque sin él, el sistema no puede responder preguntas sobre productos. Si alguien pregunta "¿cuánto cuesta el panel solar?" o "¿en qué fragancias viene el champú?", tenemos que tener esa información estructurada. La descripción expandida también ayuda con preguntas más generales como "¿qué materiales usa la botella de bambú?".

### 4. Política de envíos y tiempos (shipping_policy.md)

Documento más narrativo con secciones sobre cobertura geográfica, tiempos de entrega por zona, costos, procesamiento de pedidos, transportadoras aliadas, y manejo de pedidos no entregados.

¿Por qué este documento? Las preguntas sobre envíos son muy comunes y tienen muchos detalles ("¿cuánto tarda a Bogotá?", "¿hacen envíos a Estados Unidos?", "¿qué transportadora usan?"). Un documento estructurado en Markdown nos permite tener toda esta información disponible.

### Lo que decidí no incluir

Considera estos otros documentos que podrían parecer útiles pero no agregué:

**Inventario en tiempo real:** Aunque tener stock actualizado sería útil, los datos de inventario cambian constantemente y no son apropiados para indexar en una base vectorial estática. Para preguntas como "¿hay stock?", lo correcto sería conectar con un sistema operacional de tiempo real, no con RAG.

**Reseñas de productos:** Podrían enriquecer las respuestas, pero introducen ruido. Si el sistema responde basado en reseñas (que son opiniones subjetivas), puede dar información inconsistente. Mejor mantener el RAG enfocado en información oficial.

**Información de competidores:** Aunque sería útil para responder preguntas comparativas, traería complicaciones legales y potencialmente generaría respuestas que perjudiquen a EcoMarket.

## Estrategia de chunking por tipo de documento

Una de las decisiones más importantes en RAG es cómo dividir los documentos en fragmentos. Hay tres estrategias generales: tamaño fijo, recursivo, y semántico. Pero la mejor decisión es escoger una diferente según el tipo de documento.

### Reglas que guían el chunking

Antes de meterme en cada documento, las reglas que apliqué son:

1. **Cada chunk debe ser autocontenido.** Si el chunk dice "como se mencionó antes...", está roto. El sistema debe poder usarlo sin necesitar contexto externo.

2. **Ni muy chico ni muy grande.** Chunks de 50 caracteres pierden contexto, chunks de 5000 caracteres traen mucha información irrelevante.

3. **Respetar la estructura semántica.** No partir oraciones a la mitad ni separar una pregunta de su respuesta.

### Estrategia 1: Chunk por entrada (FAQs y políticas de devolución)

Para las FAQs y políticas de devolución, cada entrada en el JSON ya es una unidad semántica completa. Una FAQ tiene su pregunta y su respuesta, una política tiene el producto y sus condiciones de devolución.

**Implementación:** Cada item del JSON se convierte en un chunk independiente. No usamos splitter automático porque ya tienen la granularidad correcta.

```python
# Ejemplo: cada FAQ se vuelve un chunk
content = f"Pregunta: {faq['pregunta']}\nRespuesta: {faq['respuesta']}"
```

**¿Por qué funciona?** Cuando alguien pregunta "¿cómo recupero mi contraseña?", su pregunta se parece semánticamente a "Olvidé mi contraseña, ¿cómo la recupero?". El embedding va a recuperar exactamente ese chunk. Si hubiéramos partido el JSON por tamaño fijo, podríamos haber separado preguntas de respuestas, lo cual sería desastroso.

**Tamaño promedio:** 150-300 tokens por chunk.

### Estrategia 2: Chunk por producto (catálogo)

Cada producto del catálogo tiene mucha información: nombre, descripción, características, precio, certificaciones, stock, etc. Un usuario que pregunta sobre un producto generalmente quiere TODA esa información, no fragmentos.

**Implementación:** Cada producto se convierte en un chunk con toda su información formateada.

```python
content = f"""Producto: {nombre}
Descripción: {descripcion}
Características: {caracteristicas}
Precio: {precio}
..."""
```

**¿Por qué funciona?** Cuando alguien pregunta "¿la botella de bambú viene con tapa antiderrame?", el sistema recupera el chunk completo de ese producto y Gemini puede ver toda la información de una vez para responder con precisión. Si hubiéramos partido el catálogo por tamaño, podríamos haber separado el nombre del producto de sus características.

**Tamaño promedio:** 200-400 tokens por chunk.

### Estrategia 3: Chunking recursivo por secciones (política de envíos)

La política de envíos es diferente: es un documento narrativo en Markdown con encabezados, párrafos, listas y tablas. No tiene una estructura predefinida tan clara como un JSON.

**Implementación:** Usamos `RecursiveCharacterTextSplitter` de LangChain con separadores configurados específicamente:

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=[
        "\n## ",     # Primero parte por secciones principales
        "\n### ",    # Luego por subsecciones
        "\n\n",      # Luego por párrafos
        "\n",        # Luego por líneas
        ". ",        # Luego por oraciones
        " "          # En último caso por palabras
    ]
)
```

El splitter intenta primero partir por secciones (`## `), si no puede por subsecciones (`### `), luego por párrafos, y así sucesivamente. Esto respeta la estructura del documento.

**El parámetro `chunk_overlap=100` es importante:** algunos chunks adyacentes comparten 100 caracteres. Esto evita perder contexto en los bordes. Por ejemplo, si una sección sobre "Bogotá" se divide en dos chunks, el final de uno y el inicio del otro mencionan "Bogotá" para que ambos tengan contexto.

**¿Por qué este tamaño (800 caracteres)?** En español, esto equivale aproximadamente a 200-250 tokens, que es un buen balance entre tener contexto suficiente y no incluir información irrelevante. Probé con 500 (muy chico, perdía contexto) y 1500 (muy grande, traía secciones enteras innecesariamente).

### Resumen de las estrategias

| Documento | Estrategia | Tamaño aprox. | Razón |
|-----------|-----------|---------------|-------|
| FAQs | Por entrada JSON | 150-300 tokens | Cada FAQ ya es semánticamente independiente |
| Políticas de devolución | Por entrada JSON | 100-200 tokens | Cada producto tiene su política independiente |
| Catálogo de productos | Por producto JSON | 200-400 tokens | El usuario quiere ver el producto completo |
| Política de envíos | Recursivo por secciones | 200-250 tokens | Documento narrativo con estructura jerárquica |

## Por qué la calidad del chunking importa tanto

En un sistema RAG, el chunking es el cuello de botella silencioso. El modelo de embeddings puede ser excelente, la base vectorial súper rápida, y Gemini puede ser inteligente. Pero si un chunk está mal partido, el sistema falla aunque todo lo demás funcione bien.

Ejemplos concretos de qué pasa con un mal chunking:

**Caso 1: Chunks por tamaño fijo en FAQs.** Si parto las FAQs cada 500 caracteres, podría dividir "¿Cómo creo una cuenta?" de su respuesta. El sistema recuperaría una pregunta sin respuesta, o una respuesta sin saber a qué pregunta corresponde.

**Caso 2: Chunks demasiado grandes en el catálogo.** Si pongo todos los productos en chunks gigantes, cuando alguien pregunte sobre un producto específico, el sistema va a traer información de varios productos al mismo tiempo. Gemini se confunde y puede mezclar información (decir el precio de un producto con las características de otro).

**Caso 3: Política de envíos partida arbitrariamente.** Si parto el documento de envíos en chunks de tamaño fijo, podría separar "Para Bogotá:" de "el costo es $8.000". El sistema recupera el dato sin saber para qué ciudad aplica.

## Proceso de indexación

Una vez que tenemos los chunks correctamente formados, el proceso de indexación es directo:

1. **Cargar cada documento** según su tipo (JSON, Markdown).
2. **Aplicar la estrategia de chunking** correspondiente.
3. **Generar metadata** para cada chunk: source (faqs, return_policies, etc.), tipo de documento, IDs cuando aplica. Esta metadata sirve para filtros posteriores y para auditar de dónde sacó la información el sistema.
4. **Generar embeddings** con el modelo multilingüe que escogimos.
5. **Almacenar en ChromaDB** con persistencia en disco.

El script `build_knowledge_base.py` automatiza todo esto. Una corrida típica genera entre 50 y 80 chunks totales, depende del tamaño de la política de envíos.

Si los documentos cambian (políticas actualizadas, nuevos productos, FAQs adicionales), simplemente se vuelve a ejecutar el script y se regenera toda la base. Para EcoMarket es preferible regenerar completamente que hacer actualizaciones incrementales, porque garantiza consistencia.

## Lo que vendría después

Esta es una base de conocimiento estática. En producción, querríamos:

- **Actualización automática** cuando cambian los datos en el sistema operacional.
- **Versionamiento** de los documentos para poder hacer rollback si una actualización rompe algo.
- **Métricas** sobre qué chunks se recuperan más, cuáles nunca, cuáles fallan.
- **A/B testing** de diferentes estrategias de chunking para ver cuál funciona mejor en preguntas reales.

Para el taller, la versión actual cubre los criterios de la rúbrica y demuestra que entendí cómo el chunking afecta la calidad del retrieval. Cada estrategia escogida tiene una razón clara basada en la naturaleza del documento.
