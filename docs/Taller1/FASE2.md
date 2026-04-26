# Fase 2: Qué Funciona, Qué No, y Qué Puede Salir Mal

## Qué Funciona

### 1. Soporte Disponible las 24 Horas

La espera actual de 24 horas desaparece. Los clientes obtienen respuestas en segundos, a cualquier hora del día. No más respuestas automáticas de "nos comunicaremos contigo en horario hábil".

Esto ayuda especialmente a clientes internacionales en diferentes zonas horarias y a cualquiera que contacte soporte fuera del horario 9-17. El tiempo de respuesta pasa de 24 horas a 2 segundos.

### 2. Consistencia

Cada cliente recibe la misma respuesta a la misma pregunta. Sin variación según qué agente atendió el ticket, cuántos tickets había gestionado ese día, o si recordaba bien la política.

Cuando se actualiza algo, se actualiza una sola vez (en el prompt o en la base de datos) y aplica en todas partes de inmediato. Con agentes humanos, hay que reentrenar a todos y esperar que el cambio se asimile.

### 3. El 80% que es Repetitivo

La mayoría de consultas de soporte son simples:
- ¿Dónde está mi pedido?
- ¿Cuál es la política de devoluciones?
- ¿Cómo hago seguimiento a mi paquete?
- ¿Cuándo llegará esto?

La IA maneja estas bien. Esto libera a los agentes humanos para enfocarse en lo realmente complicado: clientes molestos, casos extremos, situaciones donde la política no encaja exactamente.

### 4. Escala Sin Costo Lineal

Contratar otro agente de soporte cuesta otro salario. Manejar 10 veces más consultas con IA cuesta... nada, si se mantiene en la capa gratuita. Incluso al llegar a capas pagas, el costo marginal por consulta es mínimo.

En Black Friday o en una campaña de marketing viral, no hay pánico por el volumen de soporte.

### 5. Multilingüe Sin Contrataciones

Gemini maneja más de 100 idiomas. No es necesario contratar equipos de soporte que hablen español, francés y alemán. La IA simplemente cambia de idioma.

### 6. Se Puede Ver Qué Confunde a la Gente

Cuando se registran todas las consultas, los patrones emergen rápido:
- Todos preguntan lo mismo sobre un producto → la descripción no es clara
- Muchas preguntas sobre una política específica → la política es confusa
- Pico de "¿dónde está mi pedido?" el día 5 → problema de comunicación de envíos

Se pueden corregir sistemáticamente en lugar de responder la misma pregunta repetidamente.

### 7. La Mejora Continua es Barata

Se actualiza el prompt, se prueba y se despliega. Listo. Todos reciben la versión mejorada de inmediato. Sin programar sesiones de capacitación ni esperar que el equipo lea el memo.

### 8. Sin Costo por Consulta

La capa gratuita es genuinamente gratuita. Mientras se mantenga por debajo de los límites de uso, responder consultas cuesta $0. Con humanos, cada consulta tiene un costo marginal (tiempo del agente).

---

## Qué No Funciona

### 1. Situaciones Complicadas Necesitan Humanos

Aproximadamente el 20% de las consultas requieren alguien que pueda:
- Empatizar genuinamente (no solo decir palabras empáticas)
- Leer entre líneas
- Tomar decisiones fuera de la política
- Manejar a una persona realmente molesta

**Ejemplo:** El paquete de un cliente se retrasó y ahora se perderá el cumpleaños de su hija. No está pidiendo un reembolso, solo quiere que se reconozca que esto es un problema. La IA puede decir "entiendo que esto es frustrante", pero no tiene el mismo impacto que un humano.

**Qué hacer:** Facilitar la escalación. Si la IA detecta lenguaje emocional o el cliente pide hablar con un humano, transferir de inmediato con el contexto completo.

### 2. Datos Malos Generan Respuestas Incorrectas con Confianza

Si la base de datos dice que un pedido fue despachado pero en realidad no lo fue, la IA le dirá al cliente con seguridad que fue despachado. Esto es peor que decir "no sé".

**Qué hacer:**
- Mantener la base de datos actualizada en tiempo real
- Enseñar a la IA a expresar incertidumbre cuando los datos parecen incorrectos
- Facilitar que los clientes reporten información incorrecta
- Auditar regularmente las consultas más comunes

### 3. No Puede Tomar Acciones

Sin integración con sistemas backend, la IA solo puede consultar información y explicar políticas. No puede:
- Procesar un reembolso
- Cancelar un pedido
- Hacer una excepción a la política
- Autorizar un reemplazo

