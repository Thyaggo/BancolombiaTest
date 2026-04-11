import os
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)

# Configuración vía Variables de Entorno
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "bancolombia_docs")

class VectorDBClient:
    """Manejador centralizado para la base vectorial ChromaDB."""

    def __init__(self, db_path: str):
        if not db_path or not isinstance(db_path, str):
            raise ValueError("db_path debe ser una ruta de directorio válida y no vacía.")
        self.db_path = db_path
        self._embeddings = None
        self._vector_store = None

    def _get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            logger.info(f"Cargando modelo de embeddings: {EMBEDDINGS_MODEL}")
            self._embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)
        return self._embeddings

    def get_store(self) -> Chroma:
        if self._vector_store is None:
            logger.info(f"Conectando a ChromaDB en: {self.db_path}")
            self._vector_store = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=self._get_embeddings(),
                persist_directory=self.db_path,
            )
        return self._vector_store

    def get_embeddings_name(self) -> str:
        return EMBEDDINGS_MODEL