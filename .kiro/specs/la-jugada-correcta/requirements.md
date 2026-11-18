# Requirements Document

## Introduction

La Jugada Correcta es una aplicación web para un coach ofensivo de la NFL. Dada una situación de juego (down, distancia, zona del campo objetivo y cobertura defensiva), recomienda hacia qué zona atacar, indica qué tan seguro puede estar el coach de esa recomendación (tamaño de muestra, intervalo de confianza y semáforo) y compara las decisiones reales de los quarterbacks con el receptor más abierto mediante el Índice de Arrepentimiento (Regret), medido en yardas de separación.

El alcance de esta especificación es el núcleo (carga de datos, recomendación, incertidumbre, Evidencia, Regret, resumen y dashboard) más el modo en vivo con alertas. Los requisitos 11, 12, 13 y 16 (IA, bilingüe ES/EN, banda lateral y chat) son funciones opcionales que se implementan como tareas finales. El requisito 17 (datos MOCK) permite que el frontend avance sin esperar al backend real.

Los nombres de endpoints, los campos de respuesta y las reglas del semáforo de este documento siguen el CONTRATO OFICIAL DE API, que está congelado. Cualquier cambio al contrato requiere acuerdo explícito del equipo.

Lenguaje y stack: backend en Python 3.12.12 (FastAPI 0.115.14, pandas 2.2.3, numpy 2.1.3) y frontend en TypeScript 5.7.3 (React 18.3.1, Vite 5.4.21, Tailwind CSS 3.4.19, Recharts 3.10.1). Los datos provienen de `data/` (Big Data Bowl, semanas 1 a 8 de 2021, 122 partidos) y son de solo lectura.

## Glossary

- **Backend**: Aplicación FastAPI expuesta en `backend/main.py` como `app`.
- **Dashboard**: Aplicación React + TypeScript en `dashboard/` cuyo build se genera en `dashboard/dist`.
- **Cargador_de_Datos**: Componente del Backend que lee `games.csv`, `plays.csv`, `players.csv`, `pffScoutingData.csv` y `tracking/tracking_[gameId].csv` desde `data/`.
- **Motor_de_Recomendación**: Componente del Backend que estima el valor de atacar cada zona para una situación y emite la recomendación.
- **Motor_de_Incertidumbre**: Componente del Backend que calcula el tamaño de muestra n, el intervalo de confianza al 95 % (IC95%) mediante bootstrap y el semáforo.
- **Motor_de_Regret**: Componente del Backend que calcula el Índice_de_Regret.
- **Servicio_en_Vivo**: Componente del Backend y del Dashboard que reproduce las jugadas de un partido en orden cronológico.
- **Motor_de_Alertas**: Componente del Backend que genera alertas con reglas deterministas y umbrales fijos.
- **Servicio_de_Explicación**: Componente opcional del Backend que redacta la explicación del porqué de una recomendación y atiende el chat.
- **Dropback**: Jugada de `plays.csv` con valor no nulo en `passResult` (C, I, S, IN o R). En el dataset real, todas las jugadas son Dropbacks.
- **Pase_Lanzado**: Dropback con `passResult` igual a C, I o IN y con evento `pass_forward` en el tracking.
- **Jugada_Válida**: Pase_Lanzado que cumple las reglas de limpieza del Cargador_de_Datos (`down` entre 1 y 4, sin intentos de conversión de dos puntos y sin nulos en las columnas de contexto).
- **Estimación**: Objeto `{"valor": float, "ic95": [lo, hi], "n": int, "concluyente": bool, "confianza": "verde|amarillo|rojo"}`.
- **Valor_de_Zona**: Yardas esperadas (`playResult` medio, sin penalizaciones) de los Pases_Lanzados dirigidos a una zona sobre las Jugadas_Comparables. El dataset no trae EPA y el valor no son puntos esperados.
- **Zona**: Combinación de profundidad (corta, media, profunda) y lado (izquierda, centro, derecha) de la posición de un receptor al momento del pase, con código `profundidad_lado` (por ejemplo `media_izquierda`).
- **Cobertura**: Valor `Man` o `Zone` de `pff_passCoverageType` en `plays.csv`.
- **Jugadas_Comparables**: Jugadas_Válidas con el mismo down, el mismo rango de yardsToGo, la misma Zona y la misma Cobertura que la situación consultada, según los criterios definidos en el diseño.
- **n**: Número de Jugadas_Comparables (o de jugadas con Regret) usadas para una Estimación.
- **Ancho_IC**: Diferencia en yardas entre el límite superior y el inferior del IC95%.
- **Semáforo**: Campo `confianza` de la Estimación con valores verde, amarillo o rojo.
- **Concluyente**: Campo booleano de la Estimación que es true cuando el Semáforo es verde o amarillo y false cuando es rojo.
- **Separación**: Distancia en yardas entre un receptor elegible y el defensor más cercano en el frame `pass_forward`.
- **Proxy_de_Receptor_Más_Abierto**: Receptor elegible con la mayor Separación en el frame `pass_forward`.
- **Receptor_Inferido**: Receptor objetivo del pase, obtenido del parseo de `playDescription` cruzado con `players.displayName` y, como respaldo, por cercanía al balón en el frame `pass_arrived`, porque el dataset no identifica al objetivo.
- **Índice_de_Regret**: Para una jugada, Separación del Proxy_de_Receptor_Más_Abierto menos Separación del Receptor_Inferido, en yardas, con mínimo 0 por construcción.
- **Alerta**: Objeto `{id, nivel, titulo{es,en}, texto{es,en}, estimacion}` generado por el Motor_de_Alertas.
- **Estado_de_Carga**: Estado del Cargador_de_Datos: "cargando", "listo" o "error".
- **Respuesta_de_Error**: Objeto JSON `{"detail": <texto>, "codigo": <texto>}` devuelto por el Backend en condiciones de error.
- **Plantilla_de_Explicación**: Texto bilingüe generado por reglas, sin llamar a un modelo de lenguaje.
- **Modo_MOCK**: Modo del Backend que responde todos los endpoints del contrato con datos de ejemplo deterministas.

