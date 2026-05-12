# Fase 1: Arquitectura del Agente de Devoluciones

## Objetivo

El proyecto final extiende el sistema RAG del Taller 2 para que EcoMarket no solo responda preguntas, sino que tambien pueda ejecutar una tarea concreta: gestionar solicitudes de devolucion.

La arquitectura separa dos responsabilidades:

- El RAG responde preguntas informativas sobre productos, envios, pagos, politicas y FAQs.
- El agente de devoluciones ejecuta acciones cuando el usuario quiere iniciar o tramitar una devolucion.

## Arquitectura propuesta

```text
Usuario
  |
  v
Router de intencion
  |
  |-- Pregunta informativa
  |       -> Sistema RAG
  |
  |-- Solicitud accionable de devolucion
          -> Agente LangChain
                -> verificar_elegibilidad_devolucion_tool
                -> generar_etiqueta_devolucion_tool
                -> registrar_solicitud_devolucion_tool
```

Esta separacion evita que el agente intente resolver todo. El RAG es mejor para recuperar conocimiento desde documentos, mientras que el agente es mejor para coordinar pasos y herramientas.

## Seleccion del marco de agentes

Se selecciono LangChain por tres razones:

1. El Taller 2 ya usaba LangChain para el flujo RAG.
2. LangChain permite registrar funciones Python como herramientas del agente.
3. LangChain se integra directamente con LangSmith para observar trazas y llamadas a herramientas.

LlamaIndex tambien podria resolver el problema, especialmente en flujos centrados en documentos, pero en este proyecto el foco nuevo es la ejecucion de acciones con tools. Por eso LangChain encaja mejor con el codigo existente.

## Herramientas del agente

Las herramientas se implementaron como funciones deterministicas en `scripts/return_tools.py`. Esto es importante porque las decisiones de negocio no deben depender de que el modelo "recuerde" o invente reglas.

### `consultar_pedido`

Entrada:

```json
{
  "order_id": "12345"
}
```

Salida esperada:

- Pedido encontrado o no encontrado.
- Estado del pedido.
- Productos incluidos.

### `verificar_elegibilidad_devolucion`

Entrada:

```json
{
  "order_id": "12345",
  "product_name": "botella de bambu"
}
```

Salida esperada:

- Si el pedido existe.
- Si el producto esta en el pedido.
- Si el pedido permite devolucion.
- Si el producto es retornable.
- Condiciones o razon de rechazo.

### `generar_etiqueta_devolucion`

Entrada:

```json
{
  "order_id": "12345",
  "product_name": "botella de bambu"
}
```

Salida esperada:

- Numero de solicitud de devolucion.
- URL simulada de etiqueta.
- Transportadora.
- Pasos de empaque y entrega.

### `registrar_solicitud_devolucion`

Entrada:

```json
{
  "order_id": "12345",
  "product_name": "botella de bambu",
  "status": "approved"
}
```

Salida esperada:

- ID de auditoria.
- Ruta del registro local.

## Flujo de trabajo

```text
Cliente pide devolver producto
  |
  v
Router detecta solicitud accionable
  |
  v
Agente recibe mensaje + tools disponibles
  |
  v
Agente verifica elegibilidad
  |
  |-- No elegible -> registra solicitud y responde rechazo
  |
  |-- Elegible -> genera etiqueta
                  |
                  v
               registra solicitud
                  |
                  v
               responde al cliente
```

## Decision de seguridad

El agente no esta autorizado a aprobar devoluciones usando solo texto generado por el modelo. Toda aprobacion debe venir de las herramientas. Esto reduce alucinaciones y hace que la respuesta final sea auditable.
