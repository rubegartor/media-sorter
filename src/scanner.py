import os
import logging
import re
import unicodedata
from guessit import guessit
from src.config import WATCH_DIR, VIDEO_EXTENSIONS
from src.tmdb_utils import get_official_movie_title, get_official_series_title


def _normalize_title_for_cache(title):
    """Normaliza un título para usarlo como clave en caché, ignorando diacríticos y espacios extras."""
    if not title:
        return None
    title = title.lower()
    title = ' '.join(title.split())
    nfd = unicodedata.normalize('NFD', title) # Eliminar diacríticos (NFD)
    title_no_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return title_no_accents

def scan_and_classify():
    """Escanea el directorio, clasifica contenido y obtiene títulos oficiales."""
    items = []
    title_cache = {}

    for item_name in os.listdir(WATCH_DIR):
        if item_name.startswith('.'): # Ignorar archivos ocultos
            continue

        item_path = os.path.join(WATCH_DIR, item_name)
        if os.path.isdir(item_path):
            # Si es carpeta, buscar archivos de video dentro
            for root, dirs, files in os.walk(item_path):
                for file in files:
                    if file.lower().endswith(VIDEO_EXTENSIONS):
                        full_path = os.path.join(root, file)
                        data = guessit(file)
                        if data and data.get('type') in ['episode', 'movie']:
                            items.append((full_path, data))
        else:
            if item_name.lower().endswith(VIDEO_EXTENSIONS):
                data = guessit(item_name)
                if data and data.get('type') in ['episode', 'movie']:
                    items.append((item_path, data))

    classified_items = []

    for item_path, data in items:
        try:
            item_name = os.path.basename(item_path)
            if data and data.get('type') == 'movie' and 'alternative_title' in data:
                match = re.match(r'^T(\d+)$', data['alternative_title'])
                if match:
                    data['season'] = int(match.group(1))
                    data['type'] = 'episode'
                    del data['alternative_title']

            if not data or data.get('type') not in ['episode', 'movie']:
                logging.warning(f"❓ NO CLASIFICADO (Guessit): {item_name}")
                continue

            type_ = data.get("type")
            title_detected = data.get('title', 'N/A')
            canonical_name = None

            if type_ == "movie":
                title_key = _normalize_title_for_cache(title_detected)
                if title_key not in title_cache:
                    title_cache[title_key] = get_official_movie_title(data)
                official_title, official_year = title_cache[title_key]
                if official_title:
                    canonical_name = f"{official_title} ({official_year})" if official_year else official_title
                else:
                    logging.warning(f"❌ PELÍCULA: '{item_name}' -> Fallo al obtener título oficial de TMDb (Título detectado: {title_detected}).")
                    canonical_name = title_detected

            elif type_ == "episode":
                if "title" not in data or "season" not in data:
                    logging.warning(f"📺 SERIE (Incompleto): '{item_name}' -> Faltan Título/Temporada en Guessit.")
                    continue
                title_key = _normalize_title_for_cache(title_detected)
                if title_key not in title_cache:
                    title_cache[title_key] = get_official_series_title(data)
                official_title = title_cache[title_key]
                if official_title:
                    season_num = data['season']
                    episode_num = data.get('episode')
                    if episode_num:
                        canonical_name = f"{official_title} - S{season_num:02d}E{episode_num:02d}"
                    else:
                        canonical_name = f"{official_title} (Season {season_num:02d})"
                else:
                    logging.warning(f"❌ SERIE: '{item_name}' -> Fallo al obtener título oficial de TMDb (Título detectado: {title_detected}).")
                    canonical_name = title_detected

            if canonical_name:
                classified_items.append((item_path, type_, canonical_name, data))

        except Exception as e:
            logging.error('Error al procesar item %s: %s', item_path, e)

    return classified_items