## Requirements

### Requirement 1: Carga de datos no bloqueante

**User Story:** Como coach ofensivo, quiero que la aplicación cargue los datos sin bloquear el servidor, para que la aplicación esté disponible rápido y me informe cuando aún no puede responder.

#### Acceptance Criteria

1. WHEN el Backend arranca, THE Cargador_de_Datos SHALL iniciar la lectura de los archivos de `data/` en hilos de ejecución en segundo plano.
2. WHILE el Estado_de_Carga es "cargando", THE Backend SHALL responder `GET /health` con HTTP 200 y el cuerpo `{"status": "ok"}`.
3. WHEN el Backend recibe `GET /health`, THE Backend SHALL responder con el cuerpo `{"status": "ok"}` sin esperar a que termine la carga de datos.
4. WHILE el Estado_de_Carga es "cargando", THE Backend SHALL responder cada solicitud a un endpoint bajo `/api/...` con HTTP 503 y una Respuesta_de_Error cuyo campo `codigo` sea `cargando`.
5. WHEN el Cargador_de_Datos termina de leer todos los archivos, THE Backend SHALL cambiar el Estado_de_Carga a "listo" y atender los endpoints bajo `/api/...` con respuestas distintas de 503 por carga.
6. IF el Cargador_de_Datos falla al leer un archivo requerido, THEN THE Backend SHALL cambiar el Estado_de_Carga a "error" y responder los endpoints bajo `/api/...` con HTTP 503 y una Respuesta_de_Error cuyo campo `codigo` sea `error_de_carga`.
7. THE Cargador_de_Datos SHALL leer los archivos de `data/` con rutas relativas a la raíz del proyecto y sin modificar ni escribir archivos en disco.
8. THE Cargador_de_Datos SHALL leer cada archivo de tracking con `usecols` y conservar en memoria solo los frames con evento `ball_snap`, `pass_forward` y `pass_arrived` (más los eventos `autoevent_ballsnap` y `autoevent_passforward` como sustitutos cuando falta el evento principal).
9. THE Cargador_de_Datos SHALL mantener todos los datos procesados en memoria y responder las solicitudes sin releer archivos de disco.
10. THE Cargador_de_Datos SHALL descartar las jugadas con valores nulos en down, yardsToGo, absoluteYardlineNumber, quarter, gameClock, preSnapHomeScore, preSnapVisitorScore o passResult.
11. THE Cargador_de_Datos SHALL descartar las jugadas con down igual a 0 (intentos de conversión de dos puntos).
12. THE Cargador_de_Datos SHALL excluir las jugadas con penalización (penaltyYards distinto de 0) del cálculo del Valor_de_Zona.

