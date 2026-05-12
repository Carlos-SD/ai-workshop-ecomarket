# Fase 3: Analisis Critico y Propuestas de Mejora

## Riesgos de seguridad

Dar capacidad de accion a un modelo introduce riesgos que no existian en el RAG original.

### Aprobaciones incorrectas

Riesgo: el modelo podria aprobar una devolucion sin cumplir la politica.

Mitigacion: las aprobaciones no se hacen desde el modelo. El agente debe llamar `verificar_elegibilidad_devolucion_tool`, que consulta datos locales y devuelve una respuesta estructurada.

### Generacion indebida de etiquetas

Riesgo: el agente podria generar una etiqueta para un producto no elegible.

Mitigacion: `generar_etiqueta_devolucion` vuelve a verificar elegibilidad internamente antes de crear la etiqueta. Aunque el modelo llame esta tool en mal momento, la tool rechaza la accion.

### Datos insuficientes

Riesgo: el usuario podria pedir "quiero una devolucion" sin numero de pedido ni producto.

Mitigacion: el agente tiene instrucciones para pedir el dato faltante y no ejecutar herramientas si no hay suficiente informacion.

### Abuso o automatizacion maliciosa

Riesgo: un usuario podria intentar generar muchas etiquetas o probar numeros de pedido.

Mitigacion propuesta para produccion:

- Autenticacion del cliente.
- Rate limiting por usuario.
- Validacion contra sistema real de pedidos.
- Revision manual para casos de alto valor.

## Riesgos eticos

### Falta de transparencia

El cliente debe entender si una devolucion fue rechazada por politica y no por una decision arbitraria del modelo.

Mitigacion: las respuestas incluyen la razon concreta de rechazo cuando la tool la devuelve.

### Sesgo en el trato

El agente podria responder con tono distinto segun la forma de escribir del cliente.

Mitigacion: el prompt fuerza un tono profesional, claro y empatico. En produccion se deberian revisar conversaciones reales.

### Exceso de automatizacion

No todas las devoluciones deberian automatizarse. Casos con garantia, productos defectuosos o reclamos complejos pueden requerir atencion humana.

Mitigacion propuesta:

- Escalar a soporte cuando la tool no encuentre politica.
- Escalar si el usuario expresa frustracion fuerte.
- Escalar si el producto es costoso o el pedido tiene inconsistencias.

## Monitoreo y observabilidad

Se agrego soporte para LangSmith. Esto permite observar:

- Prompt enviado al modelo.
- Ruta seleccionada por el router.
- Tools llamadas por el agente.
- Resultados de cada tool.
- Tiempo de ejecucion.
- Errores del modelo o de red.

Tambien se registra localmente cada solicitud de devolucion en:

```text
logs/return_requests.json
```

Este archivo no se sube al repositorio porque puede contener datos operativos.

## Evaluacion

Se agrego:

```text
evaluation/agent_test_cases.json
scripts/evaluate_agent.py
```

El modo por defecto evalua la clasificacion del router sin consumir llamadas a Gemini:

```bash
venv/bin/python scripts/evaluate_agent.py --no-save
```

El modo live ejecuta el flujo completo:

```bash
venv/bin/python scripts/evaluate_agent.py --live
```

## Propuestas de mejora

1. Conectar pedidos a una base de datos real.
2. Agregar autenticacion de usuario antes de generar etiquetas.
3. Crear un agente de reemplazos para productos defectuosos.
4. Agregar un sistema de aprobacion humana para casos sensibles.
5. Guardar metricas de satisfaccion despues de cada respuesta.
6. Mejorar el router con un clasificador entrenado o evaluado con mas datos.
7. Agregar busqueda hibrida al RAG para mejorar preguntas con nombres exactos.
