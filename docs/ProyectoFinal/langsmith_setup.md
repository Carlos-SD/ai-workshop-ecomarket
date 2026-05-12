# Configuracion de LangSmith

LangSmith permite observar visualmente lo que hace el sistema:

- Ruta seleccionada por el router.
- Llamadas del agente a herramientas.
- Respuestas de Gemini.
- Tiempos de ejecucion.
- Errores de ejecucion.

## Variables de entorno

En `.env`, agrega:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=tu-api-key-de-langsmith
LANGSMITH_PROJECT=ecomarket-final-agent
```

`GOOGLE_API_KEY` sigue siendo necesaria para Gemini.

## Como generar una traza

Ejecuta una solicitud que pase por el router:

```bash
venv/bin/python scripts/customer_service_router.py \
  --message "Quiero devolver la botella de bambu del pedido 12345" \
  --json
```

Luego abre LangSmith y busca el proyecto:

```text
ecomarket-final-agent
```

Deberias ver una traza con el flujo del agente y sus herramientas:

```text
customer message
  -> ecomarket_return_agent
     -> verificar_elegibilidad_devolucion_tool
     -> generar_etiqueta_devolucion_tool
     -> registrar_solicitud_devolucion_tool
```

## Nota

LangSmith no es obligatorio para que el proyecto funcione. Si `LANGSMITH_TRACING=false`, el sistema sigue ejecutando el agente y el RAG normalmente, solo que sin enviar trazas al dashboard.
