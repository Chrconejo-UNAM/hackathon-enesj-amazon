# La Jugada Correcta

**Una línea:** Le dice a un coach de la NFL qué decisión conviene tomar y por qué, comparando al receptor elegido contra el más abierto en el momento del pase, con n e IC 95 % en cada cifra.

> NFL Big Data Bowl · UNAM 2026 · Equipo ENES Juriquilla

![Captura del dashboard](docs/dashboard.png)

<!-- TODO antes de entregar: sube una captura real a docs/dashboard.png. -->

## 1. Qué es

App web para un coach NFL. Pregunta analítica: **¿qué decisión conviene tomar y por qué?** En concreto, al momento del pase (`pass_forward`): ¿el QB eligió al receptor más abierto, y en qué zona del campo se maximiza el éxito? No es un tablero de estadísticas: entrega una recomendación con su porqué, su muestra y su incertidumbre.

## 2. Qué responde (hallazgo)

- **Target Regret Index (Regret):** separación del receptor más abierto − separación del receptor elegido, en yardas, en `pass_forward`. Siempre ≥ 0.
- **Semáforo** con ícono y texto: verde (Confiable), amarillo (Con reservas), rojo (No concluyente).
- Toda cifra va con **n** e **IC bootstrap 95 %**. Si **n < 30** el resultado es rojo y "aún no es concluyente".
- El titular del Inicio sale de reglas sobre los agregados, no de la IA. El hallazgo final con cifras se lee en la pantalla Inicio (`GET api/resumen`).

## 3. Pantallas

- **Inicio:** hallazgo como título y tarjeta resumen (Regret de la liga, línea base "2021 sem. 1-8", % de receptores inferidos).
- **Sala de Decisiones:** controles de down, yardsToGo, zona y cobertura → recomendación, porqué, semáforo, gráficas de evidencia y comparables.
- **Tablero de Arrepentimiento:** ranking de equipos por Regret, con filtro de zona.
- **Modo Banda Lateral:** una columna, texto grande, alto contraste; solo recomendación, semáforo y alertas.
- **ES/EN:** un botón; el idioma vive solo en memoria.

**Pendiente (roadmap, aún no implementado en el frontend):**

- **Partido en Vivo simulado:** reproducir un partido real jugada por jugada (manual o cada 3 s) con Regret acumulado por zona y lado, sin datos del futuro.
- **Panel IA:** alertas por reglas, 4 preguntas sugeridas y chat (Strands + Bedrock Nova, con plantilla de respaldo). Drawer en móvil, columna en escritorio; si falla, el resto de la app sigue.

## 4. Cómo correrlo

Backend (desde la raíz del proyecto, Uvicorn):

```
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Frontend en desarrollo (Vite hace proxy de `/api` → `http://localhost:8000` solo en dev):

```
cd dashboard
npm run dev
```

Build de producción: `npm run build` (en `dashboard/`) genera `dashboard/dist`, que FastAPI sirve junto con la API en la misma URL y puerto.

**Windows:** si `node`/`npm` no se reconocen, agrega Node al PATH de la sesión y usa `npm.cmd` (PowerShell bloquea `npm.ps1`):

```
$env:Path = "<repo>\.hackathon\.tools\node;" + $env:Path
npm.cmd run dev
```

Pruebas del backend:

```
.\.venv\Scripts\python.exe -m pytest tests
```

Verificar entorno: `.\.hackathon\setup.cmd --check`. Generar entrega: `.\.hackathon\setup.cmd --entregar`.

El dashboard llama a la API con rutas relativas sin diagonal inicial (`fetch('api/...')`), nunca `localhost` ni URLs absolutas.

## 5. Mocks del frontend

Hasta que cada endpoint exista, `dashboard/src/api.ts` responde con mocks de forma idéntica al contrato.

- `VITE_USE_MOCKS=false` (en un `.env` dentro de `dashboard/`, no versionado) apaga todos los mocks. Por defecto es `true`.
- `MOCK_ENDPOINTS` en `dashboard/src/api.ts` activa o apaga el mock **por endpoint**: poner un endpoint en `false` lo pasa a la API real.
- Escenarios por URL: `?mock=error`, `?mock=amarillo`, `?mock=vacio` para ver los estados de error, semáforo amarillo y vacío.

## 6. Variables de entorno (`.env` en la raíz, no versionado)

