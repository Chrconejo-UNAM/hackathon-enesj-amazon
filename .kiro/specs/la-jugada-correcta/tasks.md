# Implementation Plan: La Jugada Correcta

## Overview

Orden de entrega: 1) esqueleto end-to-end, 2) núcleo analítico + pytest, 3) pantallas, 4) Regret + modo en vivo + alertas, 5) pulido (375 px, ES/EN, Banda Lateral, accesibilidad), 6) panel IA, 7) integración y README.

Reparto en paralelo con el contrato de `design.md` congelado:
- **[BACKEND]** Christian, solo `backend/` (y `backend/tests/`).
- **[FRONTEND]** Marianne, solo `dashboard/`. Trabaja con mocks hasta que Christian avise.
- **[FRONTEND + BACKEND]** solo en integración.

Cada tarea [FRONTEND] termina con `npm run build` (en `dashboard/`) sin errores de TypeScript. Cada tarea [BACKEND] con prueba corre `pytest` en `backend/tests/` dentro de `.venv`.

Reglas de despliegue (criterio en cada tarea que toca rutas o configuración):
- `fetch('api/...')` sin diagonal inicial; sin `localhost`, `127.0.0.1` ni URLs absolutas en `dashboard/src`.
- `vite.config.ts` con `base: './'` y proxy `/api` → `http://localhost:8000` solo en desarrollo.
- Sin dependencias nuevas. Sin escribir a disco en el servidor. Sin llaves en código.

Estado actual a preservar: en `dashboard/` ya existen `src/types.ts`, `src/api.ts`, `src/mocks/index.ts`, `src/useApi.ts`, `src/vite-env.d.ts` y `vite.config.ts` (con `base: './'` y proxy `/api`). Tailwind 3 ya está configurado. El build NO está verificado (falta Node en el PATH del usuario), por eso la tarea 1.1 queda pendiente.

## Tasks

- [ ] 1. Esqueleto end-to-end (`/health` + una gráfica con datos reales servida por FastAPI)
  - [x] 1.1 [FRONTEND] Verificar lo ya creado: `types.ts`, `api.ts`, `mocks/index.ts`, `useApi.ts`, `vite-env.d.ts`, `vite.config.ts` y Tailwind 3 (en paralelo con 1.2)
    - Agregar Node al PATH, correr `npm install` y `npm run build`; corregir errores de TypeScript que aparezcan. No marcar completada hasta que el build pase.
    - Criterio de aceptación: `npm run build` pasa sin errores TS y genera `dashboard/dist`; `vite.config.ts` conserva `base: './'` y proxy `/api` solo en dev; `api.ts` usa `fetch('api/...')` sin diagonal inicial.
    - Prueba: `npm run build`; `grep` de `'/api` y `localhost` en `dashboard/src` sin resultados.
    - _Requisitos: 9.3, 10.4, 10.5, 10.6_
  - [ ] 1.2 [BACKEND] Crear `backend/main.py` con `app`, `cargar_env()` exacto de `rules.md`, `GET /health` → `{"status":"ok"}`, manejadores de error `{detail, codigo}` (400, 404, 422, 500) e inclusión automática de todo `router` en `backend/rutas/*.py`
    - Criterio de aceptación: `GET /health` responde `{"status":"ok"}`; un 404 y un 422 devuelven `{"detail","codigo"}` con `NO_ENCONTRADO` y `VALIDACION`; no se leen ni exigen variables `AWS_*`.
    - Prueba: `backend/tests/test_salud_errores.py` (httpx) para `/health` y formato de errores.
    - _Requisitos: 9.1, 9.2_
  - [ ] 1.3 [BACKEND] Cargar `games.csv` y `plays.csv` desde `data/` (ruta relativa a la raíz) en `backend/datos.py` y exponer `GET /api/partidos` (`gameId, semana, local, visitante, n_pases`) en `backend/rutas/partidos.py`
    - Criterio de aceptación: devuelve 122 partidos con la forma del contrato; `n_pases` son jugadas de pase con receptor identificable o, en este esqueleto, pases de `plays.csv`; todo en memoria.
    - Prueba: `backend/tests/test_partidos.py`: longitud 122 y claves del contrato.
    - _Requisitos: 3.1, 9.1, 9.6_
  - [x] 1.4 [FRONTEND] Gráfica Recharts de barras `n_pases` por partido en `App.tsx` usando `useApi` + `api.ts` (`GET api/partidos`) con Cargando, Vacío y Error
    - Criterio de aceptación: con el mock de `partidos` encendido se ve la gráfica; con el mock apagado y el proxy a `localhost:8000` (solo dev) se ve con datos reales; sin desplazamiento horizontal a 375 px.
    - Prueba: `npm run build`; verificación manual a 375 px y con backend apagado (se ve el estado Error con Reintentar).
    - _Requisitos: 9.3, 10.1, 10.7_
  - [ ] 1.5 [FRONTEND + BACKEND] Servir `dashboard/dist` desde FastAPI en la misma URL y puerto y verificar el esqueleto completo
    - Criterio de aceptación: con `npm run build` y `uvicorn backend.main:app --port 8000`, `http://localhost:8000/` muestra la gráfica con datos reales y `/health` responde ok; los assets cargan con rutas relativas (probar también bajo una subruta simulada).
    - Prueba: manual (abrir en navegador) + `pytest` de `GET /` devolviendo HTML cuando `dist` existe.
    - _Requisitos: 9.1, 10.5, 10.6_

