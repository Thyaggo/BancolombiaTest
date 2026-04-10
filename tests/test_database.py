import pytest
from unittest.mock import MagicMock, patch
from database import VectorDBClient, COLLECTION_NAME, EMBEDDINGS_MODEL


class TestVectorDBClient:
    """Tests para la clase VectorDBClient"""

    @patch("database.HuggingFaceEmbeddings")
    @patch("database.Chroma")
    def test_get_store_creates_chroma_instance(
        self, mock_chroma_class, mock_embeddings_class
    ):
        """get_store() crea una instancia de Chroma con parámetros correctos"""
        mock_embeddings = MagicMock()
        mock_embeddings_class.return_value = mock_embeddings

        mock_chroma_instance = MagicMock()
        mock_chroma_class.return_value = mock_chroma_instance

        client = VectorDBClient("/tmp/test_db")
        store = client.get_store()

        mock_chroma_class.assert_called_once_with(
            collection_name=COLLECTION_NAME,
            embedding_function=mock_embeddings,
            persist_directory="/tmp/test_db",
        )
        assert store == mock_chroma_instance

    @patch("database.HuggingFaceEmbeddings")
    @patch("database.Chroma")
    def test_get_store_is_lazy_singleton(
        self, mock_chroma_class, mock_embeddings_class
    ):
        """Llamar get_store() dos veces retorna el mismo objeto"""
        mock_embeddings = MagicMock()
        mock_embeddings_class.return_value = mock_embeddings

        mock_chroma_instance = MagicMock()
        mock_chroma_class.return_value = mock_chroma_instance

        client = VectorDBClient("/tmp/test_db")
        store1 = client.get_store()
        store2 = client.get_store()

        assert store1 is store2
        assert mock_chroma_class.call_count == 1

    @patch("database.HuggingFaceEmbeddings")
    @patch("database.Chroma")
    def test_get_embeddings_name(self, mock_chroma_class, mock_embeddings_class):
        """get_embeddings_name() retorna la constante EMBEDDINGS_MODEL"""
        mock_embeddings = MagicMock()
        mock_embeddings_class.return_value = mock_embeddings
        mock_chroma_class.return_value = MagicMock()

        client = VectorDBClient("/tmp/test_db")
        assert client.get_embeddings_name() == EMBEDDINGS_MODEL

    def test_collection_name_constant(self):
        """COLLECTION_NAME es 'bancolombia_docs'"""
        assert COLLECTION_NAME == "bancolombia_docs"