**Qué hacer:**
- Fase 1: La IA guía a los clientes a través del autoservicio o crea tickets
- Fase 2: Integrar con sistemas backend para acciones automatizadas simples
- Siempre: Ser claro sobre qué puede y no puede hacer la IA

### 4. Las Conversaciones Largas se Enredan

Después de 50-100 mensajes, la IA empieza a perder el hilo de lo dicho anteriormente. Puede contradecirse u olvidar detalles clave.

**Qué hacer:**
- Resumir conversaciones largas periódicamente
- Almacenar hechos clave en un formato estructurado al que la IA pueda hacer referencia
- Escalar hilos inusualmente complejos a humanos

### 5. Los Prompts Necesitan Mantenimiento

Las políticas cambian. Los productos se agregan o descontinúan. Las políticas estacionales van y vienen. Los prompts necesitan actualizarse para que coincidan.

**Qué hacer:** Asignar a alguien para que sea dueño del mantenimiento de prompts. Tratarlo como documentación: requiere revisión regular.

### 6. La Detección de Fraude No Está Incorporada

La IA no detecta patrones como:
- La misma persona creando múltiples cuentas para explotar la política de devoluciones
- Pedidos masivos que parecen intentos de reventa
- Ingeniería social para obtener información que no deberían tener

**Qué hacer:** Integrar con sistemas reales de detección de fraude. No depender de la IA para detectar abusos.

### 7. La Capa Gratuita Tiene Límites

60 solicitudes por minuto, 1.500 por día, 1 millón por mes. Si se alcanzan esos límites, el servicio se degrada o hay que actualizar a un plan pago.

**Qué hacer:**
- Monitorear el uso
- Configurar alertas al 80% de los límites
- Tener un plan para cuando se excedan (encolar solicitudes, actualizar a plan pago, etc.)

---

## Qué Puede Salir Mal (Ética y Riesgos)

### 1. Inventar Información (Alucinaciones)

**El problema:** La IA inventa números de seguimiento, fechas de entrega o detalles de productos que no existen. El cliente lo cree, planifica en torno a eso, y luego descubre que era incorrecto.

Esto es peor que que la IA diga "no tengo esa información". La equivocación con confianza daña la confianza más que la incertidumbre admitida.

**Cómo reducirlo:**

Hacer las instrucciones extremadamente claras:
```
SOLO usa información de la base de datos.
Si no puedes encontrar algo, di que no puedes encontrarlo.
Nunca adivines. Nunca inventes números de seguimiento ni fechas.
```

Verificar respuestas antes de enviarlas:
```python
if respuesta contiene número de seguimiento:
    if número de seguimiento no está en la base de datos:
        no enviar esta respuesta
        registrarlo para revisión
        enviar respuesta de respaldo en su lugar
```

Monitorear:
- Rastrear quejas sobre información incorrecta
- Muestrear respuestas y verificarlas contra la base de datos
- Configurar alertas si la tasa de error sube

**Meta:** Menos del 1% de las respuestas contienen información que no está en la base de datos.

### 2. Tratar a las Personas Diferente (Sesgo)

**El problema:** La IA podría tratar a los clientes diferente según su nombre, ubicación, idioma o cuánto han gastado. Esto puede ser ilegal y definitivamente está mal.

**Ejemplos:**
- Menos útil con personas de nombres no anglófonos
- Respuestas más cortas y menos amigables para personas en ciertos países
- Esfuerzo extra para clientes de alto gasto, mínimo para los demás

**Cómo reducirlo:**

Incluirlo en las instrucciones:
```
Trata a cada cliente de manera idéntica.
Nunca hagas suposiciones sobre alguien basadas en su nombre, ubicación o idioma.
Usa lenguaje neutral en género a menos que sepas los pronombres de alguien.
```

Verificarlo regularmente:
- Cada trimestre, revisar 1.000+ conversaciones
- Dividirlas por datos demográficos (cuando se tiene esa información)
- Medir calidad de respuesta, extensión y utilidad entre grupos
- Buscar diferencias estadísticas

**Meta:** Sin diferencias estadísticamente significativas en calidad de servicio entre grupos demográficos.

### 3. Problemas de Privacidad

**El problema:** Los datos de clientes (nombres, direcciones, detalles de pedidos) podrían exponerse a través de:
- Google almacenándolos para entrenamiento del modelo
- La IA incluyendo accidentalmente información de alguien más en una respuesta
- Registros accedidos por personas que no deberían tenerlos