- [ ] 2. Núcleo analítico + pytest [BACKEND] (Christian, en paralelo con los pasos [FRONTEND] de las secciones 3-5)
  - [ ] 2.1 [BACKEND] `backend/tracking.py`: leer los 122 CSV con `usecols` mínimo (gameId, playId, nflId, frameId, team, x, y, playDirection, event), `chunksize`, solo `event == "pass_forward"` y `"pass_arrived"` (igualdad exacta)
    - Criterio de aceptación: no se cuentan frames `autoevent_passforward`; la memoria queda acotada; no se escribe a disco.
    - Prueba: `test_tracking.py` con un CSV mínimo que incluya `autoevent_passforward` y verifique que se excluye.
    - _Requisitos: 9.6_
  - [ ] 2.2 [BACKEND] `backend/analitica.py` (parte 1): normalizar `x`,`y` a ataque hacia la derecha y calcular la separación de cada candidato (`pff_role == "Pass Route"`) al defensor `Coverage` más cercano en `pass_forward`
    - Criterio de aceptación: con `playDirection` left y right la misma jugada simétrica da las mismas separaciones; separación ≥ 0.
    - Prueba: `test_separacion.py` con jugada sintética.
    - _Requisitos: 3.2, 8.1_
  - [ ] 2.3 [BACKEND] `backend/receptor.py`: inferir receptor elegido desde `playDescription` (inicial + apellido contra `players.displayName` de candidatos) con respaldo al candidato más cercano al balón en `pass_arrived` (`inferido=true`); excluir sacks `S` y scrambles `R`
    - Criterio de aceptación: "C.Godwin" resuelve a "Chris Godwin" entre los candidatos; sin coincidencia usa el respaldo y marca `inferido=true`; se calcula `pct_objetivo_inferido`.
    - Prueba (no opcional): `test_receptor.py`: coincidencia por inicial+apellido, homónimos de apellido con inicial distinta, respaldo y exclusión de sacks.
    - _Requisitos: 9.7, 1.3_
  - [ ] 2.4 [BACKEND] `backend/analitica.py` (parte 2): Regret, zona (`propia` >50, `medio` 21-50, `roja` ≤20), lado (orientado a la dirección de ataque) y éxito (40 % en 1ª, 60 % en 2ª, 100 % en 3ª y 4ª)
    - Criterio de aceptación: `regret = max(separaciones) − separación del elegido`, siempre ≥ 0; los límites 20/21 y 50/51 caen en la zona correcta; `down` vacío se excluye del filtro afectado.
    - Prueba: `test_zona_exito.py` con valores límite.
    - _Requisitos: 3.2, 8.1_
  - [ ] 2.5 [BACKEND] `backend/estadistica.py`: bootstrap percentil IC95 % (1000 remuestreos, semilla fija) y `estimacion()` que devuelve `{valor, ic95, n, concluyente, confianza}` con las reglas del semáforo
    - Criterio de aceptación: n<30 → rojo y `concluyente=false`; n 30-99 o IC ancho (>1.5 yardas para Regret, >0.20 para tasas) → amarillo; n≥100 e IC angosto → verde; mismo resultado en dos ejecuciones.
    - _Requisitos: 8.1, 8.2, 8.3, 8.4_
  - [ ] 2.6 [BACKEND] Prueba de propiedad del semáforo
    - **Property 1: Propiedad 1**
    - **Validates: Requirements 8.2, 8.3, 8.4**
    - Criterio de aceptación: `test_semaforo.py` recorre n de 0 a 500 y verifica que n<30 implica rojo y no concluyente, y las reglas amarillo/verde.
    - _Requisitos: 8.2, 8.3, 8.4, 9.7_
  - [ ] 2.7 [BACKEND] Prueba del bootstrap IC95 %
    - Criterio de aceptación: `test_bootstrap.py`: `lo ≤ valor ≤ hi`, determinismo con la semilla fija, el IC se estrecha al subir n, y un conjunto constante da IC de ancho 0.
    - _Requisitos: 8.1, 9.7_
  - [ ] 2.8 [BACKEND] Completar la prueba de inferencia del receptor con casos de `plays.csv` reales (muestra de 20 jugadas)
    - Criterio de aceptación: `test_receptor_real.py` verifica que el % inferido está entre 0 y 100 y que ningún elegido queda fuera de los candidatos `Pass Route`.
    - _Requisitos: 9.7_
  - [ ] 2.9 [BACKEND] Prueba de propiedad del Regret
    - **Property 3: Propiedad 3**
    - **Validates: Requirements 3.2**
    - Criterio de aceptación: `test_regret.py` con datos aleatorios generados: `regret ≥ 0` y `regret = max(separaciones) − separación del elegido`.
    - _Requisitos: 3.2, 9.7_
  - [ ] 2.10 [BACKEND] `backend/tabla.py`: construir al arrancar (lifespan en `main.py`) la tabla en memoria de pases, una fila por pase, con regret, zona, lado, éxito, separaciones, `inferido` y el orden `n` por partido
    - Criterio de aceptación: la tabla se calcula una sola vez al arrancar, sin escribir a disco; `n` por partido es contiguo desde 1; el arranque termina sin error.
    - Prueba: `test_tabla.py` (tabla pequeña sintética: columnas y orden).
    - _Requisitos: 9.6, 3.2_

