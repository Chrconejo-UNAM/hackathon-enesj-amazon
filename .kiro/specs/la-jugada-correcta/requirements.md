# Requirements Document

## Introduction

La Jugada Correcta es una app web para un coach NFL. Responde: "¿qué decisión conviene tomar y por qué?". Compara, al momento del pase (`pass_forward`), al receptor elegido contra el receptor más abierto y muestra en qué zona se maximiza el éxito. Datos: temporada 2021, semanas 1-8, 122 partidos. Línea base mostrada en pantalla: "2021 sem. 1-8".

Prioridad de entrega: primero FRONTEND (Marianne, solo `dashboard/`), con el contrato de API congelado en `design.md` para que BACKEND (Christian, solo `backend/`) trabaje en paralelo. Las preguntas de aclaración se omitieron por tiempo; los supuestos están declarados abajo.

## Glossary

- **Regret (Target Regret Index)**: separación del receptor más abierto menos separación del receptor elegido, en yardas, en `pass_forward`. Siempre ≥ 0.
- **Separación**: distancia (yardas) del receptor al defensor más cercano. Es un proxy de "abierto".
- **Estimación**: objeto `{valor, ic95, n, concluyente, confianza}` (ver `design.md`).
- **Semáforo**: verde, amarillo o rojo, tomado de `estimacion.confianza`. Siempre con ícono y texto.
- **Zona**: ubicación en el campo de la jugada: `propia` (más de 50 yardas de la end zone rival), `medio` (21 a 50), `roja` (20 o menos).
- **Lado**: `izquierda`, `centro`, `derecha`, según la posición del objetivo respecto al centro del campo, orientado hacia la dirección de ataque.
- **Éxito**: pase completo con ganancia de al menos 40 % de yardsToGo en 1ª, 60 % en 2ª, y 100 % en 3ª y 4ª. Se usa porque no hay EPA.

## Supuestos declarados

- Zona, lado y éxito se definen como en el glosario.
- Cobertura del filtro: `todas`, `Man`, `Zone` (de `pff_passCoverageType`).
- Umbral "IC ancho": ancho del IC95 mayor a 1.5 yardas (Regret) o mayor a 0.20 (tasas).
- Bootstrap: 1000 remuestreos, semilla fija.
- Jugadas incluidas: pases con receptor objetivo identificable (excluye sacks `S` y scrambles `R`).
- Si el backend no está listo, el frontend usa mocks con las formas exactas del contrato.

## Verificación contra reglas y datos

Verificado en `.kiro/steering/rules.md` y en `data/`:

| Hallazgo | Impacto | Alternativa dentro del stack |
|---|---|---|
| `plays.csv` no tiene receptor objetivo (columnas confirmadas). | Hay que inferirlo. | `playDescription` + `players.displayName`; respaldo: jugador ofensivo más cercano al balón en `pass_arrived`; reportar `pct_objetivo_inferido`. |
| Los nombres en la descripción son abreviados ("C.Godwin"), no `displayName` completo ("Chris Godwin"). | El cruce exacto falla. | Comparar inicial + apellido contra jugadores del equipo ofensivo de esa jugada (solo los de `pff_role` = Pass Route). |
| El tracking tiene el evento `autoevent_passforward` además de `pass_forward` (confirmado en `tracking_2021090900.csv`). | Un filtro por substring contaría dos frames. | Filtrar con igualdad exacta `pass_forward` y `pass_arrived`. |
| Las coordenadas dependen de `playDirection` (left/right). | Zona y lado salen invertidos si no se normaliza. | Normalizar `x` y `y` a "ataque hacia la derecha" antes de calcular. |
| 122 CSV de tracking (~7 MB cada uno, ~850 MB en total). | Arranque lento y riesgo de memoria. | Leer con `usecols` y `chunksize`, conservar solo frames `pass_forward` y `pass_arrived`, precalcular al arrancar en memoria. Sin disco. |
| `down` puede venir vacío y `pff_passCoverage` puede ser `NA` en algunas jugadas. | Estados vacíos en filtros. | Excluir esas filas del filtro afectado y mostrar el estado Vacío. |
| `.kiro/` no se toca salvo el spec; `dashboard/vite.config.ts` no tiene proxy. | Falta `/api` en dev. | Tarea [FRONTEND] 1.2 lo añade. |
| `dashboard/package.json` ya tiene React 18.3.1, Vite 5.4.21, TS 5.7.3, Tailwind 3.4.19, Recharts 3.10.1. | Sin conflicto. | No se agregan dependencias. Sin librería de pruebas de frontend: se valida con `npm run build`. |

