import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)

# Configuración única
EMBEDDINGS_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "bancolombia_docs"

class VectorDBClient:
    """Clase Singleton o manejador centralizado para la base vectorial."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)
        self._vector_store = None

    def get_store(self) -> Chroma:
        if self._vector_store is None:
            logger.info(f"Conectando a ChromaDB en: {self.db_path}")
            self._vector_store = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=self._embeddings,
                persist_directory=self.db_path,
            )
        return self._vector_store

    def get_embeddings_name(self) -> str:
        return EMBEDDINGS_MODEL