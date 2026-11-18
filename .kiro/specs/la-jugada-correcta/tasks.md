# Implementation Plan: La Jugada Correcta (Plan de Implementación)

## Overview

Plan en siete fases, con tareas pequeñas y un criterio de aceptación en cada una. Cada tarea lleva una etiqueta de dueño:

- **[BACKEND]**: Christian. Trabaja en `backend/`, `tests/` y la carga de datos.
- **[FRONTEND]**: Marianne. Trabaja solo en `dashboard/`.

Convenciones:

- El contrato de API está congelado (ver `design.md`, "Contrato de API"). Ningún cambio de campos sin acuerdo de ambos.
- Backend: **un commit por paso** de Christian (pasos 1 a 5). Cuando un paso abarca varias tareas, el commit se hace al cerrar la última tarea del paso.
- Las tareas marcadas con `*` son opcionales según la decisión de alcance: IA (Requisitos 11 y 16), ES/EN (Requisito 12) y banda lateral (Requisito 13).
- Etiqueta **[PARALELO]**: la tarea puede avanzar al mismo tiempo que trabajo de la otra persona, sin esperar. Etiqueta **[SECUENCIAL]**: depende de una tarea anterior.
- Las pruebas de pytest del backend son parte del alcance (Requisito 9). El diseño define 15 propiedades de corrección y una estrategia de pruebas (`design.md`, "Testing Strategy"): las pruebas de las tareas 3.6, 3.7, 3.8, 5.2, 5.3, 5.9, 7.5 y 10.3 se implementan como pruebas de ejemplo más pruebas de propiedades de pytest (100 iteraciones con `numpy.random.default_rng` y semilla fija, sin agregar Hypothesis), con el comentario `# Feature: la-jugada-correcta, Property N`.
- Lenguajes: backend en Python 3.12 (FastAPI, pandas, numpy, Pydantic, pytest, httpx) y frontend en TypeScript (React, Vite, Tailwind, Recharts).

## Datos mock compartidos (acuerdo Backend y Frontend)

Estos datos viven en `backend/analytics/mock.py` y se sirven con `LJC_MOCK=1`. Son la única fuente de verdad para que Marianne trabaje sin esperar al análisis real.

| Elemento | Valor acordado |
|---|---|
| Activación | Variable de entorno `LJC_MOCK=1`. Estado de carga nace en `listo`. |
| Partidos | 3 partidos con 5 jugadas cada uno. `gameId` reales: `2021090900` y `2021091200` (más un tercero real de la semana 1 o 2). Equipos reales. |
| Determinismo | Mismos datos en cada llamada, sin aleatoriedad. |
| Estimaciones | Al menos una `verde`, una `amarillo` y una `rojo` repartidas entre recomendación, regret y alertas. |
| Alertas | Una de cada nivel: `info`, `aviso`, `critico`. |
| Catálogo de zonas | `corta_izquierda`, `corta_centro`, `corta_derecha`, `media_izquierda`, `media_centro`, `media_derecha`, `profunda_izquierda`, `profunda_centro`, `profunda_derecha`. |
| Recomendación de ejemplo | `GET /api/recomendacion?down=3&yardsToGo=5&zona=media_izquierda&cobertura=Man` devuelve la zona `media_izquierda`, valor 7.4, IC95% [5.9, 8.8], n=64, amarillo (ver `design.md`, "Modo MOCK"). |
| Errores | `gameId` o `n` fuera de los datos mock responden 404 (`partido_no_encontrado` o `jugada_no_encontrada`). Parámetros inválidos responden 422 (`parametros_invalidos`). |
| Textos | Todo texto de cara al usuario es `{"es": ..., "en": ...}`. |
| Estado de carga | Para probar el 503, el mock admite `LJC_MOCK_CARGANDO=1` (devuelve 503 `cargando`). |
| IA | `/api/explicacion` y `/api/chat` en mock responden `fuente: "plantilla"`. |

## Tasks