- [ ] 3. Pantallas: Inicio, Sala de Decisiones y Tablero de Arrepentimiento
  - [ ] 3.1 [BACKEND] `rutas/resumen.py` y `rutas/regret.py`: `GET /api/resumen` y `GET /api/regret/equipos?zona=` (orden descendente por `estimacion.valor`)
    - Criterio de aceptación: formas idénticas al contrato; `titulo` sale de reglas sobre agregados; `zona` inválida → 400 `PARAMETRO_INVALIDO`.
    - Prueba: `test_resumen_equipos.py` (orden descendente y 400).
    - _Requisitos: 1.1, 1.2, 4.1, 4.2, 9.1_
  - [ ] 3.2 [BACKEND] `rutas/decision.py`: `GET /api/recomendacion` y `GET /api/evidencia`, con Pydantic (`down` 1-4, `yardsToGo` 1-30)
    - Criterio de aceptación: `comparables: []` cuando no hay jugadas; parámetros fuera de rango → 422 `VALIDACION`; n<30 en `estimacion` se refleja en rojo.
    - Prueba: `test_recomendacion_evidencia.py` (rangos, vacío, n<30).
    - _Requisitos: 2.2, 2.4, 2.5, 2.6, 9.1_
  - [x] 3.3 [FRONTEND] Mocks de las pantallas, en `mocks/` (ver sección "Mocks para el frontend"): `resumen`, `recomendacion`, `regret_equipos`, `evidencia`, `explicacion`, con interruptor por endpoint
    - Criterio de aceptación: cada archivo cumple la forma de `design.md` y cubre sus casos; `MOCK_ENDPOINTS` permite apagar cada endpoint por separado.
    - Prueba: `npm run build`; verificación manual: cambiar un endpoint a falso no afecta a los demás.
    - _Requisitos: 9.4, 9.5_
  - [x] 3.4 [FRONTEND] Componentes base: `Semaforo` (ícono + texto "Confiable / Con reservas / No concluyente"), `EstimacionBadge` (valor, IC95 %, n y "aún no es concluyente" si n<30), `TarjetaResumen`, `Cargando` (`aria-busy`), `Vacio`, `ErrorEstado` (con Reintentar)
    - Criterio de aceptación: cada confianza se ve con ícono y texto, no solo color; n<30 muestra "aún no es concluyente".
    - Prueba: `npm run build`; verificación manual con los 3 casos de semáforo del mock de `recomendacion`.
    - _Requisitos: 8.1, 8.2, 8.5, 1.2, 10.3, 10.7_
  - [x] 3.5 [FRONTEND] `state.tsx` (contexto en memoria: idioma, banda lateral, partido, n actual, panel IA; sin `localStorage`) y navegación de 3 pestañas en `App.tsx` (Inicio, Sala de Decisiones, Tablero de Arrepentimiento)
    - Criterio de aceptación: máximo 3 pestañas; pestañas inferiores en 375 px; el estado se pierde al recargar (esperado).
    - Prueba: `npm run build`; verificación manual a 375 px.
    - _Requisitos: 6.3, 7.3, 10.2_
  - [x] 3.6 [FRONTEND] Pantalla Inicio (`screens/Inicio.tsx`): `titulo` como título de pantalla, `TarjetaResumen` con `regret_liga` y "2021 sem. 1-8", `pct_objetivo_inferido`, estados Cargando/Error/Reintentar mostrando `detail`
    - Criterio de aceptación: título = conclusión del endpoint; el error muestra `detail` y reintenta.
    - Prueba: `npm run build`; manual con el caso de error `{detail,codigo}` del mock.
    - _Requisitos: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [x] 3.7 [FRONTEND] Sala de Decisiones (`screens/SalaDecisiones.tsx`): controles down 1-4, yardsToGo 1-20, zona, cobertura; `accion` como título, `porque`, Semáforo y EstimacionBadge; llamadas a `api/recomendacion` al cambiar un control
    - Criterio de aceptación: n<30 muestra "aún no es concluyente" y Semáforo rojo; `comparables: []` muestra "Sin jugadas con esos filtros"; los controles bloquean valores fuera de rango.
    - Prueba: `npm run build`; manual con n=12, 60, 240 y el caso vacío.
    - _Requisitos: 2.1, 2.2, 2.3, 2.5, 2.6_
  - [ ] 3.8 [FRONTEND] Sala de Decisiones: gráficas Recharts de evidencia (éxito por zona, por separación, por cobertura), lista de `comparables` con n y texto de `explicacion` con la etiqueta "respuesta automática" si `fuente = plantilla`
    - Criterio de aceptación: cada gráfica tiene Cargando/Vacío/Error y n e IC95 % visibles; la etiqueta aparece solo con `plantilla`.
    - Prueba: `npm run build`; manual a 375 px sin desplazamiento horizontal.
    - _Requisitos: 2.4, 2.7, 8.1, 10.7_
  - [x] 3.9 [FRONTEND] Tablero de Arrepentimiento (`screens/TableroRegret.tsx`): ranking descendente, filtro de zona (`todas`, `propia`, `medio`, `roja`), filas con equipo, valor, IC95 %, n y Semáforo, marca de no concluyente, título = equipo con mayor Regret concluyente
    - Criterio de aceptación: el filtro llama a `api/regret/equipos?zona=`; las filas con n<30 muestran "aún no es concluyente" y no pueden ser el título.
    - Prueba: `npm run build`; manual con los 8 equipos del mock.
    - _Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 4. Regret Index + modo partido en vivo + alertas
  - [ ] 4.1 [BACKEND] `rutas/jugada.py`: `GET /api/partido/{gameId}/jugada/{n}` (n desde 1) con la forma `Jugada`
    - Criterio de aceptación: 404 `NO_ENCONTRADO` si el partido o `n` no existen; la respuesta no contiene datos de jugadas con índice mayor a `n`; `marcador` es el de antes de la jugada.
    - Prueba: `test_jugada.py` (404 y forma).
    - _Requisitos: 3.2, 3.4, 9.2_
  - [ ] 4.2 [BACKEND] `backend/acumulado.py` y `rutas/acumulado.py`: `GET /api/partido/{gameId}/acumulado?hasta=n` con `regret_total`, `regret_medio`, `por_zona`, `por_lado` y `serie`
    - Criterio de aceptación: usa solo jugadas 1..n; `hasta=0` devuelve acumulado vacío válido; `hasta` negativo → 400.
    - Prueba: ver 4.5.
    - _Requisitos: 3.4, 3.5_
  - [ ] 4.3 [BACKEND] `rutas/alertas.py`: `GET /api/partido/{gameId}/alertas?hasta=n` con reglas sin IA (Regret medio reciente en rojo, lado con más Regret, cambio entre mitades solo con n≥30)
    - Criterio de aceptación: cada alerta trae `id`, `nivel`, `titulo`, `texto` (ES/EN) y `estimacion`; no se generan alertas de cambio entre mitades con n<30; solo usa jugadas ≤ n.
    - Prueba: `test_alertas.py` (n<30 sin alerta de mitades).
    - _Requisitos: 5.2, 5.7, 3.4_
  - [ ] 4.4 [BACKEND] Prueba de propiedad: no filtración del futuro
    - **Property 2: Propiedad 2**
    - **Validates: Requirements 3.4**
    - Criterio de aceptación: `test_no_futuro.py` modifica las jugadas con índice > n y comprueba que `acumulado`, `alertas` y `jugada/{n}` no cambian.
    - _Requisitos: 3.4, 9.7_
  - [ ] 4.5 [BACKEND] Prueba de propiedad: acumulado = suma de regrets
    - **Property 4: Propiedad 4**
    - **Validates: Requirements 3.5**
    - Criterio de aceptación: `test_acumulado.py` verifica que `regret_total` a `hasta=n` es la suma de los `regret` de 1..n para varios n y que `serie` es monótona no decreciente.
    - _Requisitos: 3.5, 9.7_
  - [ ] 4.6 [FRONTEND] Mocks del modo en vivo: `partidos`, `jugada` (12 jugadas de un partido), `acumulado` por `hasta` y `alertas`
    - Criterio de aceptación: formas exactas del contrato; ningún mock de `hasta=n` incluye datos de jugadas posteriores.
    - Prueba: `npm run build`.
    - _Requisitos: 9.4, 3.4_
  - [ ] 4.7 [FRONTEND] Sección "Partido en vivo" en la Sala de Decisiones (`screens/EnVivo.tsx`): selector desde `api/partidos` y botón "Siguiente jugada" (`api/partido/{gameId}/jugada/{n+1}`) con down, distancia, marcador, reloj, zona, receptor elegido, más abierto y Regret
    - Criterio de aceptación: n sube de 1 en 1; llamadas con rutas relativas sin diagonal inicial.
    - Prueba: `npm run build`; manual a 375 px.
    - _Requisitos: 3.1, 3.2_
  - [ ] 4.8 [FRONTEND] Avance automático cada 3 s con `setInterval`, pausa, limpieza al desmontar y mensaje "Fin del partido" en la última jugada
    - Criterio de aceptación: avanza cada 3 s hasta pausar o llegar al final; en la última jugada se detiene y muestra "Fin del partido"; sin temporizadores huérfanos al cambiar de pestaña.
    - Prueba: `npm run build`; manual con el partido mock de 12 jugadas.
    - _Requisitos: 3.3, 3.6_
  - [ ] 4.9 [FRONTEND] Regret acumulado (`api/partido/{gameId}/acumulado?hasta=n`) por zona y por lado con n e IC95 %
    - Criterio de aceptación: se actualiza al cambiar n; muestra Vacío con `hasta=0`; Semáforo y "aún no es concluyente" según `estimacion`.
    - Prueba: `npm run build`; manual con los pasos 1, 5 y 12.
    - _Requisitos: 3.5, 8.1, 10.7_

