import json
import asyncio
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

# Crawl4AI
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, RateLimiter
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher

logger = logging.getLogger(__name__)

# Configuración Global
# DATA_DIR permite sobreescribir la ubicación en Docker vía variable de entorno.
# Localmente se usa el directorio de trabajo actual como fallback.
_DATA_DIR = os.getenv("DATA_DIR", ".")
DEFAULT_OUTPUT_FILE = str(Path(_DATA_DIR) / "resultados_bancolombia.jsonl")
SEED_URL = "https://www.bancolombia.com/personas"
SKIP_PATTERNS = ["/!ut/p/", ".pdf", "contenthandler", "solicitud-turno.apps.", "segurodeviaje."]


def is_crawlable(url: str) -> bool:
    """Retorna True si la URL no coincide con ningún patrón a omitir."""
    if not url or not isinstance(url, str):
        return False
    return not any(p in url for p in SKIP_PATTERNS)


def categorizar_url(url: str) -> str:
    """Clasifica una URL en una categoría de contenido de Bancolombia."""
    if not url or not isinstance(url, str):
        return "Otros / Landing"
    u = url.lower()
    if any(k in u for k in ["acerca-de", "corporativo", "gobierno-corporativo", "trabaja-con-nosotros", "mapa-del-sitio", "condiciones-de-uso"]):
        return "Institucional / Corporativo"
    if any(k in u for k in ["relacion-inversionistas", "valores", "fiduciaria", "bancainversion"]):
        return "Inversionistas y Subsidiarias Financieras"
    if "blog" in u:
        return "Blog / Educación Financiera"
    if any(k in u for k in ["tu360", "tu360compras", "inmobiliario", "movilidad"]):
        return "Tu360 (Comercio y Marketplace)"
    if any(k in u for k in ["panama", "puertorico", "sucursalpanama"]):
        return "Presencia Internacional"
    if any(k in u for k in ["leasing", "productos-servicios", "cuentas", "/creditos"]):
        return "Productos y Servicios"
    if any(k in u for k in ["sucursal", "sv", "apps.bancolombia.com", "transaccionesbancolombia.com"]):
        return "Canales Digitales / Sucursales Virtuales"
    return "Otros / Landing"


async def run_crawler(output_file: str = DEFAULT_OUTPUT_FILE) -> int:
    """Ejecuta el crawler completo y persiste resultados en *output_file* (JSONL).

    Puede ser invocado desde otros módulos (streamlit_app, main) además de
    ejecutarse como script independiente.

    Args:
        output_file: Ruta del archivo de salida. Se crea si no existe.

    Returns:
        Número de páginas guardadas exitosamente.

    Raises:
        ValueError: Si output_file es una cadena vacía.
        RuntimeError: Si la URL semilla falla completamente.
    """
    if not output_file or not isinstance(output_file, str):
        raise ValueError("output_file debe ser una ruta de archivo válida.")

    # Asegurar que el directorio padre existe
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Fase 1: Extracción de URLs semilla...")
    seed_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=False,
        magic=True,
    )
    browser_cfg = BrowserConfig(
        headless=True,
        verbose=False,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept-Language": "es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=SEED_URL, config=seed_config)
        if not result.success:
            raise RuntimeError(f"Fallo crítico en URL semilla: {result.error_message}")

        urls = [
            link["href"]
            for link in result.links.get("internal", [])
            if link.get("href") and link["href"].startswith("http") and is_crawlable(link["href"])
        ]
        urls = list(dict.fromkeys(urls))

    if not urls:
        print("Operación abortada: No se encontraron URLs válidas en la semilla.")
        return 0

    print(f"Fase 2: Deep Crawl sobre {len(urls)} URLs...")

    run_config = CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),
        excluded_tags=["script", "style", "header", "footer", "form", "iframe", "nav", "img", "picture", "svg"],
        word_count_threshold=30,
        only_text=True,
        remove_overlay_elements=True,
        exclude_all_images=True,
        exclude_external_images=True,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.5, threshold_type="fixed", min_word_threshold=30),
            options={"ignore_links": False, "body_width": 0},
        ),
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=False,
        magic=True,
        page_timeout=90000,
        stream=True,
        verbose=False,
    )

    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=80.0,
        check_interval=1.0,
        max_session_permit=5,
        rate_limiter=RateLimiter(base_delay=(2.0, 4.0), max_delay=30.0, max_retries=2),
    )

    pages_saved = 0
    with open(output_file, "a", encoding="utf-8") as f:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            async for result in await crawler.arun_many(urls=urls, config=run_config, dispatcher=dispatcher):
                if not result.success:
                    logger.error(f"Fallo en {result.url}: {result.error_message}")
                    continue

                md = result.markdown
                page_data = {
                    "url": result.url,
                    "titulo": result.metadata.get("title", "Sin Título") if result.metadata else "Sin Título",
                    "categoria": categorizar_url(result.url),
                    "status_code": result.status_code,
                    "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "fit_markdown": md.fit_markdown if md and md.fit_markdown else "",
                    "raw_markdown": md.raw_markdown if md and md.raw_markdown else "",
                }

                # Persistencia atómica línea a línea
                f.write(json.dumps(page_data, ensure_ascii=False) + "\n")
                f.flush()
                pages_saved += 1
                logger.info(f"Guardado: {result.url}")

    print(f"Crawler finalizado. {pages_saved} páginas guardadas en {output_file}")
    return pages_saved


if __name__ == "__main__":
    asyncio.run(run_crawler())