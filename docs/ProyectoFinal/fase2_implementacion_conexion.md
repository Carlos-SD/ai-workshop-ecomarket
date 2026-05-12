# Fase 2: Implementacion y Conexion de Componentes

## Componentes agregados

La implementacion agrega cinco piezas principales:

- `scripts/return_tools.py`: reglas de negocio deterministicas.
- `scripts/return_agent.py`: agente LangChain que usa Gemini y herramientas.
- `scripts/customer_service_router.py`: router entre RAG y agente.
- `scripts/langsmith_config.py`: configuracion opcional de LangSmith.
- `app.py`: interfaz Streamlit.

## Herramientas deterministicas

Las herramientas leen los datos locales:

- `data/orders.json`
- `data/return_policies.json`

Esto permite validar pedidos y politicas sin depender del razonamiento libre del modelo.

Ejemplo:

```text
Quiero devolver la botella de bambu del pedido 12345
```

La tool de elegibilidad valida:

- El pedido `12345` existe.
- El producto esta dentro del pedido.
- La politica de devolucion permite devolver la botella.
- El plazo es de 30 dias.
- La condicion es producto sin uso y en empaque original.

## Agente LangChain

El agente se construyo con `create_agent` de LangChain. Gemini decide que herramienta llamar, pero no decide las reglas de negocio.

El prompt del agente esta en:

```text
prompts/return_agent_prompt.txt
```

Las reglas principales del prompt son:

- No aprobar devoluciones sin tools.
- No generar etiqueta si la elegibilidad falla.
- Pedir datos faltantes si no hay pedido o producto.
- Responder con empatia cuando hay rechazo.

## Router de intencion

El router decide la ruta inicial:

- Solicitudes accionables de devolucion van al agente.
- Preguntas informativas van al RAG.

Ejemplos:

```text
Quiero devolver la botella de bambu del pedido 12345
-> return_agent
```

```text
Cuanto cuesta el envio a Medellin?
-> rag
```

```text
Puedo devolver un cepillo de bambu?
-> rag
```

La clasificacion se implemento con reglas transparentes para que sea facil justificarla en la sustentacion.

## Manejo de respuestas

El sistema devuelve una estructura con:

- Ruta usada.
- Respuesta final.
- Clasificacion.
- Trazas de tools.
- Estado de LangSmith.
- Documentos recuperados si uso RAG.

Esto facilita la interfaz, la evaluacion y la depuracion.

## Validaciones realizadas

Se probaron estos casos:

- Botella del pedido `12345`: devolucion aprobada y etiqueta generada.
- Champu solido del pedido `12347`: rechazo por politica.
- Panel solar del pedido `12351`: rechazo por pedido cancelado.
- Solicitud incompleta: el agente pide numero de pedido.
- Pregunta de envio: el router envia al RAG.

## Limitacion observada

Durante pruebas se alcanzo cuota de Gemini en el free tier. Por eso el script de evaluacion permite correr en modo de clasificacion sin llamadas al modelo, y solo usar `--live` cuando se quiera validar el flujo completo.