- [ ] 5. Pulido: móvil 375 px, ES/EN, Modo Banda Lateral, accesibilidad
  - [ ] 5.1 [FRONTEND] `i18n.ts` (diccionario ES/EN, helper `t()`, respaldo ES si falta clave) y botón único ES/EN; textos del backend por campo `es`/`en`
    - Criterio de aceptación: inicia en ES; un botón alterna a EN en todas las pantallas; clave faltante se muestra en ES; el idioma no se guarda fuera de memoria.
    - Prueba: `npm run build`; manual alternando idioma en las 3 pestañas.
    - _Requisitos: 7.1, 7.2, 7.3, 7.4_
  - [ ] 5.2 [FRONTEND] Revisión responsive a 375 px de las 3 pantallas, gráficas y tablas
    - Criterio de aceptación: sin desplazamiento horizontal a 375 px; escritorio ≥1024 px reserva columna para el panel IA.
    - Prueba: `npm run build`; manual en DevTools a 375 px.
    - _Requisitos: 10.1_
  - [ ] 5.3 [FRONTEND] Toggle Modo Banda Lateral visible en todas las pantallas con `aria-pressed`
    - Criterio de aceptación: una columna, texto grande, alto contraste, solo recomendación, Semáforo y alertas; el estado se conserva al cambiar de pestaña (memoria).
    - Prueba: `npm run build`; manual en 375 px.
    - _Requisitos: 6.1, 6.2, 6.3_
  - [ ] 5.4 [FRONTEND] Accesibilidad: contraste ≥4.5:1, foco visible, `aria-label` en botones de solo ícono, `aria-busy` en cargando, uso por teclado, sin depender solo del color
    - Criterio de aceptación: se puede operar todo con teclado; el Semáforo siempre lleva ícono y texto.
    - Prueba: `npm run build`; manual con Tab/Enter y revisión de contraste.
    - _Requisitos: 8.5, 10.3_
  - [ ] 5.5 [FRONTEND] Prueba de propiedad: rutas del frontend
    - **Property 5: Propiedad 5**
    - **Validates: Requirements 9.3, 10.4**
    - Criterio de aceptación: búsqueda en `dashboard/src` sin `'/api`, `"/api`, `localhost`, `127.0.0.1` ni `http`; sin CDN ni fuentes externas; `package.json` sin dependencias nuevas; `vite.config.ts` con `base: './'` y proxy solo en dev.
    - Prueba: `grep` documentado + `npm run build`.
    - _Requisitos: 9.3, 9.5, 10.4, 10.5_
  - [ ] 5.6 [FRONTEND] Prueba de propiedad: estados de las respuestas
    - **Property 6: Propiedad 6**
    - **Validates: Requirements 10.7**
    - Criterio de aceptación: cada tabla y gráfica se renderiza en Cargando, Vacío y Error sin excepciones (usar los mocks de vacío y de error); `npm run build` pasa y `dashboard/dist` se genera.
    - _Requisitos: 10.6, 10.7_