- [x] 1. Fase 1: Esqueleto end-to-end (health, una gráfica con datos reales, build servido por FastAPI)
  - [x] 1.1 [BACKEND] Paso 1 (parte A): `main.py` con `cargar_env()`, `/health` y servicio de `dashboard/dist` **[SECUENCIAL: primera tarea del backend]**
    - Crear `backend/main.py` con `app`, la función `cargar_env()` de `rules.md` al inicio (antes de importar boto3) y `GET /health` que responde `{"status": "ok"}`.
    - Montar `StaticFiles` sobre `dashboard/dist` con `html=True` como **último** montaje y solo si la carpeta existe.
    - Crear `backend/analytics/__init__.py` y `backend/analytics/config.py` con las constantes del diseño.
    - Aceptación: `GET /health` responde 200 `{"status": "ok"}`; sin `dashboard/dist` la app arranca sin error; sin `.env` la app arranca sin error y sin imprimir credenciales.
    - Prueba: cubierta por la tarea 1.8.
    - _Requisitos: 1.2, 1.3, 8.3, 8.4, 8.6, 8.7, 11.8_

  - [x] 1.2 [BACKEND] Paso 1 (parte B): modelos Pydantic, `mock.py` y endpoints MOCK conformes al contrato **[SECUENCIAL: después de 1.1]**
    - Crear `schemas.py` con todos los modelos del contrato (Estimación, Texto, Zona, recomendación, partidos, jugada, acumulado, alertas, regret por equipos, evidencia, explicación, chat, Respuesta_de_Error).
    - Crear `mock.py` con los datos de la sección "Datos mock compartidos" y `api.py` con las 11 rutas del contrato (`response_model` en cada una), manejadores de error `{"detail","codigo"}` y middleware de estado de carga (503 `cargando` y `error_de_carga`).
    - Con `LJC_MOCK=1` no se lanza el cargador y el estado nace en `listo`.
    - Aceptación: cada endpoint del contrato responde con la forma exacta del contrato en modo mock; hay estimaciones verde, amarillo y rojo; 404 y 422 devuelven `{"detail","codigo"}`.
    - Al terminar: hacer commit del Paso 1 y **avisar a Marianne dentro de los primeros 15 minutos** del trabajo, con el comando `LJC_MOCK=1 uvicorn backend.main:app --port 8000` y el enlace al commit.
    - _Requisitos: 8.3, 8.8, 8.9, 8.10, 17.1, 17.2, 17.3, 17.4_

  - [x] 1.3 [FRONTEND] Crear el proyecto `dashboard/` con Vite, React, TypeScript y Tailwind **[PARALELO: con 1.1 y 1.2]**
    - Configurar `vite.config.ts` con `base: './'` y proxy de `/api` hacia `http://localhost:8000`.
    - Configurar Tailwind sin fuentes ni recursos de CDN y tamaño de fuente base de 16 px.
    - Aceptación: `npm run build` genera `dashboard/dist` con rutas relativas (`./assets/...`); no aparece `localhost` ni `/` inicial en `dist/index.html`.
    - _Requisitos: 7.6, 7.9, 8.2, 8.5_

  - [x] 1.4 [FRONTEND] Tipos TypeScript del contrato y cliente de API **[PARALELO: con 1.2; usa la forma del contrato y de los datos mock]**
    - Definir tipos explícitos para cada respuesta (Estimación, Texto, Zona, Alerta, etc.) en `dashboard/src/api/tipos.ts`.
    - Crear el cliente `fetch('api/<ruta>')` (ruta relativa sin diagonal inicial) con manejo de 503 `cargando` (reintento cada 2 s) y de errores con `detail`.
    - Aceptación: el cliente nunca usa `/api/...` con diagonal inicial; ante 503 `cargando` reintenta cada 2 s y expone el estado "cargando"; ante otro error expone el texto de `detail`.
    - Prueba: prueba unitaria con `vitest` del reintento y del manejo de errores (opcional si el equipo no instala vitest).
    - _Requisitos: 7.7, 7.8, 7.9, 8.1_

  - [x] 1.5 [BACKEND] Paso 1 (parte C): carga mínima real de `games.csv` y `plays.csv` para `/api/partidos` con datos reales **[SECUENCIAL: después de 1.2]**
    - Crear `carga.py` con el `Estado` y un cargador mínimo en un hilo de fondo (sin tracking) que lee `games.csv` y `plays.csv` con `usecols`.
    - Hacer que `GET /api/partidos` responda con datos reales de los 122 partidos (`n_pases` provisional: jugadas de `plays.csv` con `passResult` en C, I o IN del partido). El resto de endpoints sigue en mock mientras no se reemplacen.
    - Supuesto: la "gráfica real" de la Fase 1 usa `/api/partidos` porque es el único dato real que no depende del tracking. La tarea 3.1 extiende este cargador.
    - Aceptación: sin `LJC_MOCK`, `/api/partidos` devuelve 122 elementos con equipos reales; mientras carga responde 503 `cargando`.
    - _Requisitos: 1.1, 1.4, 1.5, 1.7, 1.9, 6.1_

  - [x] 1.6 [FRONTEND] Primera gráfica real: pases por partido (Recharts) con `/api/partidos` **[SECUENCIAL: después de 1.4 y 1.5]**
    - Mostrar una gráfica de barras de `n_pases` por semana o por partido con datos del backend real.
    - Mostrar el estado de carga y el de error con el texto de `detail`.
    - Aceptación: con el backend real encendido, la gráfica muestra datos de los 122 partidos; con `LJC_MOCK=1` muestra los datos mock sin cambiar código.
    - _Requisitos: 4.4, 7.7, 7.8_

  - [x] 1.7 [FRONTEND] Generar `dashboard/dist` y verificar que FastAPI lo sirve en la misma URL y puerto **[SECUENCIAL: después de 1.6 y 1.1]**
    - Ejecutar `npm run build` y abrir `http://localhost:8000/` servido por FastAPI.
    - Aceptación: `/` muestra la gráfica; `/api/partidos` y `/health` responden en el mismo puerto; no hay llamadas a `localhost` ni rutas absolutas en el bundle.
    - _Requisitos: 8.1, 8.2, 8.4_

  - [x] 1.8 [BACKEND] Pruebas de humo con httpx: `/health` y 503 mientras carga **[PARALELO: con 1.5 y 1.6]**
    - Crear `tests/conftest.py` y `tests/test_estado_carga.py`.
    - Aceptación: `GET /health` devuelve `{"status": "ok"}` con el estado "cargando"; un endpoint `/api/...` devuelve 503 con `detail` y `codigo` igual a `cargando`; la prueba del archivo estático se omite (`skipif`) si no existe `dashboard/dist`.
    - _Requisitos: 9.2, 9.3_

