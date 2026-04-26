# Fase 1: Selección del Modelo

## ¿Por qué Google Gemini Pro?

Escogí Google Gemini Pro después de compararlo con las otras opciones principales. La decisión se redujo a tres factores: es completamente gratis, la calidad es suficientemente buena para lo que necesitamos, y lo pude poner a funcionar en menos de cinco minutos.

---

## Análisis de costos

**Gemini Pro es gratuito.** Sin tarjeta de crédito, sin sorpresas en la factura, sin "capa gratuita que se agota a las dos semanas." Se incluye:
- 60 solicitudes por minuto
- 1.500 solicitudes por día
- 1 millón de solicitudes por mes

En comparación:
- GPT-3.5-Turbo costaría alrededor de $30 USD/mes para un volumen similar
- GPT-4 rondaría los $450 USD/mes
- Claude requiere tarjeta de crédito aunque ofrezca $5 de crédito inicial
- Llama requiere servidores y GPUs propios

Para un proyecto académico o un MVP temprano, gastar cero pesos importa. El concepto se puede validar sin tocar el presupuesto.

---

## Evaluación de calidad

Probé Gemini con los casos de uso reales: consultas de estado de pedido y preguntas sobre política de devoluciones. Los manejó sin problema.

**En qué destaca:**
- Lee datos JSON con precisión
- No inventa información cuando los datos son claros
- Genera respuestas con lenguaje natural
- Ajusta el tono apropiadamente (más empático ante retrasos, directo ante confirmaciones)

**Donde tiene dificultades:**
- Conversaciones muy largas (100+ mensajes) empiezan a confundirlo
- Necesita instrucciones claras o se desvía del guion
- A veces intenta ser demasiado útil y sobre-explica

Pero para "dime dónde está mi paquete" y "¿puedo devolver este cepillo de dientes?", funciona. La diferencia entre Gemini y GPT-4 en estas tareas específicas no justifica pagar 30 veces más.

---

## El problema de la velocidad de respuesta

Actualmente, el equipo de soporte de EcoMarket tarda aproximadamente 24 horas en responder. Con IA manejando las consultas simples, el tiempo de respuesta cae a unos 2 segundos. Eso es una mejora de 12.000 veces.

La limitación: la IA no puede manejar todo. Aproximadamente el 20% de las consultas requieren juicio humano real: alguien está molesto, la situación es inusual, la política no encaja perfectamente. Esas siguen yendo a personas. Pero el otro 80% ("¿dónde está mi pedido?", "¿cuál es su política de devolución?") se responden de inmediato.

---

## Cómo funcionaría

La configuración básica es simple:

```
El cliente hace una pregunta
         ↓
El sistema decide: ¿es esto simple o complicado?
         ↓                              ↓
  Consulta simple               Consulta compleja
         ↓                              ↓
Gemini responde              El agente humano lo atiende
 con info de la BD
         ↓
Respuesta al cliente
```

**Para la parte de IA:**
- Conectar con la base de datos de pedidos
- Cargar las políticas de devolución
- Darle a Gemini instrucciones claras sobre tono y formato
- Enviar la consulta

**Para la escalación humana:**
- Pasar la conversación completa hasta ese punto
- Indicar qué hizo que fuera complicada
- Dejar que el agente tome el control

---

## ¿Por qué no los otros?

**GPT-4:** Caro. Muy bueno, pero excesivo para "¿dónde está mi paquete?". Si se hace razonamiento complejo o análisis de múltiples pasos, quizás vale la pena. Para consultas de servicio al cliente, no.

**GPT-3.5:** Cuesta dinero y requiere tarjeta de crédito. La calidad es comparable a Gemini. La única razón para usarlo sería tener ya infraestructura de OpenAI configurada.

**Claude:** También requiere configuración de pago. La ventana de contexto de 100K+ tokens es impresionante, pero no estamos procesando novelas enteras, sino consultando estados de pedidos.

**Llama (ejecutándolo uno mismo):** Da control total y no tiene costos por consulta después de la configuración. Pero se necesitan servidores, GPUs, lógica de monitoreo y escalamiento. Ese es un proyecto en sí mismo. Tiene sentido para empresas con requisitos estrictos de datos o volumen masivo, no para un piloto.

---

## Comparación rápida

| Factor | Gemini | GPT-3.5 | GPT-4 | Claude | Llama |
|--------|--------|---------|-------|--------|-------|
| Costo | Gratis | ~$30/mes | ~$450/mes | Pago | Infraestructura |
| Tiempo de configuración | 5 min | 20 min | 20 min | 20 min | Días |
| Requiere pago | No | Sí | Sí | Sí | No (pero servidores) |
| Calidad para este caso | Buena | Buena | Excelente | Buena | Aceptable |
| Velocidad de respuesta | 1-2s | 2-3s | 4-6s | 2-3s | <1s |

---

## Cómo se ve el éxito

**Rendimiento:**
- Respuesta correcta >95% de las veces
- No inventar información (<1% de alucinaciones)
- Responder en menos de 3 segundos

**Negocio:**
- Clientes satisfechos (>85% de satisfacción)
- Resolver la mayoría de consultas sin escalación (>80%)
- Escalar 15-25% a humanos (los casos realmente complejos)

**Costo:**
- Mantenerse en la capa gratuita
- $0 por consulta
- Ahorrar más de lo que costaría contratar otro agente de soporte

---

## La razón real

Gemini funciona para este caso de uso y no cuesta nada. Si deja de funcionar, se puede cambiar de modelo con aproximadamente 2 horas de cambios en el código. Los prompts son portables. El riesgo es bajo.

No se afirma que sea el mejor modelo del planeta. Se afirma que es suficientemente bueno para estado de pedidos y políticas de devolución, y que se puede desplegar hoy sin trámites de aprovisionamiento.