- [ ] 6. Panel IA (alertas, 4 preguntas, chat) al final
  - [ ] 6.1 [BACKEND] `backend/ia.py` y `rutas/ia.py`: `GET /api/explicacion` y `POST /api/chat` con Strands + Bedrock Nova (`BEDROCK_MODEL_ID`, región con `AWS_REGION`, `boto3.client("bedrock-runtime", region_name=region)`) y plantilla de respaldo
    - Criterio de aceptación: si Bedrock falla o no hay credenciales se responde `fuente: "plantilla"` con 200, nunca error; `mensaje` de 1-500 caracteres validado; `chat` usa solo jugadas ≤ `hasta`; sin llaves en código ni logs.
    - Prueba: ver 6.2.
    - _Requisitos: 2.7, 5.4, 5.5, 5.7, 3.4_
  - [ ] 6.2 [BACKEND]* Pruebas del fallback de IA
    - Criterio de aceptación: `test_ia_fallback.py` simula falla del modelo y verifica `fuente="plantilla"`, 422 con mensaje vacío o de más de 500 caracteres.
    - _Requisitos: 5.5, 5.7, 9.7_
  - [ ] 6.3 [FRONTEND] Mocks de IA: `chat` (`ia` y `plantilla`) y alertas con 3 niveles (`info`, `atencion`, `critica`)
    - Criterio de aceptación: formas exactas; incluyen `fuente: "plantilla"` y un caso de error `{detail,codigo}`.
    - Prueba: `npm run build`.
    - _Requisitos: 9.4, 5.5_
  - [ ] 6.4 [FRONTEND] `panel/PanelIA.tsx`: drawer en móvil (`role="dialog"`, cierre con Esc, botón flotante con `aria-label`) y columna en escritorio ≥1024 px, visible en las 3 pestañas, con estado de error aislado
    - Criterio de aceptación: si el panel falla, el resto de la app sigue funcionando; el drawer no produce desplazamiento horizontal a 375 px.
    - Prueba: `npm run build`; manual a 375 px y a 1024 px.
    - _Requisitos: 5.1, 5.6, 10.1_
  - [ ] 6.5 [FRONTEND] Alertas en el panel (`api/partido/{gameId}/alertas?hasta=n`) con badge de nuevas, recargadas al cambiar `hasta`
    - Criterio de aceptación: el badge muestra el número de alertas nuevas y se limpia al abrir el panel; en Modo Banda Lateral las alertas siguen visibles.
    - Prueba: `npm run build`; manual avanzando jugadas en el modo en vivo.
    - _Requisitos: 5.2, 6.1_
  - [ ] 6.6 [FRONTEND] Las 4 preguntas sugeridas ("¿A quién tiro en 3ª y 5?", "¿Por qué lado me cubren?", "¿Qué cambió desde el medio tiempo?", "Resumen para el vestidor" con traducción EN) y chat libre con `POST api/chat` `{gameId, hasta, mensaje}`
    - Criterio de aceptación: muestra `respuesta`; con `fuente = plantilla` muestra "respuesta automática"; limita el mensaje a 500 caracteres; re-ejecutar la auditoría de la tarea 5.5 sobre `panel/` sin resultados.
    - Prueba: `npm run build`; manual con respuestas `ia`, `plantilla` y error.
    - _Requisitos: 5.3, 5.4, 5.5, 5.6_