### Requirement 2: Recomendación de zona

**User Story:** Como coach ofensivo, quiero indicar la situación de juego y recibir una recomendación de hacia dónde atacar, para que pueda decidir en segundos qué jugada conviene.

#### Acceptance Criteria

1. WHEN el Dashboard envía una situación válida a `GET /api/recomendacion` con los parámetros `down`, `yardsToGo`, `zona` y `cobertura`, THE Motor_de_Recomendación SHALL responder con `{accion{es,en}, porque{es,en}, estimacion, comparables[]}`.
2. THE Motor_de_Recomendación SHALL seleccionar como zona recomendada la que tenga el mayor Valor_de_Zona entre las zonas con n mayor o igual a 30, y entre las zonas con n mayor que 0 cuando ninguna zona alcanza n igual a 30.
3. WHERE el parámetro `zona` está presente, THE Motor_de_Recomendación SHALL devolver la Estimación y los `comparables[]` de esa zona e indicar en `accion` si esa zona es la zona recomendada o si otra zona tiene mayor Valor_de_Zona.
4. WHERE el parámetro `cobertura` está presente, THE Motor_de_Recomendación SHALL restringir las Jugadas_Comparables a las que tengan esa Cobertura.
5. THE Backend SHALL validar los parámetros de `GET /api/recomendacion` con un modelo Pydantic.
6. IF un parámetro está fuera de rango (down fuera de 1 a 4, yardsToGo menor que 1, zona fuera del catálogo o cobertura distinta de Man y Zone), THEN THE Backend SHALL responder HTTP 422 con una Respuesta_de_Error cuyo campo `codigo` sea `parametros_invalidos`.
7. IF ninguna Jugada_Comparable existe para la situación, THEN THE Motor_de_Recomendación SHALL devolver una Estimación con n igual a 0, confianza `rojo` y concluyente igual a false.
8. THE Motor_de_Recomendación SHALL incluir en `porque` la definición de Valor_de_Zona en yardas esperadas y la etiqueta de que no es EPA oficial.

### Requirement 3: Incertidumbre y semáforo

**User Story:** Como coach ofensivo, quiero saber qué tan seguro puedo estar de la recomendación, para que no actúe con base en una muestra pequeña.

#### Acceptance Criteria

1. THE Motor_de_Incertidumbre SHALL calcular el IC95% de cada Estimación mediante bootstrap sobre las observaciones de la Estimación.
2. WHEN n es mayor o igual a 100 y el Ancho_IC es menor que 1.0 yardas, THE Motor_de_Incertidumbre SHALL asignar confianza `verde` y concluyente igual a true.
3. WHEN n está entre 30 y 99 inclusive, o cuando n es mayor o igual a 30 y el Ancho_IC es mayor o igual que 1.0 yardas, THE Motor_de_Incertidumbre SHALL asignar confianza `amarillo` y concluyente igual a true.
4. WHEN n es menor que 30, THE Motor_de_Incertidumbre SHALL asignar confianza `rojo` y concluyente igual a false, sin importar el Ancho_IC.
5. WHEN la Estimación tiene concluyente igual a false, THE Dashboard SHALL mostrar el texto "Aún no es concluyente" junto a la recomendación.
6. THE Dashboard SHALL mostrar n, el IC95% y el Semáforo junto a toda recomendación.
7. WHEN el Motor_de_Incertidumbre calcula un bootstrap, THE Motor_de_Incertidumbre SHALL usar una semilla fija con numpy para que las mismas observaciones produzcan el mismo IC95%.
8. THE Backend SHALL serializar toda Estimación con los campos `valor`, `ic95`, `n`, `concluyente` y `confianza` del contrato.

