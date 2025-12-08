# 🎬 Media Sorter

## 📋 Descripción

Sistema automático de organización de medios que vigila un directorio, clasifica archivos de video usando TMDB, y crea hard links organizados. Incluye gestión automática de enlaces.

## 🐳 Docker (desarrollo)

Este repositorio incluye un archivo de desarrollo `docker-compose.dev.yml` que define el servicio `media-sorter` (imagen `media-sorter:dev`) y monta los directorios de ejemplo `./dev-media` y `./dev-config` dentro del contenedor.

### Variables de entorno (definidas en `docker-compose.dev.yml`)

- `TMDB_API_KEY` — API key de TMDB (v3).
- `WATCH_DIR` — ruta en el contenedor al directorio que se debe vigilar (p. ej. `/media/watch`).
- `SERIES_DIR` — ruta en el contenedor donde crear/hardlink las series (p. ej. `/media/series`).
- `MOVIES_DIR` — ruta en el contenedor donde crear/hardlink las películas (p. ej. `/media/movies`).
- `CONFIG_DIR` — ruta en el contenedor para archivos de configuración (p. ej. `/config`).
- `WATCHER_POLLING` — `0` o `1`. Si `1` fuerza usar `PollingObserver` en vez de observador nativo (útil para montajes en red/FUSE).

### Ejemplo de archivo `.env` (colocar en la raíz del repo)

```
TMDB_API_KEY=<tmdb_api_key_v3>
WATCH_DIR=/media/watch
SERIES_DIR=/media/series
MOVIES_DIR=/media/movies
CONFIG_DIR=/config
WATCHER_POLLING=0
```

Ajusta las rutas si vas a montar volúmenes diferentes; las rutas arriba son las que usa la configuración por defecto del `docker-compose.dev.yml` (montajes locales `./dev-media` y `./dev-config`).

### Levantar con Docker Compose (recomendado para desarrollo)

Construir y arrancar el servicio en segundo plano:

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

Ver logs:

```bash
docker compose -f docker-compose.dev.yml logs -f
```

Detener y eliminar contenedores de desarrollo:

```bash
docker compose -f docker-compose.dev.yml down
```

### Construcción de la imagen y ejecución `docker build` / `docker run`

```bash
docker build -t media-sorter .
docker run -d \
  --env-file .env \
  -v /mnt/media:/media:rw \
  -v /mnt/config:/config:rw \
  --name media-sorter \
  media-sorter
```

Ejemplo (PowerShell / Windows):

```powershell
docker build -t media-sorter . ;
docker run -d `
  --env-file .env `
  -v ${PWD}\media:/media:rw `
  -v ${PWD}\config:/config:rw `
  --name media-sorter `
  media-sorter
```

### Notas y recomendaciones

- Asegúrate de que los volúmenes locales están disponibles y compartidos con Docker (particularmente en Windows / Docker Desktop).
- Si usas un NAS o un montaje en red para `WATCH_DIR`, considera activar `WATCHER_POLLING=1` para evitar problemas con la monitorización basada en eventos.
- `TMDB_API_KEY` es obligatoria para que la clasificación funcione; sin ella el proyecto no podrá consultar TMDB.