- [x] 2. Checkpoint de Fase 1: esqueleto end-to-end
  - Ensure all tests pass, ask the user if questions arise.
  - Verificar entre Christian y Marianne: `/health` OK, una gráfica con datos reales, el build servido por FastAPI en un solo puerto y los datos mock acordados.

- [x] 3. Fase 2: Núcleo analítico y pytest (backend)
  - [x] 3.1 [BACKEND] Paso 2 (parte A): carga en memoria con hilos, `usecols` y frames de eventos **[SECUENCIAL: después de 1.5]**
    - Extender `carga.py`: `ThreadPoolExecutor` para leer los 122 `tracking_*.csv` con `usecols=COLS_TRACKING`, filtrar de inmediato los eventos `ball_snap`, `pass_forward`, `pass_arrived`, `autoevent_ballsnap` y `autoevent_passforward`.
    - Usar `autoevent_*` solo si falta el evento principal. Descartar los frames crudos al terminar.
    - Si un archivo requerido falla: estado `error` y mensaje sin rutas absolutas ni credenciales.
    - Aceptación: la carga completa termina en segundos (objetivo: unos 12 s en un hilo o menos), no usa más de lo necesario en memoria y el estado pasa a `listo`; `pass_forward` cubre cerca de 99.96 % de los pases C, I e IN con el sustituto.
    - _Requisitos: 1.1, 1.5, 1.6, 1.8, 1.9_

  - [x] 3.2 [BACKEND] Paso 2 (parte B): limpieza, features por jugada y unión con plays, games, players y pff **[SECUENCIAL: después de 3.1]**
    - Implementar `limpiar_plays()`: descartar nulos de contexto y `down` igual a 0; marcar `penalizada`.
    - Construir la tabla `jugadas` (una fila por Pase_Lanzado válido) con `down`, `yardsToGo`, `rango_ytg`, `cobertura`, `equipo`, `semana`, `playResult`, `quarter`, `gameClock`, marcador y los frames de tracking.
    - Unir con `games`, `players` y `pffScoutingData` (comparación de `pff_role` insensible a mayúsculas).
    - Aceptación: el recuento de pases con tracking es cercano a 7,562; no quedan jugadas con `down` 0 ni con `absoluteYardlineNumber` nulo; las penalizadas existen pero quedan marcadas.
    - _Requisitos: 1.10, 1.11, 1.12_

  - [x] 3.3 [BACKEND] Paso 2 (parte C): inferencia de receptor y porcentaje inferido **[SECUENCIAL: después de 3.2]**
    - Crear `receptor.py` (regex sobre `playDescription`, clave `inicial.Apellido` sin sufijos, cruce con el roster ofensivo, respaldo por cercanía en `pass_arrived`) y `calidad.py` (`pct_objetivo_inferido` y diagnóstico interno).
    - Aceptación: cerca de 94.7 % de las jugadas con pase y tracking resuelven receptor por texto; las demás quedan con `receptor_elegido` nulo y fuera del Regret; `pct_objetivo_inferido` se calcula como porcentaje de 0 a 100.
    - Commit del Paso 2 al cerrar 3.1 a 3.3.
    - _Requisitos: 5.4, 5.5, 5.6, 5.7_

  - [x] 3.4 [BACKEND] Paso 3 (parte A): `zonas.py` y `separacion.py` (separación, receptor más abierto, regret por jugada) **[SECUENCIAL: después de 3.2]**
    - Implementar profundidad (corta, media, profunda), lado (con perspectiva ofensiva), código de zona y rangos de `yardsToGo`.
    - Implementar separación mínima a defensores, proxy del receptor más abierto con desempate por menor `nflId` y regret por jugada.
    - Aceptación: el regret de toda jugada es mayor o igual a 0; el receptor elegido siempre pertenece al conjunto elegible; existen exactamente 9 códigos de zona.
    - _Requisitos: 5.1, 5.2, 5.3_

  - [x] 3.5 [BACKEND] Paso 3 (parte B): `estimacion.py` con bootstrap reproducible y semáforo **[PARALELO: con 3.1 a 3.4; no depende de datos]**
    - Implementar `semaforo()`, `bootstrap_ic()` con semilla fija (`SEMILLA=2021`, 1000 remuestreos en bloques) y `construir_estimacion()` (n igual a 0 devuelve rojo; `ic95` degenerado con n igual a 1).
    - Aceptación: mismas observaciones producen el mismo IC95%; `concluyente` es true solo para verde y amarillo.
    - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.7, 3.8_

  - [x] 3.6 [BACKEND] Pruebas pytest de `estimacion.py`: semáforo en límites y bootstrap reproducible **[SECUENCIAL: después de 3.5]**
    - Crear `tests/test_estimacion.py`: n = 29, 30, 99 y 100; ancho = 0.99 y 1.0; n igual a 0 y n igual a 1; mismo arreglo da el mismo IC dos veces.
    - Aceptación: todas las pruebas pasan y fallan si se cambia un umbral de `config.py`.
    - _Requisitos: 3.2, 3.3, 3.4, 3.7, 9.1_

  - [x] 3.7 [BACKEND] Pruebas pytest de receptor, zonas y regret **[SECUENCIAL: después de 3.3 y 3.4]**
    - Crear `tests/test_receptor_regret.py` con casos sintéticos y casos reales: parseo de `D.Prescott pass deep left to A.Cooper`, apellido con sufijo y con inicial doble (`O.J. Howard`), nombre ambiguo, jugada sin objetivo nombrado, respaldo con `pass_arrived`, regret mayor o igual a 0 en todas las jugadas reales, empates y zonas en los bordes (5 y 15 yd, ±5 yd).
    - Aceptación: pasan con datos sintéticos sin leer `data/`; las de datos reales se omiten si falta `data/`.
    - _Requisitos: 5.1, 5.3, 5.4, 5.5, 5.6, 9.4_

  - [x] 3.8 [BACKEND] Paso 3 (parte C): validación Pydantic de parámetros con 422 `parametros_invalidos` y su prueba **[PARALELO: con 3.1 a 3.5; solo toca `schemas.py`, `api.py` y un archivo de prueba nuevo]**
    - Modelos de consulta para `down` (1 a 4), `yardsToGo` (mínimo 1), `zona` (catálogo) y `cobertura` (solo `Man` y `Zone`) y manejador de `RequestValidationError` a `{"detail","codigo":"parametros_invalidos"}`.
    - Crear `tests/test_validacion.py` con httpx en modo mock.
    - Commit del Paso 3 al cerrar 3.4 a 3.8.
    - Aceptación: `down=0`, `down=5`, `yardsToGo=0`, `zona=xx` y `cobertura=Other` responden 422 con `codigo` igual a `parametros_invalidos`; una consulta válida responde 200.
    - _Requisitos: 2.5, 2.6, 4.5, 5.10, 8.10_

