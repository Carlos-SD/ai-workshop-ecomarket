# Guion de demo - Proyecto Final EcoMarket

Este documento resume como demostrar el proyecto final de forma ordenada. La idea es mostrar primero la arquitectura, despues el flujo funcionando y finalmente la observabilidad en LangSmith.

## Preparacion

1. Activar el entorno virtual:

```bash
source venv/bin/activate
```

2. Confirmar variables en `.env`:

```env
GOOGLE_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=ecomarket-final-agent
```

3. Ejecutar evaluacion offline sin gastar Gemini:

```bash
venv/bin/python scripts/evaluate_agent.py --no-save
```

Resultado esperado:

```text
route_accuracy_percent: 100.0
```

4. Levantar la interfaz:

```bash
venv/bin/streamlit run app.py
```

Abrir:

```text
http://localhost:8501
```

## Explicacion inicial

El sistema no reemplaza el RAG del Taller 2. Lo extiende con un router y un agente:

- Si el usuario hace una pregunta informativa, el router envia la consulta al RAG.
- Si el usuario pide ejecutar una devolucion, el router envia la solicitud al agente.
- El agente usa LangChain para decidir que tool llamar.
- Las reglas de negocio no estan en el prompt, sino en tools deterministicas.
- LangSmith permite ver la traza completa: entrada, ruta, modelo, tools, salida y errores.

## Caso 1: devolucion aprobada

Prompt:

```text
Quiero devolver la botella de bambu del pedido 12345
```

Resultado esperado:

- Ruta: `return_agent`
- Tools esperadas:
  - `verificar_elegibilidad_devolucion_tool`
  - `generar_etiqueta_devolucion_tool`
  - `registrar_solicitud_devolucion_tool`
- El agente responde que la devolucion fue aprobada y entrega una etiqueta simulada.

Que mostrar en LangSmith:

- Run del agente `ecomarket_return_agent`.
- Waterfall con llamadas a tools.
- Inputs enriquecidos con `order_id` y `product_name`.
- Outputs de cada tool.

## Caso 2: producto no retornable

Prompt:

```text
Quiero devolver el champu solido del pedido 12347
```

Resultado esperado:

- Ruta: `return_agent`
- El agente valida elegibilidad.
- No debe generar etiqueta.
- Debe explicar que el producto no cumple la politica de devolucion.

Punto importante para explicar:

El modelo puede redactar la respuesta, pero no decide arbitrariamente la politica. La decision viene de `verificar_elegibilidad_devolucion`.

## Caso 3: pedido inexistente

Prompt:

```text
Quiero devolver una botella del pedido 99999
```

Resultado esperado:

- Ruta: `return_agent`
- No se genera etiqueta.
- El sistema explica que el pedido no existe.

## Caso 4: pregunta informativa al RAG

Prompt:

```text
Cuanto cuesta el envio a Medellin?
```

Resultado esperado:

- Ruta: `rag`
- No hay tools de devolucion.
- La respuesta se basa en documentos recuperados por ChromaDB.

Que mostrar:

- Panel tecnico de la app con `fallback_used`, `best_score` y ruta `rag`.
- Trace en LangSmith si el tracing esta activo.

## Caso 5: solicitud incompleta

Prompt:

```text
Quiero hacer una devolucion
```

Resultado esperado:

- Ruta: `return_agent`
- El agente debe pedir los datos faltantes: numero de pedido y producto.
- No debe inventar datos ni aprobar la devolucion.

## Si Gemini falla por cuota

Si aparece un run rojo en LangSmith o la app muestra `model_quota_exceeded`, significa que LangSmith funciono: la plataforma capturo el fallo del proveedor del modelo.

Como explicarlo:

- LangSmith no es el modelo ni ejecuta Gemini.
- LangSmith observa la ejecucion.
- El error rojo indica que la llamada al modelo fallo, normalmente por cuota `429`.
- El proyecto maneja ese fallo con una respuesta controlada para que la interfaz no se rompa.

Para seguir demostrando sin gastar cuota:

```bash
venv/bin/python scripts/evaluate_agent.py --no-save
```

Y para probar solo el router:

```bash
venv/bin/python scripts/customer_service_router.py \
  --message "Quiero devolver una botella del pedido 12345" \
  --classify-only
```

## Cierre recomendado

Concluir con estos puntos:

- El Taller 2 tenia RAG para responder informacion.
- El proyecto final agrega comportamiento agente para ejecutar una tarea concreta.
- LangChain se usa para orquestar el agente y sus tools.
- LangSmith se usa para trazabilidad, depuracion y evidencia visual.
- Streamlit permite probar el sistema sin depender de la terminal.
