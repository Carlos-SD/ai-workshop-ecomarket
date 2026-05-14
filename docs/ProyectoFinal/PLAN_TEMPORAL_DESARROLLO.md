# Plan temporal de desarrollo - Proyecto Final EcoMarket

Este archivo deja documentado el plan de implementacion antes de iniciar el desarrollo. La rama de trabajo es `devolutions-agent`.

## Objetivo del proyecto

Extender el sistema RAG del Taller 2 para convertir EcoMarket en un asistente capaz de gestionar devoluciones de productos mediante un agente de IA. El sistema debe mantener el RAG para preguntas informativas y agregar un agente especializado para acciones de devolucion.

## Arquitectura propuesta

```text
Usuario
  |
  v
Router de intencion
  |
  |-- Pregunta informativa general
  |       -> RAG actual
  |
  |-- Solicitud accionable de devolucion
          -> Agente de devoluciones
                -> consultar_pedido
                -> verificar_elegibilidad_devolucion
                -> generar_etiqueta_devolucion
                -> registrar_solicitud_devolucion
```

La division principal sera:

- RAG: responde preguntas sobre politicas, productos, envios, pagos y FAQs.
- Agente: ejecuta el flujo de devolucion cuando el usuario pide realizar una accion.
- Router: decide si la entrada va al RAG o al agente.
- LangSmith: permite observar visualmente trazas, llamadas a herramientas, prompts y tiempos.
- Streamlit: interfaz web simple para demostrar el flujo completo.

## Fase 1 - Diseño de arquitectura y herramientas

Entregables esperados:

- Documento de arquitectura del agente.
- Justificacion de LangChain como marco de agentes.
- Definicion clara de tools.
- Diagrama del flujo de devolucion.

Decisiones iniciales:

- Usar LangChain porque el repo ya lo usa para RAG y permite integrar tools con Gemini.
- Usar un router previo al agente para separar consultas informativas de solicitudes accionables.
- Mantener las reglas de negocio en funciones deterministicas, no en razonamiento libre del LLM.

Tools propuestas:

- `consultar_pedido(order_id)`: valida si el pedido existe y devuelve su informacion.
- `verificar_elegibilidad_devolucion(order_id, product_name)`: valida pedido, producto incluido y politica de devolucion.
- `generar_etiqueta_devolucion(order_id, product_name)`: genera una etiqueta simulada si la devolucion es elegible.
- `registrar_solicitud_devolucion(...)`: deja registro local de la accion para trazabilidad.

## Fase 2 - Implementacion y conexion de componentes

Orden de desarrollo recomendado:

1. Crear `scripts/return_tools.py`.
2. Implementar tools deterministicas usando `data/orders.json` y `data/return_policies.json`.
3. Crear un runner simple para probar tools sin LLM.
4. Crear `scripts/return_agent.py`.
5. Definir prompt del agente de devoluciones.
6. Conectar Gemini mediante LangChain.
7. Registrar las tools en el agente.
8. Crear `scripts/customer_service_router.py`.
9. Reutilizar `query_rag()` de `scripts/rag_query.py` para la ruta informativa.
10. Agregar metadatos de ejecucion: ruta usada, tools llamadas, errores y resultado.

Criterios de comportamiento:

- El agente no debe aprobar devoluciones sin consultar tools.
- El agente no debe generar etiqueta si la elegibilidad falla.
- Si falta numero de pedido o producto, debe pedir el dato faltante.
- Si el pedido no existe, debe responder con error controlado.
- Si el producto no esta en el pedido, debe explicarlo.
- Si el producto no es retornable, debe explicar la razon de politica.

## Fase 3 - LangSmith, evaluacion y observabilidad

Configuracion esperada en `.env.example`:

```env
GOOGLE_API_KEY=your-google-api-key-here
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your-langsmith-api-key-here
LANGSMITH_PROJECT=ecomarket-final-agent
```

Uso de LangSmith:

- Ver trazas del RAG.
- Ver trazas del agente.
- Confirmar llamadas a tools.
- Medir tiempo de respuesta.
- Comparar casos exitosos y fallidos.

Evaluacion propuesta:

- Crear `evaluation/agent_test_cases.json`.
- Crear `scripts/evaluate_agent.py`.
- Cubrir minimo estos escenarios:
  - Devolucion aprobada.
  - Producto no retornable.
  - Pedido inexistente.
  - Producto no incluido en pedido.
  - Consulta general que debe ir a RAG.
  - Solicitud ambigua con datos faltantes.

## Fase 4 - Interfaz web y despliegue funcional

Herramienta propuesta: Streamlit.

Archivo esperado:

- `app.py`

Elementos minimos de la interfaz:

- Campo de texto para el mensaje del usuario.
- Boton para enviar.
- Area de respuesta del asistente.
- Panel opcional de detalles tecnicos:
  - ruta usada: `rag` o `agent`
  - tools llamadas
  - estado final
  - errores controlados

Comandos esperados:

```bash
streamlit run app.py
```

## Documentacion final esperada

Crear carpeta:

```text
docs/ProyectoFinal/
```

Documentos finales:

- `fase1_arquitectura_agente.md`
- `fase2_implementacion_conexion.md`
- `fase3_analisis_critico.md`
- `fase4_despliegue.md`

Actualizar tambien:

- `README.md`
- `.env.example`
- `requirements.txt`

## Prompts de demostracion para sustentacion

Casos para mostrar:

```text
Quiero devolver la botella de bambu del pedido 12345.
```

Resultado esperado: agente valida pedido, valida politica y genera etiqueta.

```text
Quiero devolver el champu solido del pedido 12347.
```

Resultado esperado: agente rechaza por politica de producto cosmetico abierto/no retornable.

```text
Quiero devolver el panel solar del pedido 12351.
```

Resultado esperado: agente detecta que el pedido esta cancelado y no genera etiqueta.

```text
Quiero devolver una botella del pedido 99999.
```

Resultado esperado: agente indica que el pedido no existe.

```text
Cuanto cuesta el envio a Medellin?
```

Resultado esperado: router envia al RAG.

```text
Quiero hacer una devolucion.
```

Resultado esperado: agente pide numero de pedido y producto.

## Estado de avance

1. Implementar tools deterministicas. Completado.
2. Probar tools manualmente. Completado.
3. Implementar agente LangChain. Completado.
4. Implementar router RAG/agente. Completado.
5. Activar trazabilidad LangSmith. Completado.
6. Crear interfaz Streamlit. Completado.
7. Agregar evaluacion. Completado.
8. Escribir documentacion final. Completado.
9. Actualizar README. Completado.
10. Verificar extremo a extremo. Completado parcialmente; los flujos live dependen de cuota disponible en Gemini.

## Pendiente recomendado antes de entrega

1. Ejecutar una demo live cuando Gemini tenga cuota disponible.
2. Capturar evidencia visual de LangSmith con un caso exitoso y un caso fallido.
3. Revisar el guion en `docs/ProyectoFinal/demo_sustentacion.md`.
4. Confirmar que `.env` local tiene `LANGSMITH_TRACING=true` antes de la sustentacion.