- [ ] 7. Integración y README
  - [ ] 7.1 [FRONTEND + BACKEND] Apagar mocks endpoint por endpoint cuando Christian avise (poner cada entrada de `MOCK_ENDPOINTS` en falso) y corregir desvíos del contrato
    - Criterio de aceptación: cada endpoint probado con datos reales; los desvíos se corrigen en el cliente o en el backend según el contrato de `design.md`; con la IA apagada (sin credenciales) la app sigue mostrando el hallazgo.
    - Prueba: `npm run build`; `pytest` completo; prueba manual de punta a punta en `http://localhost:8000/` y bajo subruta.
    - _Requisitos: 9.4, 9.5, 5.6, 10.6_
  - [x] 7.2 [FRONTEND + BACKEND] `README.md` en la raíz: cómo correr dev (Vite + Uvicorn) y build, variables `.env` (sin llaves), supuestos y limitaciones (proxy de separación, receptor inferido, sin EPA, 2021 sem. 1-8)
    - Criterio de aceptación: un tercero puede levantar la app siguiendo el README; no contiene credenciales; las limitaciones coinciden con `requirements.md`.
    - _Requisitos: 9.1, 10.5_

- [ ] 8. Punto de control final
  - Ensure all tests pass, ask the user if questions arise.

## Mocks para el frontend

