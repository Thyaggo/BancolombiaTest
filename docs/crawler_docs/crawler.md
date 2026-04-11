# Crawler (`crawler.py`)

## Descripción
El Crawler es el componente encargado de extraer contenido del sitio web de Bancolombia (`bancolombia.com/personas`) de forma automatizada. Utiliza la librería **Crawl4AI** junto con **Playwright** para navegar y procesar el HTML en un entorno de navegador headless (sin interfaz).

## Funciones Principales

### `run_crawler(output_file)`
Es el punto de entrada principal del componente. Realiza el proceso en dos fases:
1.  **Fase de Descubrimiento:** Navega la URL semilla (`https://www.bancolombia.com/personas`) para extraer todos los enlaces internos.
2.  **Fase de Deep Crawl:** Utiliza un despachador adaptativo de memoria para navegar concurrentemente por todas las URLs descubiertas, extrayendo el contenido de cada una.
-   **Salida:** Un archivo `.jsonl` donde cada línea es un objeto JSON con los datos de una página.
-   **Persistencia:** Implementa escritura atómica con `f.flush()` para asegurar que los datos se guarden inmediatamente tras procesar cada página.

### `is_crawlable(url)`
Filtra URLs que no deben ser procesadas, como archivos PDF, manejadores de contenido específicos (`/!ut/p/`), o páginas de aplicaciones interactivas (turnos, seguros) que no contienen información textual útil para la base de conocimiento.

### `categorizar_url(url)`
Clasifica cada URL en una de las categorías predefinidas basándose en patrones en la ruta (path):
-   Productos y Servicios
-   Institucional / Corporativo
-   Blog / Educación Financiera
-   Tu360 (Comercio y Marketplace)
-   Presencia Internacional
-   Inversionistas y Subsidiarias Financieras
-   Canales Digitales / Sucursales Virtuales
-   Otros / Landing

## Configuración Técnica
-   **User-Agent:** Simula un navegador Chrome en Windows 10 para evitar bloqueos básicos.
-   **Content Filtering:** Usa `PruningContentFilter` con un umbral de 0.5 para eliminar "boilerplate" (menús, pies de página, scripts).
-   **Estrategia de Scraping:** `LXMLWebScrapingStrategy` para una extracción rápida y eficiente de texto.
-   **Gestión de Memoria:** `MemoryAdaptiveDispatcher` con un umbral del 80% para ajustar la concurrencia según la carga del sistema.

## Estructura de Datos de Salida (JSONL)
Cada registro contiene:
-   `url`: URL de la página.
-   `titulo`: Título extraído de la metadata.
-   `categoria`: Categoría asignada.
-   `status_code`: Código de respuesta HTTP.
-   `scraped_at`: Timestamp de la extracción.
-   `fit_markdown`: Contenido limpio en formato Markdown (ideal para RAG).
-   `raw_markdown`: Contenido completo sin filtrar.
