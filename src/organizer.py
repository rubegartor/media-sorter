import os
import platform
import logging
import unicodedata
from typing import Optional
from src.config import SERIES_DIR, MOVIES_DIR, VIDEO_EXTENSIONS
from src.link_manager import LinkManager


_INVALID_CHARS = '<>:"/\\|?*'  # Caracteres no permitidos en Windows (más restrictivo)
_RESERVED_NAMES_WINDOWS = frozenset({
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
})
_IS_WINDOWS = platform.system().lower() == 'windows'

_link_manager: Optional['LinkManager'] = None


def set_link_manager(link_manager):
    """Establece el LinkManager global para registrar hard links."""
    global _link_manager
    _link_manager = link_manager


def _normalize_string(text):
    """Normaliza un string: convierte a NFD, elimina diacríticos."""
    if not isinstance(text, str):
        return text
    # NFD: descompone caracteres acentuados y elimina marcas diacríticas
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')


def _sanitize_name(name):
    """Sanea nombres para evitar caracteres inválidos.
    Elimina completamente los caracteres no válidos de forma consistente.
    Normaliza caracteres acentuados para evitar duplicados."""
    if not name or not isinstance(name, str):
        return 'Unknown'

    # Normalizar y eliminar caracteres no válidos en una sola pasada
    normalized = _normalize_string(name)
    sanitized = ''.join(
        char for char in normalized
        if char not in _INVALID_CHARS and 32 <= ord(char) < 127
    )

    # Eliminar espacios múltiples y normalizar
    sanitized = ' '.join(sanitized.split()).rstrip('. ')

    # Validar nombres reservados en Windows
    if _IS_WINDOWS and sanitized:
        name_upper = sanitized.split('.')[0].upper()
        if name_upper in _RESERVED_NAMES_WINDOWS:
            sanitized = f"_{sanitized}"

    return sanitized if sanitized else 'Unknown'


def _try_link(src, dst):
    """Intenta crear hardlink y lo registra en el LinkManager."""
    try:
        os.link(src, dst)
        if _link_manager:
            _link_manager.add_link(src, dst)
        return True
    except Exception as e:
        logging.error("❌ Error creando hardlink '%s' -> '%s': %s", src, dst, e)
        return False


def _ensure_dir(path):
    """Asegura que la ruta exista."""
    path_str = os.fspath(path)
    os.makedirs(path_str, exist_ok=True)
    return path_str


def _is_video_file(filename):
    """Verifica si el archivo es un video."""
    return filename.lower().endswith(VIDEO_EXTENSIONS)


def _process_single_file(src_path, dest_dir):
    """Procesa un archivo individual creando un hardlink sanitizado."""
    original_filename = os.path.basename(src_path)
    sanitized_filename = _sanitize_name(original_filename)
    dest_path = os.path.join(dest_dir, sanitized_filename)

    if os.path.exists(dest_path):
        if original_filename != sanitized_filename:
            logging.debug("📝 Archivo ya existe (sanitizado): '%s' -> '%s'",
                         original_filename, sanitized_filename)
        return

    if _try_link(src_path, dest_path):
        if original_filename != sanitized_filename:
            logging.info("📝 Archivo sanitizado y enlazado: '%s' -> '%s'",
                        original_filename, sanitized_filename)


def _process_video_files(src_path, dest_dir):
    """Procesa archivo(s) de video: individual o dentro de una carpeta."""
    if os.path.isfile(src_path):
        if _is_video_file(src_path):
            _process_single_file(src_path, dest_dir)
    elif os.path.isdir(src_path):
        # Procesar recursivamente todos los videos en la carpeta
        for root, _, files in os.walk(src_path):
            for filename in files:
                if _is_video_file(filename):
                    src_file = os.path.join(root, filename)
                    _process_single_file(src_file, dest_dir)


def organize_items(classified_items):
    """Organiza los items clasificados en las carpetas destino."""
    for item_path, type_, canonical_name, data in classified_items:
        try:
            if type_ == 'movie':
                # Películas van directamente a MOVIES_DIR
                dest_dir = _ensure_dir(MOVIES_DIR)
                _process_video_files(item_path, dest_dir)

            elif type_ == 'episode':
                # Series van a SERIES_DIR/SeriesName/Season XX/
                series_name = canonical_name.split(' - ')[0] if ' - ' in canonical_name else canonical_name
                series_name = _sanitize_name(series_name)

                season_num = data.get('season')
                if season_num is None:
                    logging.warning("📺 Episodio sin número de temporada: %s", item_path)
                    continue

                dest_series_dir = _ensure_dir(os.path.join(SERIES_DIR, series_name))
                dest_season_dir = _ensure_dir(os.path.join(dest_series_dir, f"Season {int(season_num):02d}"))
                _process_video_files(item_path, dest_season_dir)

            else:
                logging.warning("❓ Tipo desconocido para item: %s", item_path)

        except Exception as e:
            logging.error("❌ Error organizando '%s': %s", item_path, e)
            logging.warning("⚠️ No se pudo organizar '%s' (hardlinks no soportados o error)", item_path)
