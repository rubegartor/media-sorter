import os
import json
import logging
from typing import Dict, List, Set


class LinkManager:
    """Gestiona el mapa de hard links entre archivos fuente y destino."""

    def __init__(self):
        """Inicializa el LinkManager."""
        from src.config import HARDLINKS_DB_PATH
        db_path = HARDLINKS_DB_PATH

        # Normalizar a ruta absoluta
        self.db_path = os.path.abspath(db_path)
        self.links: Dict[str, List[str]] = {}  # {source_path: [dest_path1, dest_path2, ...]}
        self.load()

    def load(self):
        """Carga el mapa de hard links desde el archivo JSON."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.links = json.load(f)
                logging.info(f"✅ Mapa de hard links cargado: {len(self.links)} entradas")
            except Exception as e:
                logging.error(f"❌ Error al cargar el mapa de hard links: {e}")
                self.links = {}
        else:
            logging.info("📝 Creando nuevo mapa de hard links")
            self.links = {}

    def save(self):
        """Guarda el mapa de hard links en el archivo JSON."""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.links, f, indent=2, ensure_ascii=False)
            logging.debug(f"💾 Mapa de hard links guardado: {len(self.links)} entradas")
        except Exception as e:
            logging.error(f"❌ Error al guardar el mapa de hard links en {self.db_path}: {e}", exc_info=True)

    def add_link(self, source_path: str, dest_path: str):
        """Registra un nuevo hard link."""
        source_path = os.path.abspath(os.path.normpath(source_path))
        dest_path = os.path.abspath(os.path.normpath(dest_path))

        if source_path not in self.links:
            self.links[source_path] = []

        if dest_path not in self.links[source_path]:
            self.links[source_path].append(dest_path)
            self.save()
            logging.info(f"🔗 Link registrado: {source_path} -> {dest_path}")

    def get_links(self, source_path: str) -> List[str]:
        """Obtiene todos los hard links asociados a un archivo fuente."""
        source_path = os.path.abspath(os.path.normpath(source_path))
        return self.links.get(source_path, [])

    def remove_source(self, source_path: str) -> List[str]:
        """Elimina un archivo fuente y retorna sus hard links."""
        source_path = os.path.abspath(os.path.normpath(source_path))
        links = self.links.pop(source_path, [])
        if links:
            self.save()
            logging.debug(f"🗑️ Fuente eliminada del mapa: {source_path}")
        return links

    def cleanup_broken_links(self):
        """Limpia el mapa eliminando entradas donde ni la fuente ni los destinos existen."""
        cleaned = 0
        sources_to_remove = []

        for source_path, dest_paths in list(self.links.items()):
            # Filtrar destinos que aún existen
            existing_dests = [d for d in dest_paths if os.path.exists(d)]

            # Si la fuente no existe y no quedan destinos, marcar para eliminar
            if not os.path.exists(source_path) and not existing_dests:
                sources_to_remove.append(source_path)
                cleaned += 1
            elif existing_dests != dest_paths:
                # Actualizar solo los destinos que existen
                self.links[source_path] = existing_dests
                cleaned += 1

        # Eliminar fuentes marcadas
        for source in sources_to_remove:
            del self.links[source]

        if cleaned > 0:
            self.save()
            logging.info(f"🧹 Limpieza completada: {cleaned} entradas corregidas")

        return cleaned

    def get_all_sources(self) -> Set[str]:
        """Obtiene el conjunto de todos los archivos fuente registrados."""
        return set(self.links.keys())

    def get_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas del mapa de links."""
        total_sources = len(self.links)
        total_links = sum(len(dests) for dests in self.links.values())
        return {
            "total_sources": total_sources,
            "total_links": total_links
        }