- [x] 4. Checkpoint de Fase 2: núcleo analítico verificado
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `pytest` y confirmar que el backend carga los datos reales en hilos y que `/health` responde durante la carga.

- [x] 5. Fase 3: Pantallas (frontend) y endpoints reales de recomendación, evidencia y resumen
  - [x] 5.1 [FRONTEND] Layout, navegación entre las 5 pantallas y componentes base **[PARALELO: con las tareas 3.x del backend; usa datos mock]**
    - Crear navegación para Inicio, Sala de Decisiones, Evidencia, Tablero de Arrepentimiento y Modo en Vivo.
    - Crear componentes reutilizables: `Semaforo`, `EstimacionCard` (n, IC95%, semáforo y el texto "Aún no es concluyente" cuando `concluyente` es false), `EstadoCarga`, `EstadoError` y `EstadoVacio`.
    - Aceptación: contraste mínimo de 4.5:1, fuente base de 16 px, sin scroll horizontal a 375 px; el semáforo no depende solo del color (incluye texto o icono).
    - _Requisitos: 3.5, 3.6, 7.1, 7.4, 7.5, 7.7, 7.8_

  - [x] 5.2 [BACKEND] Paso 4 (parte A): `comparables.py` y `GET /api/recomendacion` real con estados vacío y error **[SECUENCIAL: después de 3.2, 3.4 y 3.5]**
    - Implementar `recomendar()`: línea base por down y rango de `yardsToGo` (y cobertura si se especifica), exclusión de jugadas penalizadas, mejor zona con n de 30 o más (o con n mayor que 0 si ninguna llega), desempate por valor y luego por zona, hasta 50 comparables ordenados por cercanía.
    - Crear `textos.py` con `accion` y `porque` bilingües (incluye "yardas esperadas" y "no es EPA oficial").
    - Estado vacío: sin comparables devuelve estimación n igual a 0, rojo y `concluyente` false.
    - Conectar la ruta real en `api.py` (el servicio real reemplaza al mock cuando `LJC_MOCK` no está).
    - Aceptación: respuesta con la forma del contrato; el filtro de cobertura aplica; una situación sin datos devuelve el estado vacío con HTTP 200.
    - Prueba: `tests/test_recomendacion.py` con un `Almacen` sintético (zona ganadora, desempate, vacío, cobertura `Other` solo cuenta sin filtro).
    - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.7, 2.8, 4.2, 4.3_

  - [x] 5.3 [BACKEND] Paso 4 (parte B): `GET /api/evidencia` real **[SECUENCIAL: después de 5.2]**
    - Series: distribución de `playResult` por zona (bins de 5 yd de -10 a 40, con último bin acumulado), `valor_por_zona`, `valor_por_cobertura` (Man, Zone y Otra) y `regret_por_zona`.
    - Aceptación: forma conforme al contrato; parámetros fuera de rango dan 422; una situación sin datos devuelve series vacías con HTTP 200.
    - Prueba: `tests/test_evidencia.py` (bins, borde de 40 yd, vacío).
    - _Requisitos: 4.1, 4.5_

  - [x] 5.4 [BACKEND] Paso 4 (parte C): `regret.py` y `GET /api/resumen` real **[SECUENCIAL: después de 5.3]**
    - Implementar la agregación de regret por liga, equipo, zona y lado; `resumen` con `regret_liga`, `calidad_datos.pct_objetivo_inferido` y plantilla de `titulo` y `linea` (con el texto "Aún no es concluyente" cuando aplica).
    - Aceptación: `regret_liga` usa todas las jugadas con regret; la forma coincide con el contrato; el título incluye valor, IC95% y n.
    - _Requisitos: 5.7, 14.1, 14.2, 14.3, 14.4_

  - [x] 5.5 [FRONTEND] Pantalla Inicio **[PARALELO: usa mock hasta que 5.4 esté lista]**
    - Mostrar `titulo`, `linea`, `regret_liga` (con `EstimacionCard`) y `pct_objetivo_inferido`.
    - Aceptación: muestra el estado de carga con 503 `cargando` y el `detail` en errores; el texto "contrafactual estimado" aparece junto al Regret.
    - _Requisitos: 5.12, 7.2, 14.1_

  - [x] 5.6 [FRONTEND] Pantalla Sala de Decisiones **[PARALELO: usa mock hasta que 5.2 esté lista]**
    - Controles de `down`, `yardsToGo`, `zona` y `cobertura` (solo estos cuatro). Mostrar `accion`, `porque`, estimación con n, IC95% y semáforo, y la tabla de `comparables`.
    - Estados vacío (n igual a 0), 422 (mostrar `detail`) y carga.
    - Aceptación: cambiar un control actualiza la recomendación; con n menor que 30 aparece "Aún no es concluyente".
    - _Requisitos: 2.1, 3.5, 3.6, 7.3, 7.7, 7.8_

  - [x] 5.7 [FRONTEND] Pantalla Evidencia con gráficas Recharts **[PARALELO: usa mock hasta que 5.3 esté lista]**
    - Gráficas: distribución de yardas por zona, valor por cobertura con barras de error del IC95% y regret por zona.
    - Aceptación: las series de `/api/evidencia` se muestran sin desbordar a 375 px; estado vacío con mensaje claro.
    - _Requisitos: 4.1, 4.4, 7.4_

  - [x] 5.8 [FRONTEND] Sección "Limitaciones" **[PARALELO: independiente]**
    - Mostrar las 6 limitaciones del documento de requisitos y la nota de que el valor está en yardas esperadas y no es EPA.
    - Aceptación: el texto coincide con la sección "Limitaciones" de `requirements.md`.
    - _Requisitos: 10.1_

  - [x] 5.9 [BACKEND] Pruebas de forma del contrato contra los modelos Pydantic, en mock y con datos reales **[SECUENCIAL: después de 5.4]**
    - Crear `tests/test_contrato.py`: cada endpoint existente valida contra su `response_model` en modo mock; las respuestas con datos reales se omiten (`skipif`) si falta `data/`.
    - Commit del Paso 4 (parcial) al cerrar 5.2 a 5.4 y 5.9.
    - Aceptación: pasan en ambos modos.
    - _Requisitos: 9.6_

