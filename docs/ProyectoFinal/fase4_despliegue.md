# Fase 4: Despliegue Funcional

## Herramienta seleccionada

Se selecciono Streamlit para la interfaz web.

Razones:

- Es rapido para construir prototipos funcionales en Python.
- Permite integrar directamente el codigo existente.
- No requiere crear un frontend separado.
- Es suficiente para demostrar el flujo extremo a extremo en la sustentacion.

Gradio tambien era una opcion valida, pero Streamlit facilita mostrar paneles de detalle, metricas y trazas de ejecucion junto con el chat.

## Interfaz implementada

Archivo principal:

```text
app.py
```

La interfaz incluye:

- Entrada de mensaje estilo chat.
- Historial de conversacion.
- Botones con casos de ejemplo.
- Panel de estado de LangSmith.
- Metricas de ruta y herramientas usadas.
- Expander con detalles tecnicos.

## Ejecucion local

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar:

```bash
streamlit run app.py
```

O usando el entorno virtual del proyecto:

```bash
venv/bin/streamlit run app.py
```

URL local esperada:

```text
http://localhost:8501
```

## Configuracion necesaria

El archivo `.env` debe tener:

```env
GOOGLE_API_KEY=tu-api-key-de-google
```

Para ver trazas en LangSmith:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=tu-api-key-de-langsmith
LANGSMITH_PROJECT=ecomarket-final-agent
```

## Demostracion funcional

Prompts recomendados:

```text
Quiero devolver la botella de bambu del pedido 12345
```

Resultado esperado:

- Ruta: `return_agent`
- Tools: elegibilidad, etiqueta, registro
- Respuesta con etiqueta simulada

```text
Quiero devolver el champu solido del pedido 12347
```

Resultado esperado:

- Ruta: `return_agent`
- Tool de elegibilidad
- Rechazo por politica de cosmeticos

```text
Cuanto cuesta el envio a Medellin?
```

Resultado esperado:

- Ruta: `rag`
- Respuesta basada en documentos de envio

## Consideraciones de despliegue

Esta version esta pensada para demostracion academica local. Para produccion se deberia:

- Usar autenticacion.
- Proteger API keys con secret manager.
- Conectar datos a servicios reales.
- Agregar rate limiting.
- Configurar logs centralizados.
- Desplegar en Streamlit Community Cloud, Cloud Run, Render o una plataforma equivalente.