No hay contradicciones bloqueantes con las reglas. La IA usa Bedrock Nova con Strands y `BEDROCK_MODEL_ID` según `rules.md`; sin llaves en código.

## Requirements

### Requisito 1: Inicio con hallazgo y tarjeta resumen [FRONTEND]

**Historia de usuario:** Como coach, quiero ver el hallazgo principal al abrir la app, para decidir en segundos si profundizar.

#### Criterios de aceptación

1. CUANDO el usuario abre la app, EL dashboard DEBERÁ mostrar la pestaña Inicio con `titulo` de `GET api/resumen` como título de pantalla (la conclusión).
2. EL dashboard DEBERÁ mostrar la TarjetaResumen de una línea con `linea`, el `regret_liga` como EstimacionBadge y la línea base "2021 sem. 1-8".
3. EL dashboard DEBERÁ mostrar `calidad_datos.pct_objetivo_inferido` como porcentaje de receptores inferidos.
4. MIENTRAS la petición está en curso, EL dashboard DEBERÁ mostrar el estado Cargando.
5. SI la petición falla, ENTONCES EL dashboard DEBERÁ mostrar el estado Error con botón de reintento y el `detail` recibido.

### Requisito 2: Sala de Decisiones [FRONTEND]

**Historia de usuario:** Como coach, quiero fijar down, distancia, zona y cobertura y recibir una recomendación con su porqué, para elegir la jugada.

#### Criterios de aceptación

1. EL dashboard DEBERÁ ofrecer controles de down (1-4), yardsToGo (1-20), zona (`propia`, `medio`, `roja`) y cobertura (`todas`, `Man`, `Zone`).
2. CUANDO cambia un control, EL dashboard DEBERÁ llamar a `GET api/recomendacion` y a `GET api/evidencia` con los valores elegidos.
3. EL dashboard DEBERÁ mostrar `accion` como título de pantalla, `porque`, el Semáforo y el EstimacionBadge.
4. EL dashboard DEBERÁ mostrar gráficas Recharts de evidencia (tasa de éxito por zona, éxito por rango de separación, por cobertura) y la lista de `comparables` con su n.
5. SI `estimacion.n` es menor que 30, ENTONCES EL dashboard DEBERÁ mostrar "aún no es concluyente" y Semáforo rojo.
6. SI la respuesta no tiene datos, ENTONCES EL dashboard DEBERÁ mostrar el estado Vacío con el texto "Sin jugadas con esos filtros".
7. EL dashboard DEBERÁ mostrar `GET api/explicacion` como texto de apoyo, y la etiqueta "respuesta automática" cuando `fuente` sea `plantilla`.

### Requisito 3: Modo Partido en Vivo simulado [FRONTEND + BACKEND]

**Historia de usuario:** Como coach, quiero reproducir un partido real jugada por jugada, para ver cuánto Regret se acumula sin conocer el futuro.

#### Criterios de aceptación

