import os
import time
import logging
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from config import WATCH_DIR, VIDEO_EXTENSIONS
from scanner import scan_and_classify
from organizer import organize_items
from link_manager import LinkManager


def _process_new_files(files: list):
    """Procesa archivos nuevos: los clasifica y organiza."""
    try:
        # Ejecutar scan_and_classify
        logging.info("🔍 Escaneando y clasificando...")
        classified_items = scan_and_classify()

        # Filtrar solo los items que corresponden a los archivos nuevos
        files_normalized = [os.path.normpath(f) for f in files]
        new_classified = []

        for item_path, type_, canonical_name, data in classified_items:
            item_normalized = os.path.normpath(item_path)

            # Verificar si el item es uno de los archivos nuevos o está dentro de un directorio nuevo
            is_new = False
            for new_file in files_normalized:
                if item_normalized == new_file or item_normalized.startswith(new_file + os.sep):
                    is_new = True
                    break

            if is_new:
                new_classified.append((item_path, type_, canonical_name, data))

        if new_classified:
            logging.info(f"📦 Organizando {len(new_classified)} item(s)...")
            organize_items(new_classified)
            logging.info("✅ Procesamiento completado")
        else:
            logging.info("ℹ️ No se encontraron items clasificables en los archivos nuevos")

    except Exception as e:
        logging.error(f"❌ Error al procesar archivos nuevos: {e}", exc_info=True)


class MediaWatcher(FileSystemEventHandler):
    """Vigilante de cambios en el directorio WATCH."""

    def __init__(self, link_manager: LinkManager, debounce_seconds: float = 2.0):
        super().__init__()
        self.link_manager = link_manager
        self.debounce_seconds = debounce_seconds
        self.pending_files = {}  # {path: timestamp}
        self.processing = False

    def _is_video_file(self, path: str) -> bool:
        """Verifica si el archivo es un video."""
        return path.lower().endswith(VIDEO_EXTENSIONS)

    def _should_process(self, path: str) -> bool:
        """Verifica si el archivo debe ser procesado."""
        # Ignorar archivos ocultos y temporales
        basename = os.path.basename(path)
        if basename.startswith('.') or basename.endswith('.tmp') or basename.endswith('.part'):
            return False

        # Solo procesar videos
        if os.path.isfile(path):
            return self._is_video_file(path)

        # Procesar directorios (podrían contener videos)
        return os.path.isdir(path)

    def on_created(self, event: FileSystemEvent):
        """Maneja la creación de archivos o directorios."""
        if event.is_directory:
            logging.info(f"📁 Nuevo directorio detectado: {event.src_path}")
        else:
            if self._should_process(event.src_path):
                logging.info(f"📄 Nuevo archivo detectado: {event.src_path}")

        # Agregar a la cola con debounce
        self.pending_files[event.src_path] = time.time()

    def on_modified(self, event: FileSystemEvent):
        """Maneja la modificación de archivos (como cuando termina de copiarse)."""
        if not event.is_directory and self._should_process(event.src_path):
            # Actualizar timestamp para extender el debounce
            self.pending_files[event.src_path] = time.time()

    def on_deleted(self, event: FileSystemEvent):
        """Maneja la eliminación de archivos o directorios."""
        path = os.path.normpath(event.src_path)

        # Eliminar de pendientes si estaba esperando
        self.pending_files.pop(path, None)

        # Buscar y eliminar hard links asociados
        links = self.link_manager.get_links(path)

        if links:
            logging.info(f"🗑️ Archivo eliminado: {path}")
            logging.info(f"🔗 Eliminando {len(links)} hard link(s) asociado(s)...")

            for link_path in links:
                try:
                    if os.path.exists(link_path):
                        os.remove(link_path)
                        logging.info(f"  ✅ Eliminado: {link_path}")
                    else:
                        logging.debug(f"  ⚠️ Ya no existe: {link_path}")
                except Exception as e:
                    logging.error(f"  ❌ Error al eliminar {link_path}: {e}")

            # Eliminar del mapa
            self.link_manager.remove_source(path)
            logging.info(f"✅ Hard links eliminados para: {path}")

        # Si es un directorio, buscar archivos dentro que puedan tener links
        if event.is_directory:
            self._cleanup_directory_links(path)

    def _cleanup_directory_links(self, dir_path: str):
        """Limpia los links de todos los archivos que estaban dentro de un directorio eliminado."""
        dir_path_normalized = os.path.normpath(dir_path)
        sources_to_remove = []

        # Buscar todas las fuentes que empiezan con la ruta del directorio
        for source_path in self.link_manager.get_all_sources():
            if source_path.startswith(dir_path_normalized + os.sep):
                sources_to_remove.append(source_path)

        if sources_to_remove:
            logging.info(f"🗂️ Limpiando {len(sources_to_remove)} archivo(s) del directorio eliminado...")
            for source_path in sources_to_remove:
                links = self.link_manager.remove_source(source_path)
                for link_path in links:
                    try:
                        if os.path.exists(link_path):
                            os.remove(link_path)
                            logging.debug(f"  ✅ Eliminado: {link_path}")
                    except Exception as e:
                        logging.error(f"  ❌ Error al eliminar {link_path}: {e}")

    def process_pending_files(self):
        """Procesa archivos pendientes que hayan superado el tiempo de debounce."""
        if self.processing or not self.pending_files:
            return

        current_time = time.time()
        ready_files = []

        # Buscar archivos que estén listos (han pasado debounce_seconds sin modificaciones)
        for path, timestamp in list(self.pending_files.items()):
            if current_time - timestamp >= self.debounce_seconds:
                ready_files.append(path)
                del self.pending_files[path]

        if ready_files:
            # Verificar que los archivos aún existan
            existing_files = [f for f in ready_files if os.path.exists(f)]

            if existing_files:
                logging.info(f"🔄 Procesando {len(existing_files)} archivo(s) nuevo(s)...")
                self.processing = True
                try:
                    _process_new_files(existing_files)
                finally:
                    self.processing = False


def start_watching(link_manager: LinkManager):
    """Inicia la vigilancia del directorio WATCH."""
    # Decidir si usar polling observer: fuerza con WATCHER_POLLING=1
    use_polling = os.environ.get('WATCHER_POLLING') == '1'

    if use_polling:
        logging.info("ℹ️ WATCHER_POLLING activado por variable de entorno; usando PollingObserver")

    observer = PollingObserver() if use_polling else Observer()

    event_handler = MediaWatcher(link_manager)
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()

    logging.info(f"👀 Vigilando directorio: {WATCH_DIR} (polling={use_polling})")

    try:
        while True:
            time.sleep(1)
            event_handler.process_pending_files()

    except KeyboardInterrupt:
        logging.info("⏹️ Deteniendo vigilancia...")
        observer.stop()

    observer.join()
    logging.info("✅ Vigilancia detenida")