- [ ] 6. Checkpoint de Fase 3: recomendación, evidencia e inicio con datos reales
  - Ensure all tests pass, ask the user if questions arise.
  - Marianne cambia de mock a backend real y confirma que Inicio, Sala de Decisiones y Evidencia funcionan sin cambios de código.

- [x] 7. Fase 4: Regret Index, modo en vivo y alertas
  - [x] 7.1 [BACKEND] Paso 4 (parte D): `partido.py`, `GET /api/partidos` completo y `GET /api/partido/{gameId}/jugada/{n}` **[SECUENCIAL: después de 5.4]**
    - Numerar jugadas por (quarter, gameClock descendente, playId) de 1 a `n_pases`; `n_pases` real reemplaza al provisional de 1.5.
    - La jugada n incluye situación, `marcador`, `reloj`, `receptor_elegido`, `receptor_mas_abierto`, `separaciones`, `regret` y `resultado`.
    - Errores: 404 `partido_no_encontrado` y 404 `jugada_no_encontrada` (n menor que 1 o mayor que `n_pases`).
    - Aceptación: los 122 partidos aparecen con `n_pases` coherente; la numeración es estable entre llamadas.
    - _Requisitos: 6.1, 6.2, 6.3, 6.6, 6.7_

  - [x] 7.2 [BACKEND] Paso 4 (parte E): `GET /api/partido/{gameId}/acumulado?hasta=n` con corte temporal **[SECUENCIAL: después de 7.1]**
    - Toda función de `partido.py` empieza filtrando `n <= hasta`. Si `hasta` se omite, el valor por defecto es `n_pases`.
    - Respuesta: `{hasta, n_con_regret, total_yd, estimacion, por_zona[], por_lado[]}`, cada elemento con su estimación.
    - Aceptación: ningún dato de jugadas posteriores a n influye en el resultado; estado vacío (cero jugadas con regret) devuelve estimación roja con n igual a 0.
    - _Requisitos: 6.4, 6.5, 6.7_

  - [x] 7.3 [BACKEND] Paso 4 (parte F): `GET /api/regret/equipos?zona=` real **[SECUENCIAL: después de 7.2]**
    - Orden por regret promedio descendente y luego por equipo; un equipo sin jugadas en la zona no aparece; `zona` inválida da 422.
    - Aceptación: lista `[{equipo, estimacion}]` conforme al contrato; con `zona` filtra por la zona del receptor inferido.
    - _Requisitos: 5.8, 5.9, 5.10_

  - [x] 7.4 [BACKEND] Paso 4 (parte G): `alertas.py` y `GET /api/partido/{gameId}/alertas?hasta=n` **[SECUENCIAL: después de 7.3]**
    - Reglas: `regret_alto`, `zona_ciega:<zona>`, `racha` y `datos_insuficientes` con los umbrales de `config.py`; orden por gravedad y luego por `id`.
    - Regla de concluyencia: si `concluyente` es false, el nivel pasa a `info` y el texto incluye "Aún no es concluyente".
    - Aceptación: dos solicitudes idénticas devuelven la misma lista en el mismo orden; solo usa jugadas hasta n; textos `{es,en}`.
    - _Requisitos: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 7.5 [BACKEND] Pruebas: corte temporal, alertas, 404 y orden del ranking **[SECUENCIAL: después de 7.4]**
    - Crear `tests/test_partido.py` y `tests/test_alertas.py`: la respuesta de `jugada`, `acumulado` y `alertas` con n fijo no cambia al eliminar las jugadas posteriores a n; determinismo de alertas; regla de concluyencia; 404 con `codigo` correcto; orden y desempate del ranking de equipos.
    - Commit del Paso 4 (final) al cerrar 7.1 a 7.5.
    - Aceptación: todas las pruebas pasan.
    - _Requisitos: 6.5, 9.4, 9.5, 15.3, 15.4_

  - [x] 7.6 [FRONTEND] Tablero de Arrepentimiento **[PARALELO: usa mock; real cuando 7.3 esté lista]**
    - Ranking de equipos con n y semáforo por fila, filtro por zona, texto "contrafactual estimado" y aclaración de que la separación es un proxy.
    - Aceptación: estado vacío cuando un filtro no devuelve equipos; filas con n menor que 30 muestran "Aún no es concluyente".
    - _Requisitos: 5.11, 5.12_

  - [x] 7.7 [FRONTEND] Modo en Vivo: selector de partido, jugada n y control de avance **[PARALELO: usa mock; real cuando 7.1 esté lista]**
    - Selector de partido (`/api/partidos`), vista de la jugada con situación, receptor elegido, receptor más abierto, separación de ambos y regret; botón de avance que pide la jugada n+1.
    - Aceptación: avanzar muestra la siguiente jugada; al llegar a `n_pases` el botón se deshabilita; 404 muestra el `detail`.
    - _Requisitos: 6.8, 6.9_

  - [x] 7.8 [FRONTEND] Regret acumulado y panel de alertas en Modo en Vivo **[SECUENCIAL: después de 7.7]**
    - Mostrar acumulado total, por zona y por lado (cada uno con `EstimacionCard`) y la lista de alertas con color y texto por nivel; el texto "Aún no es concluyente" aparece cuando corresponde.
    - Aceptación: al avanzar de n, el acumulado y las alertas se vuelven a pedir con `hasta=n`.
    - _Requisitos: 6.4, 15.1, 15.5_

