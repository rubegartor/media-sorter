import logging
from scanner import scan_and_classify
from organizer import organize_items, set_link_manager
from config import WATCH_DIR, TMDB_API_KEY, SERIES_DIR, MOVIES_DIR
from link_manager import LinkManager
from watcher import start_watching


if __name__ == "__main__":
    logging.info("=" * 50)
    logging.info(f"📁 Watch dir : {WATCH_DIR}")
    logging.info(f"📺 Series dir: {SERIES_DIR}")
    logging.info(f"🎬 Movies dir: {MOVIES_DIR}")
    logging.info(f"🔑 TMDB API  : {'Activa' if TMDB_API_KEY else 'INACTIVA'}")
    logging.info("=" * 50)

    # Inicializar LinkManager
    link_manager = LinkManager()
    set_link_manager(link_manager)

    logging.info("🚀 Media Sorter iniciado (modo vigilancia)")

    # Limpieza inicial de links rotos
    logging.info("🧹 Limpiando enlaces rotos...")
    link_manager.cleanup_broken_links()

    # Mostrar estadísticas
    stats = link_manager.get_stats()
    logging.info(f"📊 Estado inicial: {stats['total_sources']} fuentes, {stats['total_links']} links")

    # Procesamiento inicial de archivos existentes
    logging.info("🔍 Escaneando archivos existentes...")
    classified_items = scan_and_classify()

    if classified_items:
        logging.info(f"📦 Organizando {len(classified_items)} item(s) existente(s)...")
        organize_items(classified_items)
        logging.info("✅ Organización inicial completada")
    else:
        logging.info("ℹ️ No se encontraron items nuevos para organizar")

    logging.info("=" * 50)

    # Iniciar vigilancia continua
    start_watching(link_manager)