1. EL dashboard DEBERÁ listar partidos desde `GET api/partidos` y permitir elegir uno.
2. CUANDO el usuario pulsa "Siguiente jugada", EL dashboard DEBERÁ pedir `GET api/partido/{gameId}/jugada/{n}` con n+1 y mostrar down, distancia, marcador, reloj, zona, receptor elegido, receptor más abierto y Regret.
3. CUANDO el usuario activa el avance automático, EL dashboard DEBERÁ avanzar una jugada cada 3 segundos hasta pausar o llegar a la última jugada.
4. EL backend NO DEBERÁ devolver datos de jugadas con índice mayor que `n` en ningún endpoint con `hasta=n`.
5. EL dashboard DEBERÁ mostrar el Regret acumulado de `GET api/partido/{gameId}/acumulado?hasta=n`, por zona y por lado, con n e IC95 %.
6. CUANDO el usuario llega a la última jugada, EL dashboard DEBERÁ detener el avance y mostrar "Fin del partido".

### Requisito 4: Tablero de Arrepentimiento [FRONTEND]

**Historia de usuario:** Como coach, quiero ver qué equipos eligen peor a su receptor, para preparar el partido.

#### Criterios de aceptación

1. EL dashboard DEBERÁ mostrar el ranking de `GET api/regret/equipos` ordenado de mayor a menor `estimacion.valor`.
2. EL dashboard DEBERÁ ofrecer filtro de zona (`todas`, `propia`, `medio`, `roja`) que llame a `GET api/regret/equipos?zona=`.
3. CADA fila DEBERÁ mostrar equipo, valor, IC95 %, n y Semáforo.
4. SI una fila tiene n menor que 30, ENTONCES EL dashboard DEBERÁ marcarla "aún no es concluyente".
5. EL título de pantalla DEBERÁ ser la conclusión (equipo con mayor Regret concluyente).

### Requisito 5: Panel IA persistente [FRONTEND + BACKEND]

**Historia de usuario:** Como coach, quiero alertas y respuestas rápidas durante el partido, para decidir en la banda.

#### Criterios de aceptación

1. EL dashboard DEBERÁ mostrar el panel como drawer en móvil y como columna en escritorio (1024 px o más), visible en las 3 pestañas.
2. CUANDO cambia `hasta` en el modo en vivo, EL dashboard DEBERÁ recargar `GET api/partido/{gameId}/alertas?hasta=n` y mostrar un badge con el número de alertas nuevas.
3. EL panel DEBERÁ ofrecer 4 preguntas sugeridas: "¿A quién tiro en 3ª y 5?", "¿Por qué lado me cubren?", "¿Qué cambió desde el medio tiempo?", "Resumen para el vestidor" (con traducción EN).
4. CUANDO el usuario envía una pregunta, EL dashboard DEBERÁ llamar `POST api/chat` con `{gameId, hasta, mensaje}` y mostrar `respuesta`.
5. SI `fuente` es `plantilla`, ENTONCES EL dashboard DEBERÁ mostrar "respuesta automática".
6. SI el panel IA falla, ENTONCES el resto de la app DEBERÁ seguir funcionando.
7. EL backend DEBERÁ generar alertas por reglas, sin IA, y usar Strands + Bedrock Nova solo para `chat` y `explicacion`, con plantilla como respaldo.

### Requisito 6: Modo Banda Lateral [FRONTEND]

**Historia de usuario:** Como coach en la banda, quiero una vista simple y legible, para leerla de un vistazo.

#### Criterios de aceptación

1. CUANDO el usuario activa el toggle, EL dashboard DEBERÁ mostrar una sola columna, texto grande, alto contraste y solo recomendación, Semáforo y alertas.
2. EL toggle DEBERÁ estar visible en todas las pantallas y tener `aria-pressed`.
3. EL dashboard DEBERÁ conservar el estado del modo mientras la página esté abierta (memoria, sin `localStorage`).

### Requisito 7: Idioma ES/EN [FRONTEND]

**Historia de usuario:** Como usuario, quiero cambiar de idioma con un botón, para leer en mi idioma.

#### Criterios de aceptación

1. EL dashboard DEBERÁ iniciar en ES y alternar a EN con un único botón.
2. EL dashboard DEBERÁ usar un diccionario simple para textos de interfaz y el campo `es`/`en` para textos del backend.
3. EL estado de idioma DEBERÁ vivir solo en memoria.
4. SI falta una clave, ENTONCES EL dashboard DEBERÁ mostrar el texto en ES.