### Requirement 4: Evidencia

**User Story:** Como coach ofensivo, quiero ver la evidencia detrás de la recomendación, para que pueda confiar en ella y explicarla al equipo.

#### Acceptance Criteria

1. WHEN el Dashboard solicita `GET /api/evidencia` con los parámetros `down`, `yardsToGo` y `zona`, THE Backend SHALL responder con las series para gráficas: distribución de yardas ganadas por zona, Estimación del Valor_de_Zona por zona y por Cobertura, y Estimación del Índice_de_Regret por zona.
2. THE Backend SHALL incluir en cada elemento de `comparables[]` de `GET /api/recomendacion` gameId, playId, equipo ofensivo, semana, down, yardsToGo, zona, cobertura, playResult, Separación del Receptor_Inferido y Separación del Proxy_de_Receptor_Más_Abierto.
3. THE Backend SHALL limitar `comparables[]` a un máximo de 50 elementos ordenados por cercanía a la situación consultada.
4. THE Dashboard SHALL mostrar las series de `GET /api/evidencia` con gráficas de Recharts.
5. IF un parámetro de `GET /api/evidencia` está fuera de rango, THEN THE Backend SHALL responder HTTP 422 con una Respuesta_de_Error cuyo campo `codigo` sea `parametros_invalidos`.

### Requirement 5: Índice de Arrepentimiento

**User Story:** Como analista y coach, quiero un Índice de Arrepentimiento por equipo y por zona, para que pueda ver dónde los quarterbacks lanzaron a un receptor menos abierto que la mejor opción disponible.

#### Acceptance Criteria

1. THE Motor_de_Regret SHALL calcular la Separación de cada receptor elegible como la distancia mínima a un defensor en el frame `pass_forward`, donde los receptores elegibles son los jugadores ofensivos con `pff_role` igual a `Pass Route` más el Receptor_Inferido.
2. THE Motor_de_Regret SHALL definir el Proxy_de_Receptor_Más_Abierto como el receptor elegible con la mayor Separación.
3. THE Motor_de_Regret SHALL calcular el Índice_de_Regret de cada jugada como la Separación del Proxy_de_Receptor_Más_Abierto menos la Separación del Receptor_Inferido.
4. THE Motor_de_Regret SHALL inferir el Receptor_Inferido parseando `playDescription` y cruzando el apellido con `players.displayName` de los jugadores ofensivos de la jugada.
5. WHERE el parseo de `playDescription` no identifica un receptor único y existe el frame `pass_arrived`, THE Motor_de_Regret SHALL elegir como Receptor_Inferido al jugador ofensivo más cercano al balón en ese frame.
6. IF no se identifica un Receptor_Inferido por ninguno de los dos métodos, THEN THE Motor_de_Regret SHALL dejar `receptor_elegido` y `regret` en null para esa jugada y excluirla de los promedios.
7. THE Backend SHALL reportar en `GET /api/resumen`, dentro de `calidad_datos.pct_objetivo_inferido`, el porcentaje de jugadas evaluadas cuyo Receptor_Inferido se obtuvo por el respaldo de `pass_arrived`.
8. WHEN el Dashboard solicita `GET /api/regret/equipos`, THE Motor_de_Regret SHALL responder con una lista `[{equipo, estimacion}]` donde `estimacion.valor` es el Índice_de_Regret promedio del equipo ofensivo.
9. WHERE el parámetro `zona` está presente, THE Motor_de_Regret SHALL filtrar el resultado a las jugadas cuya Zona del Receptor_Inferido coincide con ese valor.
10. IF el parámetro `zona` no pertenece al catálogo de zonas, THEN THE Backend SHALL responder HTTP 422 con una Respuesta_de_Error cuyo campo `codigo` sea `parametros_invalidos`.
11. THE Dashboard SHALL mostrar el ranking del Índice_de_Regret en el Tablero de Arrepentimiento con n y el semáforo de cada fila.
12. THE Dashboard SHALL mostrar el texto "contrafactual estimado" en la descripción de la métrica y aclarar que la Separación es un proxy.

### Requirement 6: Modo en vivo