Copia `.env.example` como `.env`. Nombres (sin valores):

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`: solo en local, llaves temporales del workshop. En AWS las credenciales vienen del rol.
- `AWS_REGION`: región de Bedrock (por defecto `us-east-1`).
- `BEDROCK_MODEL_ID`: lo define el hosting; por defecto `us.amazon.nova-pro-v1:0`.

Nunca escribas llaves en el código ni en este README. La app funciona sin IA.

## 7. Contrato de API

| Método y ruta | Respuesta |
|---|---|
| `GET /health` | `{"status":"ok"}` |
| `GET /api/resumen` | titular, línea, `regret_liga`, `calidad_datos` |
| `GET /api/partidos` | lista de partidos |
| `GET /api/partido/{gameId}/jugada/{n}` | `Jugada` (n desde 1) |
| `GET /api/partido/{gameId}/acumulado?hasta=n` | `Acumulado` |
| `GET /api/partido/{gameId}/alertas?hasta=n` | alertas por reglas |
| `GET /api/recomendacion?down=&yardsToGo=&zona=&cobertura=` | acción, porqué, estimación, comparables |
| `GET /api/regret/equipos?zona=` | ranking de equipos |
| `GET /api/evidencia?down=&yardsToGo=&zona=` | éxito por zona, separación y cobertura |
| `GET /api/explicacion?down=&yardsToGo=&zona=&cobertura=` | texto ES/EN, `fuente` `ia`\|`plantilla` |
| `POST /api/chat` `{gameId, hasta, mensaje}` | `{respuesta, fuente}` |

Forma de `Estimacion`:

```ts
type Estimacion = {
  valor: number            // yardas (Regret) o proporción 0-1 (tasas)
  ic95: [number, number]
  n: number
  concluyente: boolean     // false si n < 30
  confianza: 'verde' | 'amarillo' | 'rojo'
}
```

Textos bilingües: `{es, en}`. Errores: `{detail, codigo}` con HTTP 400/404/422/500. Con `hasta=n` ningún endpoint usa jugadas posteriores a n. Detalle completo en `.kiro/specs/la-jugada-correcta/design.md`.

## 8. Supuestos

- **Zona:** `propia` (más de 50 yardas de la end zone rival), `medio` (21 a 50), `roja` (20 o menos).
- **Éxito:** pase completo con ganancia de al menos 40 % de yardsToGo en 1ª, 60 % en 2ª y 100 % en 3ª y 4ª (no hay EPA).
- **Semáforo:** n < 30 rojo; 30-99 o IC ancho (> 1.5 yd en Regret, > 0.20 en tasas) amarillo; n ≥ 100 e IC angosto verde.
- **Bootstrap:** percentil, 1000 remuestreos, semilla fija.
- **Exclusiones:** sacks (`S`) y scrambles (`R`); filas sin `down` o con cobertura `NA` salen del filtro afectado.
- Coordenadas normalizadas a ataque hacia la derecha; solo frames `pass_forward` y `pass_arrived` (igualdad exacta).

## 9. Limitaciones

- **Proxy de separación:** "más abierto" es la mayor separación al defensor más cercano en `pass_forward`; no considera ruta, ángulo, cobertura ni capacidad de ganar el balón. El Regret no prueba que ese receptor habría completado el pase.
- **Receptor inferido:** el dataset no trae receptor objetivo. Se infiere de `playDescription` contra `players.displayName`, con respaldo al jugador ofensivo más cercano al balón en `pass_arrived`. Se reporta el % inferido y puede haber errores.
- **Alcance:** solo 2021, semanas 1-8 (122 partidos). Las muestras por equipo, zona y cobertura son pequeñas; por eso se reportan n e IC 95 %.
- **Sin EPA:** el éxito se define por yardas ganadas contra yardsToGo.
- El modo en vivo es una simulación sobre datos históricos.

## Datos

Solo lectura, en `data/` (no se versionan en git; el `.zip` de entrega sí los incluye). Fuente: `nfl-big-data-bowl-regional-event-data`.

| Archivo | Llaves | Uso |
|---|---|---|
| `games.csv` | `gameId` | equipo local/visitante, semana, fecha |
| `plays.csv` | `gameId`, `playId` | contexto de la jugada: `down`, `yardsToGo`, `yardlineNumber`, `quarter`, `gameClock`, marcador, equipos, `passResult`, `playDescription`, `pff_passCoverage*` |
| `players.csv` | `nflId` | posición y nombre del jugador |
| `pffScoutingData.csv` | `gameId`, `playId`, `nflId` | rol (`pff_role`), alineación, presión |
| `tracking/tracking_[gameId].csv` | `gameId`, `playId`, `nflId` | posición por frame (`x`, `y`), `event`, `playDirection` |

Detalle completo de columnas: [`data/README-dataset.md`](data/README-dataset.md).

## Stack

Python 3.12.12 · FastAPI 0.115.14 · Uvicorn 0.34.3 · Pydantic 2.11.7 · pandas 2.2.3 · numpy 2.1.3 · pytest 8.3.5 · httpx 0.28.1 · Node 22.23.1 · React 18.3.1 · Vite 5.4.21 · TypeScript 5.7.3 · Tailwind CSS 3.4.19 · Recharts 3.10.1. IA opcional: Strands Agents 1.64.0 + boto3 1.44.0 con Amazon Bedrock (Nova). Sin Docker y sin dependencias extra.

### Backend (sección de Christian)

<!-- Christian: pega aquí la descripción del backend (cálculo de la tabla de pases, inferencia del receptor, bootstrap, IA y pruebas). -->

## 10. Equipo

- **Christian Alexis Ramírez Conejo** (ENES Juriquilla, UNAM): backend y datos (`backend/`).
- **Marianne**: frontend (`dashboard/`).