Ubicación: `dashboard/src/mocks/` (un archivo por endpoint, reexportado desde `mocks/index.ts`). Interruptor: `MOCK_ENDPOINTS` en `api.ts` (un booleano por endpoint) con `VITE_USE_MOCKS` (por defecto `true`) como valor inicial. Cuando Christian avise que un endpoint está listo, se pone solo ese endpoint en `false`. Todos los mocks usan las formas exactas de `design.md`; los casos de error devuelven `{detail, codigo}`.

| Endpoint | Archivo mock | Forma (`design.md`) | Casos que debe cubrir |
|---|---|---|---|
| `GET api/resumen` | `mocks/resumen.ts` | `{titulo, linea, regret_liga: Estimacion, calidad_datos}` | verde (n≥100); amarillo; error `{detail,codigo}` |
| `GET api/partidos` | `mocks/partidos.ts` | `[{gameId, semana, local, visitante, n_pases}]` | 3 partidos; lista vacía |
| `GET api/partido/{gameId}/jugada/{n}` | `mocks/jugada.ts` | `Jugada` | 12 jugadas de un partido; `n` inexistente → 404 `NO_ENCONTRADO`; `inferido=true` y `false`; `pase` `C`, `I` e `IN` |
| `GET api/partido/{gameId}/acumulado?hasta=n` | `mocks/acumulado.ts` | `Acumulado` | `hasta=0` vacío; n<30 rojo "no concluyente"; solo datos ≤ n |
| `GET api/partido/{gameId}/alertas?hasta=n` | `mocks/alertas.ts` | `[{id, nivel, titulo: Textos, texto: Textos, estimacion}]` | 3 alertas (`info`, `atencion`, `critica`); lista vacía |
| `GET api/recomendacion` | `mocks/recomendacion.ts` | `{accion, porque, estimacion, comparables}` | n=12 rojo (no concluyente); n=60 amarillo; n=240 verde; `comparables: []` (vacío); error |
| `GET api/regret/equipos` | `mocks/regret_equipos.ts` | `[{equipo, estimacion}]` ordenado descendente | 8 equipos con mezcla de semáforos; al menos uno con n<30; filtro por `zona` |
| `GET api/evidencia` | `mocks/evidencia.ts` | `Evidencia` | las 3 series con estimaciones; serie vacía |
| `GET api/explicacion` | `mocks/explicacion.ts` | `{texto: Textos, fuente}` | `fuente: "ia"` y `fuente: "plantilla"` |
| `POST api/chat` | `mocks/chat.ts` | `{respuesta, fuente}` | `ia`; `plantilla`; error 422 `VALIDACION` |

