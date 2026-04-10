import json
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

from mcp_server import (
    KnowledgeBaseResponse,
    search_knowledge_base,
    get_article_by_url,
    list_categories,
    get_knowledge_base_stats,
)


class TestKnowledgeBaseResponse:
    """Tests para el modelo Pydantic KnowledgeBaseResponse"""

    def test_knowledge_base_response_valid(self):
        """Creación con contenido y fuentes válidos"""
        response = KnowledgeBaseResponse(
            contenido="Contenido de prueba",
            fuentes=[{"titulo": "Test", "url": "https://test.com"}],
        )
        assert response.contenido == "Contenido de prueba"
        assert len(response.fuentes) == 1
        assert response.fuentes[0]["titulo"] == "Test"

    def test_knowledge_base_response_empty_fuentes(self):
        """Creación con fuentes vacías"""
        response = KnowledgeBaseResponse(
            contenido="Sin resultados",
            fuentes=[],
        )
        assert response.contenido == "Sin resultados"
        assert response.fuentes == []


class TestSearchKnowledgeBase:
    """Tests para la función search_knowledge_base()"""

    @patch("mcp_server.vector_store")
    def test_search_returns_structured_response(self, mock_store):
        """Con resultados, retorna KnowledgeBaseResponse con contenido y fuentes"""
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "url": "https://www.bancolombia.com/test",
            "titulo": "Test Page",
        }
        mock_doc.page_content = "Contenido de prueba"
        mock_store.similarity_search.return_value = [mock_doc]

        result = search_knowledge_base("test query")

        assert isinstance(result, KnowledgeBaseResponse)
        assert result.contenido == "Contenido de prueba"
        assert len(result.fuentes) == 1
        assert result.fuentes[0]["url"] == "https://www.bancolombia.com/test"

    @patch("mcp_server.vector_store")
    def test_search_no_results(self, mock_store):
        """Sin resultados, retorna contenido apropiado y fuentes vacías"""
        mock_store.similarity_search.return_value = []

        result = search_knowledge_base("query inexistente")

        assert isinstance(result, KnowledgeBaseResponse)
        assert "No se encontraron" in result.contenido
        assert result.fuentes == []

    @patch("mcp_server.vector_store")
    def test_search_deduplicates_urls(self, mock_store):
        """Docs con misma URL generan solo una fuente"""
        mock_doc1 = MagicMock()
        mock_doc1.metadata = {
            "url": "https://www.bancolombia.com/test",
            "titulo": "Test Page 1",
        }
        mock_doc1.page_content = "Contenido chunk 1"

        mock_doc2 = MagicMock()
        mock_doc2.metadata = {
            "url": "https://www.bancolombia.com/test",
            "titulo": "Test Page 2",
        }
        mock_doc2.page_content = "Contenido chunk 2"

        mock_store.similarity_search.return_value = [mock_doc1, mock_doc2]

        result = search_knowledge_base("test query")

        assert len(result.fuentes) == 1
        assert result.fuentes[0]["url"] == "https://www.bancolombia.com/test"

    @patch("mcp_server.vector_store")
    def test_search_handles_exception(self, mock_store):
        """Excepción en similarity_search retorna error con fuentes vacías"""
        mock_store.similarity_search.side_effect = Exception("DB Error")

        result = search_knowledge_base("test query")

        assert isinstance(result, KnowledgeBaseResponse)
        assert "Error" in result.contenido
        assert result.fuentes == []


class TestGetArticleByUrl:
    """Tests para la función get_article_by_url()"""

    @patch("mcp_server.vector_store")
    def test_get_article_found(self, mock_store):
        """Retorna JSON con contenido y fuente"""
        mock_store.get.return_value = {
            "documents": ["Contenido del artículo"],
            "metadatas": [{"titulo": "Artículo de Prueba"}],
        }

        result = get_article_by_url("https://www.bancolombia.com/test")

        data = json.loads(result)
        assert data["contenido"] == "Contenido del artículo"
        assert len(data["fuentes"]) == 1
        assert data["fuentes"][0]["titulo"] == "Artículo de Prueba"

    @patch("mcp_server.vector_store")
    def test_get_article_not_found(self, mock_store):
        """Sin documentos, retorna JSON con fuentes vacías"""
        mock_store.get.return_value = {"documents": [], "metadatas": []}

        result = get_article_by_url("https://www.bancolombia.com/notfound")

        data = json.loads(result)
        assert "No se encontró" in data["contenido"]
        assert data["fuentes"] == []

    @patch("mcp_server.vector_store")
    def test_get_article_handles_exception(self, mock_store):
        """Excepción retorna JSON de error"""
        mock_store.get.side_effect = Exception("DB Error")

        result = get_article_by_url("https://www.bancolombia.com/test")

        data = json.loads(result)
        assert "Error" in data["contenido"]
        assert data["fuentes"] == []


class TestListCategories:
    """Tests para la función list_categories()"""

    @patch("mcp_server.vector_store")
    def test_list_categories_found(self, mock_store):
        """Retorna string con categorías ordenadas"""
        mock_store.get.return_value = {
            "metadatas": [
                {"categoria": "Productos y Servicios"},
                {"categoria": "Blog / Educación Financiera"},
                {"categoria": "Productos y Servicios"},
            ]
        }

        result = list_categories()

        assert "Categorías disponibles:" in result
        assert "Productos y Servicios" in result
        assert "Blog / Educación Financiera" in result

    @patch("mcp_server.vector_store")
    def test_list_categories_empty_db(self, mock_store):
        """Sin metadatas retorna mensaje apropiado"""
        mock_store.get.return_value = {"metadatas": []}

        result = list_categories()

        assert "No hay datos indexados" in result

    @patch("mcp_server.vector_store")
    def test_list_categories_no_category_field(self, mock_store):
        """Metadatas sin campo categoria retorna mensaje apropiado"""
        mock_store.get.return_value = {
            "metadatas": [{"url": "https://test.com"}, {"url": "https://test2.com"}]
        }

        result = list_categories()

        assert "No se encontraron categorías" in result


class TestGetKnowledgeBaseStats:
    """Tests para la función get_knowledge_base_stats()"""

    @patch("mcp_server.vector_store")
    def test_stats_returns_valid_json(self, mock_store):
        """Retorna JSON con estadísticas válidas"""
        mock_store._collection.count.return_value = 50
        mock_store.get.return_value = {
            "metadatas": [
                {"categoria": "Productos y Servicios"},
                {"categoria": "Blog"},
            ]
        }

        result = get_knowledge_base_stats()

        data = json.loads(result)
        assert data["documentos_indexados"] == 50
        assert "Productos y Servicios" in data["categorias_disponibles"]
        assert data["modelo_embeddings"] == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    @patch("mcp_server.vector_store")
    def test_stats_handles_exception(self, mock_store):
        """Excepción retorna JSON de error"""
        mock_store._collection.count.side_effect = Exception("DB Error")

        result = get_knowledge_base_stats()

        data = json.loads(result)
        assert "error" in data