**User Story:** Como coach ofensivo, quiero un modo en vivo que reproduzca los pases de un partido, para que pueda comparar la decisión real con el receptor más abierto jugada tras jugada.

#### Acceptance Criteria

1. WHEN el Dashboard solicita `GET /api/partidos`, THE Backend SHALL responder con una lista `[{gameId, semana, local, visitante, n_pases}]` con los 122 partidos de `games.csv`.
2. THE Servicio_en_Vivo SHALL numerar las Jugadas_Válidas de cada partido desde 1 en orden cronológico (quarter ascendente, gameClock descendente, playId ascendente) y usar ese número como `n`.
3. WHEN el Dashboard solicita `GET /api/partido/{gameId}/jugada/{n}`, THE Servicio_en_Vivo SHALL responder con el estado del partido y la jugada n con `down`, `yardsToGo`, `zona`, `marcador`, `reloj`, `receptor_elegido`, `receptor_mas_abierto`, `separaciones`, `regret` y `resultado`.
4. WHEN el Dashboard solicita `GET /api/partido/{gameId}/acumulado` con el parámetro `hasta=n`, THE Servicio_en_Vivo SHALL responder con el Regret acumulado, el Regret por zona y el Regret por lado, cada uno con su Estimación.
5. THE Servicio_en_Vivo SHALL calcular todas las respuestas de `/api/partido/{gameId}/...` usando únicamente las jugadas con número menor o igual a n, sin datos de jugadas posteriores a n.
6. IF el gameId solicitado no está en `/api/partidos`, THEN THE Backend SHALL responder HTTP 404 con una Respuesta_de_Error cuyo campo `codigo` sea `partido_no_encontrado`.
7. IF `n` o `hasta` es menor que 1 o mayor que `n_pases` del partido, THEN THE Backend SHALL responder HTTP 404 con una Respuesta_de_Error cuyo campo `codigo` sea `jugada_no_encontrada`.
8. WHEN el Servicio_en_Vivo presenta una jugada, THE Dashboard SHALL mostrar la situación, el receptor elegido, el receptor más abierto, la Separación de ambos y el Índice_de_Regret de esa jugada.
9. WHEN el usuario pulsa el control de avance en el Dashboard, THE Dashboard SHALL mostrar la siguiente jugada del partido seleccionado.

### Requirement 7: Dashboard usable

**User Story:** Como coach ofensivo, quiero un dashboard claro y usable en el celular, para que pueda consultarlo junto a la banda.

#### Acceptance Criteria

1. THE Dashboard SHALL ofrecer las pantallas Inicio, Sala de Decisiones, Evidencia, Tablero de Arrepentimiento y Modo en Vivo.
2. THE Dashboard SHALL mostrar en Inicio el titular y la línea de resumen de `GET /api/resumen` y el Regret de la liga.
3. THE Dashboard SHALL presentar los controles de la Sala de Decisiones para down, yardsToGo, zona y cobertura.
4. THE Dashboard SHALL mostrar un diseño usable desde un ancho de 375 px sin desplazamiento horizontal.
5. THE Dashboard SHALL cumplir una relación de contraste de al menos 4.5:1 en el texto y usar tamaño de fuente base de al menos 16 px.
6. THE Dashboard SHALL funcionar sin cargar fuentes ni recursos desde CDN externos.
7. WHILE el Backend responde HTTP 503 con `codigo` igual a `cargando`, THE Dashboard SHALL mostrar un mensaje de carga y reintentar la solicitud cada 2 segundos.
8. IF el Backend responde con una Respuesta_de_Error, THEN THE Dashboard SHALL mostrar el texto del campo `detail` al usuario.
9. THE Dashboard SHALL estar escrito en TypeScript con tipos explícitos para cada respuesta de la API.

### Requirement 8: Contrato de despliegue

**User Story:** Como equipo de desarrollo, quiero cumplir el contrato de despliegue de AWS, para que la aplicación funcione al publicarse tal cual en una subruta.

#### Acceptance Criteria