**Cómo reducirlo:**

Enviar el mínimo de datos necesarios:
```python
# No enviar:
nombre_cliente = "Juan Pérez"
direccion_cliente = "Cra 15 #80-20, Bogotá"
correo_cliente = "juan@ejemplo.com"

# Sí enviar:
id_pedido = "12345"
estado_pedido = "despachado"
entrega_estimada = "20 de abril"
```

Usar acuerdos empresariales:
- Capa enterprise de Google Cloud AI (sin retención de datos para entrenamiento)
- Datos en la región elegida
- Certificaciones de cumplimiento SOC 2, GDPR, habeas data

Actualizar políticas:
- Informar a los clientes en la política de privacidad que se usa IA
- Permitirles elegir soporte solo humano si lo desean
- Ser claros sobre qué datos van adónde

**Meta:** Cero incidentes de filtración de datos. Cumplimiento total con regulaciones de privacidad.

### 4. Impacto en el Empleo

**El problema:** Los agentes de soporte actuales temen que la IA signifique que los van a despedir. Aunque no se planifiquen despidos, el miedo solo ya afecta la moral.

**Cómo manejarlo (la manera correcta):**

Ser honesto desde el principio:
- Realizar reuniones antes de lanzar cualquier cosa
- Comprometerse por escrito: "Sin despidos por causa de la IA"
- Explicar qué está cambiando realmente (la IA maneja lo aburrido, los humanos manejan lo interesante)

Reentrenar a las personas para nuevos roles:
- **Entrenadores de IA**: Revisar respuestas de IA, mejorar prompts, detectar errores
- **Especialistas en Escalación**: Manejar los casos complejos que la IA no puede
- **Éxito del Cliente**: Contacto proactivo con clientes VIP
- **Analistas de Calidad**: Monitorear el rendimiento de la IA y satisfacción del cliente

Implementar gradualmente:
```
Mes 3: IA maneja 20% (consultas más simples)
Mes 4: IA maneja 40%
Mes 5: IA maneja 60%
Mes 6: IA maneja 80%
```

Esto da tiempo para que las personas hagan la transición sin cambios abruptos.

**Meta:** Satisfacción de los agentes por encima de 7/10. Retención por encima del 90%.

### 5. No Decirles a los Clientes que Hablan con IA

**El problema:** Los clientes se sienten engañados cuando se enteran después. Las publicaciones en redes sociales sobre "esta empresa usa IA en secreto y miente al respecto" son dañinas para el negocio.

**Cómo manejarlo:**

Ser obvio desde el inicio:
```
¡Hola! Soy el Asistente Virtual de EcoMarket. Puedo ayudarte 24/7 con:
- Seguimiento de pedidos
- Políticas de devolución
- Información de productos

Para situaciones complejas, te conectaré con un agente humano.
¿En qué puedo ayudarte?
```

Facilitar el cambio a humano:
- Botón visible grande de "Hablar con un Humano"
- Escribir "humano" o "agente" y transferir de inmediato
- Opción en configuración de cuenta: "Nunca uses IA, conéctame siempre con una persona"

**Meta:** Más del 95% de los clientes saben que están hablando con IA.

---

## Panel de Monitoreo

Rastrear continuamente:

| Indicador | Meta | Si supera |
|-----------|------|-----------|
| Quejas por información incorrecta | <5/mes | >10/mes → auditar base de datos y prompts |
| Tasa de alucinación | <1% | >2% → corregir prompts de inmediato |
| Diferencia de satisfacción entre grupos | <5 puntos | >10 puntos → auditoría de sesgo |
| Satisfacción de agentes | >7/10 | <6/10 → atender preocupaciones |
| Tasa de escalación | 15-25% | <10% o >30% → revisar enrutamiento |
| Violaciones de privacidad | 0 | Cualquiera → auditoría de seguridad |
| Conocimiento del cliente sobre uso de IA | >95% | <90% → mejorar divulgación |

---

## Resumen

La IA funciona para consultas simples. Falla en complejidad emocional y casos extremos. Los riesgos reales son: inventar información, tratar a las personas de manera injusta, filtrar datos y manejar mal la transición laboral.

Todo esto es solucionable con:
1. Instrucciones claras a la IA
2. Auditorías regulares
3. Comunicación honesta con clientes y empleados
4. Monitorear las métricas que importan

Si se presta atención a esos cuatro aspectos, el sistema puede mejorar el soporte sin causar problemas.