### Requisito 8: Calidad estadística y Semáforo [FRONTEND + BACKEND]

**Historia de usuario:** Como coach, quiero saber cuánto confiar en cada número, para no decidir con muestras pequeñas.

#### Criterios de aceptación

1. TODA cifra mostrada DEBERÁ ir con n e IC95 % bootstrap.
2. SI n es menor que 30, ENTONCES `confianza` DEBERÁ ser `rojo` y `concluyente` DEBERÁ ser `false`.
3. SI n está entre 30 y 99, o el IC es ancho, ENTONCES `confianza` DEBERÁ ser `amarillo`.
4. SI n es 100 o más y el IC es angosto, ENTONCES `confianza` DEBERÁ ser `verde`.
5. EL Semáforo DEBERÁ mostrar ícono y texto además del color.

### Requisito 9: Contrato de API y manejo de errores [FRONTEND + BACKEND]

**Historia de usuario:** Como equipo, queremos un contrato fijo, para trabajar en paralelo sin bloquearnos.

#### Criterios de aceptación

1. EL backend DEBERÁ implementar los endpoints de `design.md` con modelos Pydantic y `GET /health` → `{"status":"ok"}`.
2. EL backend DEBERÁ responder errores como `{"detail","codigo"}` con el código HTTP correcto (400 parámetros inválidos, 404 no existe, 422 validación, 500 interno).
3. EL frontend DEBERÁ usar un único cliente `api.ts` con rutas relativas sin diagonal inicial, sin `localhost` ni URLs absolutas.
4. EL frontend DEBERÁ usar mocks con formas idénticas al contrato hasta que cada endpoint exista, con un interruptor por endpoint.
5. EL frontend NO DEBERÁ llamar endpoints fuera del contrato.
6. EL backend DEBERÁ leer el tracking con `usecols`, solo frames `pass_forward` y `pass_arrived`, todo en memoria, sin escribir a disco.
7. EL backend DEBERÁ incluir pruebas pytest de las reglas de semáforo, la inferencia del receptor y la no filtración del futuro.

### Requisito 10: Accesibilidad, móvil y despliegue [FRONTEND]

**Historia de usuario:** Como coach, quiero usar la app en el teléfono, para llevarla a la banda.

#### Criterios de aceptación

1. EL dashboard DEBERÁ verse sin desplazamiento horizontal a 375 px de ancho.
2. EL dashboard DEBERÁ tener máximo 3 pestañas (Inicio, Sala de Decisiones, Tablero de Arrepentimiento) más el panel IA.
3. EL dashboard DEBERÁ tener contraste de texto de al menos 4.5:1, foco visible, `aria-label` en botones de solo ícono y no depender solo del color.
4. EL dashboard NO DEBERÁ usar CDN, fuentes externas ni dependencias nuevas.
5. `vite.config.ts` DEBERÁ tener `base: './'` y proxy de `/api` a `http://localhost:8000` solo en desarrollo.
6. `vite build` DEBERÁ generar `dashboard/dist` sin errores de TypeScript.
7. TODAS las tablas y gráficas DEBERÁN tener estados Cargando, Vacío y Error.

## Limitaciones

- **Proxy de separación:** "más abierto" es la mayor separación al defensor más cercano en `pass_forward`. No considera ángulo de ruta, tipo de cobertura ni capacidad de ganar el balón.
- **Receptor inferido:** el dataset no trae receptor objetivo. Se infiere de `playDescription` y `players.displayName`, con respaldo al jugador más cercano al balón en `pass_arrived`. Se reporta el % inferido y puede haber errores.
- **Alcance de datos:** solo 2021, semanas 1-8 (122 partidos). Las muestras por equipo, zona y cobertura son pequeñas y por eso se reporta n e IC95 %.
- **Sin EPA:** el éxito es una regla basada en yardas ganadas contra yardsToGo, no en puntos esperados.
- El Regret no prueba que el receptor más abierto habría completado el pase. El modo en vivo es una simulación sobre datos históricos.