1. THE Dashboard SHALL llamar a la API con rutas relativas sin diagonal inicial, con la forma `fetch('api/<ruta>')`.
2. THE Dashboard SHALL referenciar imágenes, CSS y enlaces con rutas relativas sin diagonal inicial y sin `localhost`, `127.0.0.1` ni URLs absolutas.
3. THE Backend SHALL exponer toda su API bajo `/api/...` y `GET /health` en la raíz.
4. THE Backend SHALL servir el contenido de `dashboard/dist` y la API en la misma URL y puerto.
5. THE Dashboard SHALL configurar en `vite.config.ts` `base: './'` y un proxy de `/api` hacia `http://localhost:8000`.
6. THE Backend SHALL calcular sus resultados al arrancar o al responder, sin depender de escribir archivos en disco.
7. THE Backend SHALL usar solo las dependencias y versiones del stack fijo, sin Docker ni otros frameworks.
8. THE Backend SHALL implementar exactamente los endpoints del contrato: `GET /health`, `GET /api/resumen`, `GET /api/partidos`, `GET /api/partido/{gameId}/jugada/{n}`, `GET /api/partido/{gameId}/acumulado`, `GET /api/partido/{gameId}/alertas`, `GET /api/recomendacion`, `GET /api/regret/equipos`, `GET /api/evidencia`, `GET /api/explicacion` y `POST /api/chat`.
9. THE Backend SHALL devolver los textos de cara al usuario como objetos `{"es": ..., "en": ...}`.
10. THE Backend SHALL responder los errores con `{"detail", "codigo"}` y el código HTTP correcto: 422 por validación, 404 por recurso inexistente y 503 por carga en curso o fallida.

### Requirement 9: Pruebas automáticas

**User Story:** Como equipo de desarrollo, quiero pruebas automáticas de las reglas críticas, para que los umbrales y contratos no se rompan sin que lo notemos.

#### Acceptance Criteria

1. THE Backend SHALL incluir pruebas de pytest que verifiquen las tres reglas del Semáforo en los límites n igual a 29, 30, 99 y 100 y Ancho_IC igual a 0.99 y 1.0.
2. THE Backend SHALL incluir una prueba con httpx que verifique que `GET /health` responde `{"status": "ok"}` mientras el Estado_de_Carga es "cargando".
3. THE Backend SHALL incluir una prueba con httpx que verifique que un endpoint bajo `/api/...` responde HTTP 503 con `detail` y `codigo` mientras el Estado_de_Carga es "cargando".
4. THE Backend SHALL incluir una prueba que verifique que el Índice_de_Regret de toda jugada es mayor o igual a 0.
5. THE Backend SHALL incluir una prueba que verifique que las respuestas de `/api/partido/{gameId}/...` con `n` fijo no cambian al eliminar las jugadas posteriores a n.
6. THE Backend SHALL incluir pruebas que verifiquen la forma de cada respuesta del contrato contra los modelos Pydantic, tanto en Modo_MOCK como con datos reales.

### Requirement 10: Limitaciones visibles

**User Story:** Como lector del proyecto, quiero que la aplicación declare sus limitaciones, para que nadie interprete los resultados más allá de lo que los datos permiten.

#### Acceptance Criteria

1. THE Dashboard SHALL mostrar en una sección "Limitaciones" el texto de las limitaciones definidas en este documento.
2. THE README SHALL incluir la sección "Limitaciones" con el mismo contenido que la sección final de este documento.
3. THE README SHALL indicar en una nota que el valor se expresa en yardas esperadas y que no se estiman puntos esperados ni EPA.

### Requirement 11: Explicación con IA (opcional)

**User Story:** Como coach ofensivo, quiero una explicación breve del porqué de la recomendación, para que pueda comunicarla al equipo.

#### Acceptance Criteria