## Notes

- Las tareas con `*` son opcionales. Las pruebas de las propiedades 1-6 y las de inferencia del receptor no son opcionales.
- Paralelo: la columna BACKEND (Christian) corre en `backend/` contra el contrato; la columna FRONTEND (Marianne) en `dashboard/` con mocks. El grafo de abajo separa ambas.
- Tareas que escriben el mismo archivo (`main.py`, `SalaDecisiones.tsx`, `mocks/index.ts`) van en oleadas distintas. Los routers nuevos en `backend/rutas/*.py` se incluyen solos desde `main.py`, para que no choquen.
- La propiedad 5 se revalida tras el panel IA (6.6) y en integración (7.1).
- **Orden si falta tiempo:** 1 (esqueleto), 2.1-2.5 y 2.6, 3.1-3.2 con 3.3-3.7 y 3.9, luego 4.1-4.2 con 4.7-4.9, 5.3 y 5.2, 6.4-6.6 y 7.1; dejar para el final 2.7-2.8, 6.1-6.2 con respaldo en plantilla y 7.2.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "2.1", "2.5"] },
    { "id": 2, "tasks": ["1.5", "2.2", "2.3", "2.6", "2.7", "3.3", "3.4"] },
    { "id": 3, "tasks": ["2.4", "2.8", "3.5"] },
    { "id": 4, "tasks": ["2.9", "2.10", "3.6", "3.7", "3.9"] },
    { "id": 5, "tasks": ["3.1", "3.2", "3.8"] },
    { "id": 6, "tasks": ["4.1", "4.2", "4.6"] },
    { "id": 7, "tasks": ["4.3", "4.5", "4.7"] },
    { "id": 8, "tasks": ["4.4", "6.1", "4.8"] },
    { "id": 9, "tasks": ["6.2", "4.9"] },
    { "id": 10, "tasks": ["5.1", "6.3"] },
    { "id": 11, "tasks": ["5.2"] },
    { "id": 12, "tasks": ["5.3"] },
    { "id": 13, "tasks": ["5.4"] },
    { "id": 14, "tasks": ["5.5"] },
    { "id": 15, "tasks": ["5.6"] },
    { "id": 16, "tasks": ["6.4"] },
    { "id": 17, "tasks": ["6.5"] },
    { "id": 18, "tasks": ["6.6"] },
    { "id": 19, "tasks": ["7.1"] },
    { "id": 20, "tasks": ["7.2"] }
  ]
}
```
