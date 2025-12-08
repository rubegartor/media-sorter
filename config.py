import os
import logging
import sys
from pathlib import Path

# Configurar logger raíz de forma sencilla si no hay handlers
_root_logger = logging.getLogger()
if not _root_logger.handlers:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format='%(levelname)s: %(message)s')

# Extensiones de video soportadas
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.iso', '.webm', '.ts', '.m2ts', '.wmv')

# Variables de entorno obligatorias
REQUIRED_ENV_VARS = [
    "TMDB_API_KEY",
    "WATCH_DIR",
    "SERIES_DIR",
    "MOVIES_DIR",
    "CONFIG_DIR",
]

# Helper: leer variable de entorno y tratar cadenas vacías como no definidas
def _get_env(var_name: str):
    val = os.environ.get(var_name)
    if val is None:
        return None
    val = val.strip()
    return val if val else None

# Construir dict de configuración y detectar ausentes
CONFIG = {}
missing = []
for v in REQUIRED_ENV_VARS:
    val = _get_env(v)
    if val is None:
        missing.append(v)
    else:
        CONFIG[v] = val

if missing:
    logging.error("❌ Variables de entorno obligatorias no definidas: %s", ", ".join(missing))
    sys.exit(1)

# Extraer variables (guardadas como cadenas para compatibilidad)
WATCH_DIR = CONFIG["WATCH_DIR"]
SERIES_DIR = CONFIG["SERIES_DIR"]
MOVIES_DIR = CONFIG["MOVIES_DIR"]
CONFIG_DIR = CONFIG["CONFIG_DIR"]
TMDB_API_KEY = CONFIG['TMDB_API_KEY']

# Construir ruta Path para el archivo de hardlinks usando el objeto Path de pathlib
HARDLINKS_DB_PATH = Path(CONFIG_DIR) / 'hardlinks_map.json'

# Validar TMDB API key (no vacía)
if not isinstance(TMDB_API_KEY, str) or not TMDB_API_KEY.strip():
    logging.error("❌ TMDB_API_KEY inválida o vacía.")
    sys.exit(1)

# Comprobar existencia de las rutas de directorio requeridas
for _var_name, _path_str in (('WATCH_DIR', WATCH_DIR), ('SERIES_DIR', SERIES_DIR), ('MOVIES_DIR', MOVIES_DIR)):
    _p = Path(_path_str)
    if not _p.exists() or not _p.is_dir():
        logging.error("❌ %s no existe o no es un directorio: %s", _var_name, _path_str)
        sys.exit(1)

# Comprobar existencia del archivo de hardlinks
_hardlinks_path = HARDLINKS_DB_PATH
if not _hardlinks_path.exists() or not _hardlinks_path.is_file():
    logging.error("❌ Archivo de hardlinks no encontrado o no es un archivo regular: %s", _hardlinks_path)
    sys.exit(1)

logging.info("ℹ️ Config rutas: WATCH_DIR=%s, SERIES_DIR=%s, MOVIES_DIR=%s, CONFIG_DIR=%s",
             WATCH_DIR, SERIES_DIR, MOVIES_DIR, CONFIG_DIR)

logging.info("✅ Configuración de entorno validada correctamente.")
