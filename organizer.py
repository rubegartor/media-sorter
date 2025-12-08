import os
import platform
import logging
import unicodedata
from typing import Optional
from config import SERIES_DIR, MOVIES_DIR, VIDEO_EXTENSIONS
from pathvalidate import sanitize_filename
from link_manager import LinkManager

_link_manager: Optional['LinkManager'] = None


def set_link_manager(link_manager):
    """Establece el LinkManager global para registrar hard links."""
    global _link_manager
    _link_manager = link_manager


def _normalize_string(text):
    """Normaliza un string: convierte a NFD, elimina diacríticos, convierte a ASCII."""
    if not isinstance(text, str):
        return text
    # NFD: descompone caracteres acentuados
    nfd = unicodedata.normalize('NFD', text)
    # Elimina marcas diacríticas
    without_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return without_accents

def sanitize_name(name):
    """Sanea nombres para evitar caracteres inválidos en carpetas según el sistema operativo.
    También normaliza caracteres acentuados para evitar duplicados."""
    # Primero normalizar acentos
    normalized = _normalize_string(name)
    plat = platform.system().lower()
    if 'windows' in plat:
        return sanitize_filename(normalized, platform='windows')
    elif 'linux' in plat:
        return sanitize_filename(normalized, platform='linux')
    else:
        return sanitize_filename(normalized, platform='universal')


def _try_link(src, dst):
    """Intenta crear hardlink y lo registra en el LinkManager"""
    try:
        os.link(src, dst)
        # Registrar el hard link en el manager
        if _link_manager:
            _link_manager.add_link(src, dst)
        return True
    except Exception as e:
        logging.error("❌ Error creando hardlink '%s' -> '%s': %s", src, dst, e)
        return False


def _ensure_dir(path):
    """Asegura que la ruta exista; path puede ser PathLike o str."""
    p = os.fspath(path)
    os.makedirs(p, exist_ok=True)
    return p


def _is_video_file(filename):
    return filename.lower().endswith(VIDEO_EXTENSIONS)

def _process_file(src_path, dest_dir):
    """Procesa un archivo individual: crea hardlink en dest_dir si no existe."""
    src = os.fspath(src_path)
    dest_dir = os.fspath(dest_dir)
    dest_path = os.path.join(dest_dir, os.path.basename(src))
    if not os.path.exists(dest_path):
        _try_link(src, dest_path)


def _process_dir(src_dir, dest_dir):
    """Procesa todos los archivos de video dentro de una carpeta (recursivamente), enlazándolos al dest_dir."""
    src_dir = os.fspath(src_dir)
    dest_dir = os.fspath(dest_dir)
    for root, _, files in os.walk(src_dir):
        for file in files:
            if _is_video_file(file):
                src_file = os.path.join(os.fspath(root), os.fspath(file))
                dest_file = os.path.join(dest_dir, os.fspath(file))
                if not os.path.exists(dest_file):
                    _try_link(src_file, dest_file)


def organize_items(classified_items):
    """Organiza los items clasificados en las carpetas destino."""
    for item_path, type_, canonical_name, data in classified_items:
        try:
            if type_ == 'movie':
                dest_dir = _ensure_dir(MOVIES_DIR)

                if os.path.isdir(item_path):
                    _process_dir(item_path, dest_dir)
                else:
                    _process_file(item_path, dest_dir)

            elif type_ == 'episode':
                series_name = canonical_name.split(' - ')[0] if ' - ' in canonical_name else canonical_name
                series_name = sanitize_name(series_name)
                season_num = data.get('season')
                if season_num is None:
                    logging.warning("📺 Episodio sin número de temporada: %s", item_path)
                    continue

                dest_series_dir = _ensure_dir(os.path.join(SERIES_DIR, series_name))
                dest_season_dir = _ensure_dir(os.path.join(dest_series_dir, f"Season {int(season_num):02d}"))

                if os.path.isdir(item_path):
                    _process_dir(item_path, dest_season_dir)
                else:
                    _process_file(item_path, dest_season_dir)

            else:
                logging.warning("❓ Tipo desconocido para item: %s", item_path)

        except Exception as e:
            logging.error("❌ Error creando hardlink para '%s': %s", item_path, e)
            logging.warning("⚠️ No se pudo organizar '%s' (hardlinks no soportados o error)", item_path)