1. WHEN el Dashboard solicita `GET /api/explicacion` con los mismos parámetros que `GET /api/recomendacion`, THE Servicio_de_Explicación SHALL responder con HTTP 200 y `{texto{es,en}, fuente}` donde `fuente` es `ia` o `plantilla`.
2. IF el archivo `.env` no existe, THEN THE Servicio_de_Explicación SHALL responder con HTTP 200, la Plantilla_de_Explicación y `fuente` igual a `plantilla`.
3. IF la llamada a Amazon Bedrock falla, THEN THE Servicio_de_Explicación SHALL responder con HTTP 200, la Plantilla_de_Explicación y `fuente` igual a `plantilla`.
4. THE Servicio_de_Explicación SHALL crear el cliente con `boto3.client("bedrock-runtime", region_name=region)` donde `region` proviene de `os.environ.get("AWS_REGION", "us-east-1")`.
5. THE Servicio_de_Explicación SHALL leer el modelo con `os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")`.
6. THE Servicio_de_Explicación SHALL omitir la lectura, la verificación y la exigencia de AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY y AWS_SESSION_TOKEN.
7. THE Servicio_de_Explicación SHALL omitir el registro y la impresión de credenciales.
8. THE Backend SHALL cargar el `.env` al inicio de `backend/main.py`, antes de usar boto3, con la función `cargar_env` definida en las reglas del proyecto.
9. THE Backend SHALL mostrar la recomendación, n, el IC95% y el Semáforo aunque el Servicio_de_Explicación no esté disponible.
10. THE Servicio_de_Explicación SHALL usar Strands Agents con Amazon Bedrock como único proveedor de IA.

### Requirement 12: Interfaz bilingüe ES/EN (opcional)

**User Story:** Como usuario hispanohablante o angloparlante, quiero cambiar el idioma de la interfaz, para que pueda usar la aplicación en mi idioma.

#### Acceptance Criteria

1. WHERE la función bilingüe está habilitada, THE Dashboard SHALL mostrar un botón que alterna el idioma de la interfaz entre español e inglés.
2. WHERE la función bilingüe está habilitada, WHEN el usuario pulsa el botón de idioma, THE Dashboard SHALL mostrar todos los textos de la interfaz y los textos `{es,en}` del Backend en el idioma seleccionado sin recargar la página.
3. WHERE la función bilingüe está habilitada, THE Dashboard SHALL iniciar en español.

### Requirement 13: Modo banda lateral (opcional)

**User Story:** Como coach ofensivo, quiero un modo compacto de banda lateral, para que pueda leer la recomendación de un vistazo mientras sigo el partido.

#### Acceptance Criteria

1. WHERE el modo banda lateral está habilitado, WHEN el usuario activa el modo, THE Dashboard SHALL mostrar solo la acción recomendada, el Semáforo, n y el IC95% en una sola pantalla.
2. WHERE el modo banda lateral está habilitado, THE Dashboard SHALL mostrar la acción recomendada con un tamaño de fuente de al menos 32 px.
3. WHERE el modo banda lateral está habilitado, WHEN el usuario desactiva el modo, THE Dashboard SHALL restaurar la pantalla anterior.

### Requirement 14: Resumen de inicio

**User Story:** Como coach ofensivo, quiero ver el hallazgo principal al abrir la aplicación, para que entienda en una línea qué dicen los datos y qué tan confiables son.

#### Acceptance Criteria

1. WHEN el Dashboard solicita `GET /api/resumen`, THE Backend SHALL responder con `{titulo, linea, regret_liga, calidad_datos}` donde `titulo` y `linea` son textos `{es,en}`, `regret_liga` es una Estimación y `calidad_datos` contiene `pct_objetivo_inferido`.
2. THE Backend SHALL calcular `regret_liga` como el Índice_de_Regret promedio de todas las jugadas con Regret de los 122 partidos.
3. THE Backend SHALL generar `titulo` y `linea` con una plantilla que incluya el valor, el IC95% y n de `regret_liga`.
4. WHERE `regret_liga.concluyente` es false, THE Backend SHALL incluir en `linea` el texto "Aún no es concluyente".

### Requirement 15: Alertas deterministas

**User Story:** Como coach ofensivo, quiero alertas durante el modo en vivo, para que me avisen cuando el quarterback se esté perdiendo receptores abiertos de forma sistemática.

#### Acceptance Criteria