- [ ] 8. Checkpoint de Fase 4: Regret, modo en vivo y alertas
  - Ensure all tests pass, ask the user if questions arise.
  - Recorrer un partido completo en el modo en vivo con datos reales y confirmar que no aparecen datos de jugadas posteriores.

- [x] 9. Fase 5: Pulido móvil, ES/EN y banda lateral
  - [x] 9.1 [FRONTEND] Pulido móvil, accesibilidad y revisión de rutas relativas **[SECUENCIAL: después de 7.8]**
    - Revisar las 5 pantallas a 375 px sin scroll horizontal, contraste mínimo de 4.5:1, fuente base de 16 px, objetivos táctiles amplios, sin CDN ni fuentes externas.
    - Buscar y eliminar `localhost`, `127.0.0.1`, URLs absolutas y rutas con diagonal inicial en el código y en `dist`.
    - Aceptación: lista de verificación cumplida y `npm run build` sin advertencias de tipos.
    - _Requisitos: 7.4, 7.5, 7.6, 8.1, 8.2_

  - [ ]* 9.2 [FRONTEND] Interfaz bilingüe ES/EN **[SECUENCIAL: después de 9.1; opcional según alcance]**
    - Botón de idioma, inicio en español, diccionario de textos de interfaz y selección de `es` o `en` en los textos `{es,en}` del backend, sin recargar la página.
    - Aceptación: al alternar, todos los textos cambian al instante; no quedan textos fijos sin traducir.
    - _Requisitos: 12.1, 12.2, 12.3_

  - [ ]* 9.3 [FRONTEND] Modo banda lateral **[SECUENCIAL: después de 9.2; opcional según alcance]**
    - Pantalla compacta con solo la acción recomendada (fuente de al menos 32 px), semáforo, n e IC95%; botón para activar y desactivar que restaura la pantalla anterior.
    - Aceptación: en 375 px la acción, el semáforo, n y el IC95% caben sin desplazamiento.
    - _Requisitos: 13.1, 13.2, 13.3_

