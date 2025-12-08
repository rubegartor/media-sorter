import logging
from config import TMDB_API_KEY
import tmdbsimple as tmdb

if TMDB_API_KEY:
    tmdb.API_KEY = TMDB_API_KEY

def get_official_movie_title(info):
    """
    Consulta TMDb para películas. Busca solo por título (sin año) para obtener mejores resultados.
    Primero busca en inglés (en-US) para obtener el nombre oficial,
    luego busca en español (es-ES) para obtener el título localizado si está disponible.
    """
    title_search = info.get('title')
    if not TMDB_API_KEY or not title_search:
        return None, None

    # Buscar solo con el título, sin incluir el año
    query_text = title_search

    try:
        search = tmdb.Search()
        
        # Primero buscar en inglés para obtener el ID y el nombre oficial
        results_en = search.movie(query=query_text, language='en-US')

        if not results_en or not results_en.get('results'):
            logging.warning(f"⚠️ TMDb: No se encontró película. Buscado: '{query_text}'.")
            return None, None

        best_match = results_en['results'][0]
        official_title_en = best_match.get('title')
        movie_id = best_match.get('id')
        year = best_match.get('release_date', '')[:4]
        
        # Si tenemos el ID, intentar obtener el nombre en español
        if movie_id:
            try:
                movie = tmdb.Movies(movie_id)
                movie_details_es = movie.info(language='es-ES')
                title_es = movie_details_es.get('title')
                if title_es and title_es != official_title_en:
                    # Devolver el título en español si es diferente
                    return title_es, year if year else None
            except Exception as e:
                logging.debug(f"⚠️ No se pudo obtener detalles en español para película ID {movie_id}: {e}")
        
        # Si no hay título en español o no se pudo obtener, usar el de inglés
        return official_title_en, year if year else None

    except Exception as e:
        logging.error(f"❌ Error TMDb para '{query_text}': {e}")
        return None, None

def get_official_series_title(info):
    """
    Consulta TMDb para series. Primero busca en inglés (en-US) para obtener el nombre oficial,
    luego busca en español (es-ES) para obtener el título localizado si está disponible.
    """
    title_search = info.get('title')
    if not TMDB_API_KEY or not title_search:
        return None

    query_text = title_search
    if info.get('year'):
        query_text += f" {info['year']}"

    try:
        search = tmdb.Search()
        
        # Primero buscar en inglés para obtener el ID y el nombre oficial
        results_en = search.tv(query=query_text, language='en-US')
        
        if not results_en or not results_en.get('results'):
            logging.warning(f"⚠️ TMDb: No se encontró serie. Buscado: '{query_text}'.")
            return None
        
        best_match = results_en['results'][0]
        official_title_en = best_match.get('name')
        series_id = best_match.get('id')
        
        # Si tenemos el ID, intentar obtener el nombre en español
        if series_id:
            try:
                tv_series = tmdb.TV(series_id)
                tv_details_es = tv_series.info(language='es-ES')
                title_es = tv_details_es.get('name')
                if title_es and title_es != official_title_en:
                    # Devolver el título en español si es diferente
                    return title_es
            except Exception as e:
                logging.debug(f"⚠️ No se pudo obtener detalles en español para serie ID {series_id}: {e}")
        
        # Si no hay título en español o no se pudo obtener, usar el de inglés
        return official_title_en

    except Exception as e:
        logging.error(f"❌ Error TMDb para '{query_text}': {e}")
        return None
