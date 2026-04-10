import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from langchain_core.documents import Document


@pytest.fixture
def mock_vector_store():
    """Crea un mock de Chroma vector store con métodos básicos."""
    store = MagicMock()
    store._collection = MagicMock()
    store._collection.count.return_value = 100
    store.similarity_search = MagicMock(return_value=[])
    store.get = MagicMock(return_value={"documents": [], "metadatas": []})
    store.add_documents = MagicMock()
    store.delete_collection = MagicMock()
    return store


@pytest.fixture
def sample_documents():
    """Lista de documentos de prueba con metadata realista."""
    return [
        Document(
            page_content="Contenido de la página de cuentas de ahorro",
            metadata={
                "url": "https://www.bancolombia.com/personas/cuentas/ahorro",
                "titulo": "Cuentas de Ahorro",
                "categoria": "Productos y Servicios",
                "scraped_at": "2025-01-15 10:30:00",
            },
        ),
        Document(
            page_content="Contenido de la página de CDT",
            metadata={
                "url": "https://www.bancolombia.com/personas/inversion/cdt",
                "titulo": "Certificados de Depósito a Término",
                "categoria": "Productos y Servicios",
                "scraped_at": "2025-01-15 11:00:00",
            },
        ),
        Document(
            page_content="Contenido del blog de educación financiera",
            metadata={
                "url": "https://blog.bancolombia.com/educacion/ahorro-inicial",
                "titulo": "Cómo ahorrar desde cero",
                "categoria": "Blog / Educación Financiera",
                "scraped_at": "2025-01-14 09:00:00",
            },
        ),
    ]


@pytest.fixture
def tmp_jsonl(tmp_path):
    """Crea un archivo JSONL temporal con datos de prueba válidos."""

    def _create_jsonl(records: list[dict]) -> Path:
        filepath = tmp_path / "test_data.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return filepath

    return _create_jsonl


@pytest.fixture
def sample_jsonl_records():
    """Registros de ejemplo para crear archivos JSONL de prueba."""
    return [
        {
            "url": "https://www.bancolombia.com/personas/cuentas/ahorro",
            "titulo": "Cuentas de Ahorro",
            "categoria": "Productos y Servicios",
            "status_code": 200,
            "scraped_at": "2025-01-15 10:30:00",
            "fit_markdown": "Contenido de cuentas de ahorro...",
            "raw_markdown": "# Cuentas de Ahorro\n\nContenido completo...",
        },
        {
            "url": "https://www.bancolombia.com/personas/inversion/cdt",
            "titulo": "CDT",
            "categoria": "Productos y Servicios",
            "status_code": 200,
            "scraped_at": "2025-01-15 11:00:00",
            "fit_markdown": "Contenido de CDT...",
            "raw_markdown": "# CDT\n\nContenido completo...",
        },
    ]