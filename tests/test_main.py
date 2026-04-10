import pytest
from main import _extract_text_from_content


class TestExtractTextFromContent:
    """Tests para la función _extract_text_from_content()"""

    def test_extract_string_content(self):
        """Input string retorna el mismo string"""
        content = "Esta es una respuesta directa del modelo"
        assert _extract_text_from_content(content) == content

    def test_extract_content_blocks(self):
        """Lista de ContentBlocks retorna texto concatenado"""
        content = [
            {"type": "text", "text": "Primera parte "},
            {"type": "text", "text": "Segunda parte"},
        ]
        result = _extract_text_from_content(content)
        assert result == "Primera parte Segunda parte"

    def test_extract_mixed_blocks(self):
        """Lista con text blocks y tool_call blocks, solo extrae text"""
        content = [
            {"type": "text", "text": "Respuesta: "},
            {"type": "tool_call", "id": "call_123", "name": "search"},
            {"type": "text", "text": "Resultado del tool"},
        ]
        result = _extract_text_from_content(content)
        assert result == "Respuesta: Resultado del tool"

    def test_extract_string_list(self):
        """Lista de strings retorna concatenación"""
        content = ["Hello", " ", "World"]
        result = _extract_text_from_content(content)
        assert result == "Hello World"

    def test_extract_empty_list(self):
        """Lista vacía retorna string vacío"""
        assert _extract_text_from_content([]) == ""

    def test_extract_none_type(self):
        """Input None retorna string vacío"""
        assert _extract_text_from_content(None) == ""

    def test_extract_int_type(self):
        """Input int retorna string vacío"""
        assert _extract_text_from_content(123) == ""