1. WHEN el Dashboard solicita `GET /api/partido/{gameId}/alertas` con el parámetro `hasta=n`, THE Motor_de_Alertas SHALL responder con una lista `[{id, nivel, titulo{es,en}, texto{es,en}, estimacion}]`.
2. THE Motor_de_Alertas SHALL generar las alertas con reglas deterministas y umbrales fijos definidos en el diseño, sin modelos de lenguaje ni aleatoriedad.
3. THE Motor_de_Alertas SHALL calcular las alertas usando únicamente las jugadas con número menor o igual a n.
4. WHEN dos solicitudes idénticas llegan al Motor_de_Alertas, THE Motor_de_Alertas SHALL responder la misma lista en el mismo orden.
5. WHERE la Estimación de una alerta tiene concluyente igual a false, THE Motor_de_Alertas SHALL asignar a la alerta el nivel `info` e incluir en el texto "Aún no es concluyente".

### Requirement 16: Chat con IA (opcional)

**User Story:** Como coach ofensivo, quiero hacer preguntas sobre el partido en curso, para que pueda entender las alertas y el regret sin leer tablas.

#### Acceptance Criteria

1. WHERE la función de IA está habilitada, WHEN el Dashboard envía `POST /api/chat` con `{gameId, hasta, mensaje}`, THE Servicio_de_Explicación SHALL responder con HTTP 200 y `{respuesta, fuente}`.
2. THE Servicio_de_Explicación SHALL construir el contexto del chat usando únicamente las jugadas con número menor o igual a `hasta`.
3. IF el Servicio_de_Explicación no está disponible o la llamada a Amazon Bedrock falla, THEN THE Backend SHALL responder con HTTP 200, una respuesta basada en plantilla y `fuente` igual a `plantilla`.
4. IF el cuerpo de `POST /api/chat` es inválido, THEN THE Backend SHALL responder HTTP 422 con una Respuesta_de_Error cuyo campo `codigo` sea `parametros_invalidos`.
5. IF el gameId no existe, THEN THE Backend SHALL responder HTTP 404 con una Respuesta_de_Error cuyo campo `codigo` sea `partido_no_encontrado`.

### Requirement 17: Datos MOCK para desarrollo del frontend

**User Story:** Como desarrollador del frontend, quiero que el Backend sirva datos de ejemplo con la forma exacta del contrato, para que pueda construir el Dashboard sin esperar a que el análisis esté terminado.

#### Acceptance Criteria

1. WHERE la variable de entorno `LJC_MOCK` es igual a `1`, THE Backend SHALL iniciar con Estado_de_Carga "listo" sin leer archivos de `data/`.
2. WHILE el Modo_MOCK está activo, THE Backend SHALL responder cada endpoint del contrato con datos deterministas que cumplen los mismos modelos Pydantic que las respuestas reales.
3. WHILE el Modo_MOCK está activo, THE Backend SHALL incluir ejemplos de Estimación con confianza verde, amarillo y rojo.
4. THE Backend SHALL mantener los datos MOCK en `backend/analytics/mock.py`.

## Limitaciones

1. **Proxy de separación:** la separación entre receptor y defensor se aproxima con el tracking en el frame `pass_forward` (distancia al defensor más cercano). No es una medición oficial de separación y depende de la calidad del Receptor_Inferido.
2. **Receptor inferido:** el dataset no identifica al receptor objetivo. El Receptor_Inferido se estima con `playDescription` y tracking y puede ser incorrecto. Las jugadas sin receptor identificable se excluyen del Regret.
3. **Muestra 2021, semanas 1 a 8:** los datos cubren 122 partidos de las semanas 1 a 8 de la temporada 2021. Las conclusiones no se extienden a otras temporadas ni a la temporada completa.
4. **Sin EPA:** el dataset no incluye EPA. El valor se expresa en yardas esperadas calculadas con Jugadas_Comparables, y no equivale a puntos esperados oficiales.
5. **Solo dropbacks:** `plays.csv` contiene únicamente Dropbacks (passResult no nulo). No hay carreras designadas, por lo que la app no compara pase contra carrera. Los sacks y scrambles no tienen evento `pass_forward` y no entran al análisis de Regret.
6. **Regret contrafactual:** el Índice_de_Regret usa la separación del receptor más abierto, no un resultado observado. Un receptor más abierto no garantiza una mejor jugada.