- [ ] 10. Fase 6: Panel de IA (opcional; el chat libre va al último)
  - [ ]* 10.1 [BACKEND] Paso 5 (parte A): `ia.py` con Strands y Bedrock y `GET /api/explicacion` con fallback **[SECUENCIAL: después de 7.5; opcional según alcance]**
    - Seguir `rules.md`: `boto3.client("bedrock-runtime", region_name=region)`, `AWS_REGION` y `BEDROCK_MODEL_ID` desde `os.environ`, sin leer ni registrar credenciales. Validar si la asignación del cliente a `BedrockModel` funciona en Strands 1.64.0 y, si no, usar la alternativa del diseño.
    - Caché en memoria, tiempo de espera de 8 s, parseo del formato `---` y plantilla bilingüe de respaldo.
    - Aceptación: sin `.env`, con error de Bedrock o con respuesta mal formada responde HTTP 200 con `fuente: "plantilla"`; nunca devuelve el texto de la excepción.
    - _Requisitos: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.9, 11.10_

  - [ ]* 10.2 [BACKEND] Paso 5 (parte B): `POST /api/chat` **[SECUENCIAL: después de 10.1; opcional según alcance]**
    - Contexto construido solo con jugadas hasta `hasta`, mensaje recortado a 500 caracteres y tratado como dato; respuesta `{respuesta, fuente}`.
    - Errores: cuerpo inválido da 422 `parametros_invalidos`; `gameId` inexistente da 404 `partido_no_encontrado`; fallo de IA da 200 con plantilla.
    - Aceptación: el contexto enviado al modelo no contiene jugadas posteriores a `hasta`.
    - _Requisitos: 16.1, 16.2, 16.3, 16.4, 16.5_

  - [ ]* 10.3 [BACKEND] Pruebas de IA y fallback con Bedrock simulado **[SECUENCIAL: después de 10.2; opcional según alcance]**
    - Crear `tests/test_ia.py` que simula fallos (sin `.env`, excepción, tiempo agotado, formato inválido) y verifica HTTP 200 con `fuente` igual a `plantilla`, sin credenciales en la respuesta, y el 422 y el 404 del chat.
    - Commit del Paso 5 al cerrar 10.1 a 10.3.
    - Aceptación: pasan sin llamar a AWS.
    - _Requisitos: 11.2, 11.3, 11.7, 16.3, 16.4, 16.5_

  - [ ]* 10.4 [FRONTEND] Panel de explicación con IA en la Sala de Decisiones **[PARALELO: con 10.1; usa mock con `fuente: "plantilla"`; opcional según alcance]**
    - Mostrar `texto` de `/api/explicacion`, indicar si la fuente es `ia` o `plantilla` y mantener visibles la recomendación, n, IC95% y semáforo si la explicación falla.
    - Aceptación: con la IA caída, la recomendación y la incertidumbre siguen visibles.
    - _Requisitos: 11.1, 11.9_

  - [ ]* 10.5 [FRONTEND] Chat libre en Modo en Vivo (último) **[SECUENCIAL: después de 10.4 y 10.2; opcional según alcance]**
    - Caja de chat que envía `{gameId, hasta, mensaje}` a `POST api/chat`, muestra `respuesta` y `fuente`, y limita el mensaje a 500 caracteres.
    - Aceptación: el chat usa el `n` actual del modo en vivo; ante error muestra `detail`.
    - _Requisitos: 16.1_

