from crawler import categorizar_url, is_crawlable


class TestIsCrawlable:
    """Tests para la función is_crawlable()"""

    def test_is_crawlable_valid_url(self):
        """URL normal sin patrones de skip debe retornar True"""
        assert is_crawlable("https://www.bancolombia.com/personas") is True

    def test_is_crawlable_pdf(self):
        """URL con .pdf debe retornar False"""
        assert is_crawlable("https://www.bancolombia.com/documento.pdf") is False

    def test_is_crawlable_portal_fragment(self):
        """URL con fragmento de portal debe retornar False"""
        assert is_crawlable("https://www.bancolombia.com/!ut/p/alguna-pagina") is False

    def test_is_crawlable_content_handler(self):
        """URL con contenthandler debe retornar False"""
        assert is_crawlable(
            "https://www.bancolombia.com/contenthandler/dummy"
        ) is False

    def test_is_crawlable_skip_patterns(self):
        """Verificar que todos los patrones de SKIP_PATTERNS son ignorados"""
        skip_patterns = [
            "/!ut/p/",
            ".pdf",
            "contenthandler",
            "solicitud-turno.apps.",
            "segurodeviaje.",
        ]
        for pattern in skip_patterns:
            assert is_crawlable(f"https://www.bancolombia.com/test{pattern}test") is False


class TestCategorizarUrl:
    """Tests para la función categorizar_url()"""

    def test_categorizar_institucional(self):
        """URLs con palabras clave institucionales retornan categoría correcta"""
        assert (
            categorizar_url("https://www.bancolombia.com/acerca-de/quienes-somos")
            == "Institucional / Corporativo"
        )
        assert (
            categorizar_url("https://www.bancolombia.com/corporativo/gobierno")
            == "Institucional / Corporativo"
        )
        assert (
            categorizar_url(
                "https://www.bancolombia.com/gobierno-corporativo/estructura"
            )
            == "Institucional / Corporativo"
        )

    def test_categorizar_blog(self):
        """URLs con 'blog' retornan Blog / Educación Financiera"""
        assert (
            categorizar_url("https://blog.bancolombia.com/educacion/ahorro")
            == "Blog / Educación Financiera"
        )
        assert (
            categorizar_url("https://www.bancolombia.com/blog/finanzas-personales")
            == "Blog / Educación Financiera"
        )

    def test_categorizar_productos(self):
        """URLs con palabras clave de productos retornan categoría correcta"""
        assert (
            categorizar_url(
                "https://www.bancolombia.com/productos-servicios/cuentas"
            )
            == "Productos y Servicios"
        )
        assert (
            categorizar_url("https://www.bancolombia.com/creditos/personales")
            == "Productos y Servicios"
        )
        assert (
            categorizar_url("https://www.bancolombia.com/leasing/vehiculos")
            == "Productos y Servicios"
        )

    def test_categorizar_internacional(self):
        """URLs con presencia internacional retornan categoría correcta"""
        assert (
            categorizar_url("https://panama.bancolombia.com/")
            == "Presencia Internacional"
        )
        assert (
            categorizar_url("https://puertorico.bancolombia.com/")
            == "Presencia Internacional"
        )

    def test_categorizar_default(self):
        """URL sin match retorna Otros / Landing"""
        assert (
            categorizar_url("https://www.bancolombia.com/alguna-pagina-desconocida")
            == "Otros / Landing"
        )
        assert (
            categorizar_url("https://www.bancolombia.com/")
            == "Otros / Landing"
        )