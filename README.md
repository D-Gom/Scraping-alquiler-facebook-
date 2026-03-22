# Buscador Inteligente de Alquileres en Neuquén

Bot automatizado que monitorea grupos de Facebook en busca de publicaciones de alquileres en Neuquén Capital, utiliza la API de Google Gemini para evaluarlas con inteligencia artificial y envía alertas en tiempo real vía Telegram.

---

## Características

- **Scraping de Facebook** con Playwright y perfil de navegador persistente (evita re-login).
- **Filtrado rápido** por palabras clave positivas/negativas antes de consultar la IA.
- **Análisis multimodal con Gemini** (texto + imágenes) para evaluar si el inmueble cumple tus criterios.
- **Base de datos SQLite** para evitar procesar el mismo post dos veces.
- **Alertas por Telegram** con texto, imágenes y enlace al post original.
- **Automatización** mediante el módulo `schedule` (o `cron`).

---

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

---

## Configuración

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales y preferencias:

| Variable | Descripción |
|---|---|
| `FACEBOOK_GROUP_URLS` | URLs de los grupos a monitorear (separadas por coma) |
| `MAX_POSTS_PER_GROUP` | Posts a extraer por grupo por ciclo (default: 20) |
| `GEMINI_API_KEY` | API Key de Google AI Studio |
| `GEMINI_MODEL` | Modelo de Gemini (default: `gemini-1.5-flash`) |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram (obtenido con @BotFather) |
| `TELEGRAM_CHAT_ID` | Chat ID del usuario/canal que recibe las alertas |
| `MAX_PRECIO` | Precio máximo de alquiler en ARS (0 = sin límite) |
| `ACEPTA_MASCOTAS` | `true` / `false` |
| `MIN_DORMITORIOS` | Número mínimo de dormitorios |
| `BARRIOS_PREFERIDOS` | Barrios aceptados en Neuquén (separados por coma) |
| `INTERVALO_MINUTOS` | Frecuencia de ejecución en minutos (default: 60) |
| `DB_PATH` | Ruta a la base de datos SQLite (default: `alquileres.db`) |

---

## Uso

### Ejecución única

```bash
python main.py
```

### Ejecución automática en bucle (cada `INTERVALO_MINUTOS` minutos)

```bash
python main.py --schedule
```

### Con cron (Linux)

```cron
0 * * * * /ruta/al/venv/bin/python /ruta/al/proyecto/main.py
```

---

## Estructura del Proyecto

```
.
├── main.py              # Pipeline principal (orquestación)
├── scraper.py           # Scraping de grupos de Facebook (Playwright)
├── filter.py            # Filtrado por palabras clave
├── gemini_analyzer.py   # Análisis multimodal con Google Gemini
├── notifier.py          # Notificaciones vía Telegram Bot API
├── database.py          # Gestión de la base de datos SQLite
├── config.py            # Configuración desde variables de entorno
├── requirements.txt     # Dependencias Python
├── .env.example         # Plantilla de configuración
└── tests/               # Tests unitarios (pytest)
```

---

## Tests

```bash
python -m pytest tests/ -v
```

---

## Notas de Seguridad

- Usa una cuenta secundaria de Facebook para el scraping; Meta puede bloquear cuentas automatizadas.
- Nunca subas tu archivo `.env` al repositorio (ya está en `.gitignore`).
- El perfil del navegador (`fb_profile/`) contiene cookies de sesión; trátalo como dato sensible.