- [ ] 11. Fase 7: README
  - [ ] 11.1 [BACKEND] README: ejecución, contrato, limitaciones y nota de yardas esperadas **[SECUENCIAL: después de la última tarea de código del backend]**
    - Pasos para correr backend, tests y modo mock; sección "Limitaciones" idéntica a la de `requirements.md`; nota de que el valor es en yardas esperadas y no EPA; corregir la viñeta de "Índice de Arrepentimiento" y el texto de pase o carrera según los hallazgos del diseño.
    - Aceptación: un compañero nuevo puede arrancar el proyecto con solo el README.
    - _Requisitos: 10.2, 10.3_

  - [ ] 11.2 [FRONTEND] README: sección del dashboard (instalar, desarrollar, construir) **[SECUENCIAL: después de 11.1]**
    - Comandos `npm install`, `npm run dev` (proxy a 8000) y `npm run build`, y la regla de rutas relativas.
    - Aceptación: los comandos documentados funcionan tal cual.
    - _Requisitos: 8.1, 8.2, 8.5_

- [x] 12. Checkpoint final
  - Ensure all tests pass, ask the user if questions arise.
  - Verificar con `npm run build` y el backend real: un solo puerto, `/health` OK, las 5 pantallas con datos reales y las limitaciones visibles.

## Paralelismo Backend y Frontend

| Fase | Backend (Christian) | Frontend (Marianne) | Relación |
|---|---|---|---|
| 1 | 1.1, 1.2, 1.5, 1.8 | 1.3, 1.4, 1.6, 1.7 | 1.3 y 1.4 son paralelas a 1.1 y 1.2; 1.6 espera a 1.5. |
| 2 | 3.1 a 3.8 | (sin tareas propias) | Marianne puede adelantar 5.1 con datos mock. |
| 3 | 5.2, 5.3, 5.4, 5.9 | 5.1, 5.5 a 5.8 | Paralelas con mock; cambio a datos reales al terminar el backend. |
| 4 | 7.1 a 7.5 | 7.6 a 7.8 | Paralelas con mock; 7.8 espera a 7.7. |
| 5 | (sin tareas) | 9.1 a 9.3 | Solo frontend. |
| 6 | 10.1 a 10.3 | 10.4, 10.5 | 10.4 es paralela a 10.1; 10.5 espera al backend. |
| 7 | 11.1 | 11.2 | 11.2 espera a 11.1 para evitar conflicto en el mismo archivo. |

## Notes

- Las tareas con `*` (9.2, 9.3, 10.1 a 10.5) son opcionales según la decisión de alcance y se pueden omitir sin afectar el núcleo.
- Los commits del backend siguen los cinco pasos de Christian: Paso 1 (1.1 a 1.2, con 1.5 como extensión), Paso 2 (3.1 a 3.3), Paso 3 (3.4 a 3.8), Paso 4 (5.2 a 5.4, 7.1 a 7.5) y Paso 5 (10.1 a 10.3).
- Todo cambio de campos del contrato o de los datos mock se acuerda entre ambos antes de implementarse.
- Este flujo solo produce artefactos de planificación; no implementa la funcionalidad.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3"] },
    { "id": 1, "tasks": ["1.2", "1.4"] },
    { "id": 2, "tasks": ["1.5", "1.8"] },
    { "id": 3, "tasks": ["1.6", "3.1", "3.5", "3.8"] },
    { "id": 4, "tasks": ["1.7", "3.2", "3.6", "5.1"] },
    { "id": 5, "tasks": ["3.3", "3.4", "5.5", "5.6", "5.7", "5.8"] },
    { "id": 6, "tasks": ["3.7", "5.2", "7.6", "7.7"] },
    { "id": 7, "tasks": ["5.3", "7.8"] },
    { "id": 8, "tasks": ["5.4", "9.1"] },
    { "id": 9, "tasks": ["5.9", "7.1", "9.2"] },
    { "id": 10, "tasks": ["7.2", "9.3"] },
    { "id": 11, "tasks": ["7.3", "10.4"] },
    { "id": 12, "tasks": ["7.4"] },
    { "id": 13, "tasks": ["7.5"] },
    { "id": 14, "tasks": ["10.1"] },
    { "id": 15, "tasks": ["10.2"] },
    { "id": 16, "tasks": ["10.3", "10.5"] },
    { "id": 17, "tasks": ["11.1"] },
    { "id": 18, "tasks": ["11.2"] }
  ]
}
```
