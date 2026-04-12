import json
from unittest.mock import MagicMock, patch

import pytest

# Importar una vez aquí para que el parche use el nombre correcto del módulo
from pipeline import BancolombiaPipeline

_PATCH_TARGET = "pipeline.VectorDBClient"


def _make_mock_store():
    """Devuelve un mock_store y mock_client correctamente configurados."""
    mock_store = MagicMock()
    # indexar_datos llama vector_store.get() para verificar URLs ya indexadas
    # ChromaDB devuelve un dict que contiene al menos 'ids', 'metadatas', 'documents'
    mock_store.get.return_value = {"ids": [], "metadatas": [], "documents": []}
    mock_client = MagicMock()
    mock_client.get_store.return_value = mock_store
    return mock_store, mock_client


class TestBancolombiaPipelineIndexarDatos:
    """Tests para el método BancolombiaPipeline.indexar_datos()"""

    def test_indexar_datos_file_not_found(self, tmp_path):
        """Archivo inexistente lanza FileNotFoundError"""
        mock_store, mock_client = _make_mock_store()
        with patch(_PATCH_TARGET, return_value=mock_client):
            pipeline = BancolombiaPipeline(
                str(tmp_path / "nonexistent.jsonl"), str(tmp_path / "db")
            )
            with pytest.raises(FileNotFoundError):
                pipeline.indexar_datos()

    def test_indexar_datos_procesa_documentos(self, tmp_path, sample_jsonl_records):
        """Verifica que indexar_datos procesa registros del JSONL"""
        jsonl_path = tmp_path / "test_data.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for record in sample_jsonl_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        db_path = tmp_path / "chroma_db"
        db_path.mkdir()

        mock_store, mock_client = _make_mock_store()
        with patch(_PATCH_TARGET, return_value=mock_client):
            pipeline = BancolombiaPipeline(str(jsonl_path), str(db_path))
            try:
                pipeline.indexar_datos()
            except Exception as e:
                pytest.fail(f"indexar_datos threw exception: {e}")

            assert mock_store.add_documents.called

    def test_indexar_datos_omite_registros_sin_contenido(self, tmp_path):
        """Registros sin fit_markdown son procesados sin error"""
        records = [
            {"url": "https://test.com/1", "titulo": "Test 1", "fit_markdown": ""},
            {"url": "https://test.com/2", "titulo": "Test 2", "fit_markdown": "Contenido válido"},
        ]

        jsonl_path = tmp_path / "test_data.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

        db_path = tmp_path / "chroma_db"
        db_path.mkdir()

        mock_store, mock_client = _make_mock_store()
        with patch(_PATCH_TARGET, return_value=mock_client):
            pipeline = BancolombiaPipeline(str(jsonl_path), str(db_path))
            try:
                pipeline.indexar_datos()
            except Exception as e:
                pytest.fail(f"indexar_datos threw exception: {e}")

    def test_indexar_datos_lote_multiple(self, tmp_path):
        """Verifica que puede procesar múltiples lotes"""
        records = [
            {"url": f"https://test.com/{i}", "titulo": f"Test {i}", "fit_markdown": f"Contenido {i}"}
            for i in range(60)
        ]

        jsonl_path = tmp_path / "test_data.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

        db_path = tmp_path / "chroma_db"
        db_path.mkdir()

        mock_store, mock_client = _make_mock_store()
        with patch(_PATCH_TARGET, return_value=mock_client):
            pipeline = BancolombiaPipeline(str(jsonl_path), str(db_path))
            try:
                pipeline.indexar_datos()
            except Exception as e:
                pytest.fail(f"indexar_datos threw exception: {e}")

    def test_indexar_datos_con_force_reindex(self, tmp_path, sample_jsonl_records):
        """Verifica que force_reindex funciona sin errores"""
        jsonl_path = tmp_path / "test_data.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for record in sample_jsonl_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        db_path = tmp_path / "chroma_db"
        db_path.mkdir()

        mock_store, mock_client = _make_mock_store()
        with patch(_PATCH_TARGET, return_value=mock_client):
            pipeline = BancolombiaPipeline(str(jsonl_path), str(db_path))
            try:
                pipeline.indexar_datos(force_reindex=True)
            except Exception as e:
                pytest.fail(f"indexar_datos threw exception: {e}")