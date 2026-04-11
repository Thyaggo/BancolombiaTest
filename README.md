# 🏦 Asistente Bancolombia - RAG & MCP

![CI Pipeline](https://img.shields.io/badge/CI-Bancolombia%20Assistant-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![Framework](https://img.shields.io/badge/Framework-LangChain-green?style=flat-square)
![VectorDB](https://img.shields.io/badge/VectorDB-ChromaDB-orange?style=flat-square)
![LLM](https://img.shields.io/badge/LLM-Gemini%203.1%20Flash-red?style=flat-square)

Un asistente conversacional inteligente especializado en productos y servicios de **Bancolombia**. Este sistema utiliza una arquitectura **RAG (Retrieval-Augmented Generation)** y el estándar **MCP (Model Context Protocol)** para proporcionar respuestas precisas, actualizadas y con fuentes verificables extraídas directamente del sitio oficial.

---

## 🚀 Características Principales

-   **Web Crawling Autónomo:** Extracción inteligente de contenido desde `bancolombia.com` usando **Crawl4AI** y **Playwright**.
-   **Búsqueda Semántica:** Motor de búsqueda vectorial con **ChromaDB** y embeddings multilingües de **HuggingFace**.
-   **Arquitectura MCP:** Integración desacoplada de herramientas de conocimiento mediante el **Model Context Protocol**.
-   **Agente Inteligente:** Orquestación basada en **LangChain** y **LangGraph** con capacidades de razonamiento, resumen de historial y manejo de herramientas.
-   **Interfaz Dual:** Acceso mediante terminal (**CLI**) o interfaz web moderna (**Streamlit**).
-   **Infraestructura Robusta:** Totalmente contenedorizado con **Docker** y validado mediante **CI/CD** con GitHub Actions.

---

## 🏗️ Arquitectura del Sistema

El sistema opera en tres fases críticas:

1.  **Ingesta (Crawler):** Navega por el sitio de Bancolombia, filtra el contenido irrelevante (boilerplate) y persiste los datos en formato JSONL.
2.  **Indexación (Pipeline):** Divide el contenido en fragmentos semánticos (chunks) y los almacena en una base de datos vectorial local.
3.  **Consulta (Agente):** Un Agente ReAct procesa las preguntas del usuario, decide cuándo consultar la base de conocimiento vía MCP y genera una respuesta citando las fuentes.

> [!TIP]
> Consulta el archivo [ARQUITECTURA.md](ARQUITECTURA.md) para un desglose técnico profundo y diagramas de flujo de datos.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
| :--- | :--- |
| **LLM** | Google Gemini 3.1 Flash Lite |
| **Agentes** | LangChain / LangGraph |
| **Protocolo** | MCP (FastMCP) |
| **Base Vectorial** | ChromaDB |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` |
| **Scraping** | Crawl4AI / Playwright |
| **UI** | Streamlit |

---

## ⚙️ Configuración e Instalación

### Requisitos Previos
- Python 3.12+
- Docker y Docker Compose (opcional para despliegue)
- Una API Key de **Google AI Studio** (Gemini)

### 1. Clonar y Configurar Entorno
```bash
git clone https://github.com/tu-usuario/BancolombiaTest.git
cd BancolombiaTest

# Crear archivo de entorno
echo "GOOGLE_API_KEY=tu_clave_aqui" > .env
```

### 2. Ejecución con Docker (Recomendado)
El entorno Docker ya incluye todas las dependencias del sistema para Playwright.
```bash
docker compose up --build
```
*La interfaz web estará disponible en `http://localhost:8501`.*

### 3. Ejecución Local (Desarrollo)
```bash
# Instalar dependencias
pip install -r requirements.txt
playwright install chromium --with-deps

# Iniciar Interfaz Web
streamlit run src/streamlit_app.py

# O iniciar Interfaz CLI
python src/main.py
```

---

## 📂 Estructura del Proyecto

```text
├── docs/               # Documentación detallada por componente
├── src/
│   ├── crawler.py      # Extracción de datos web
│   ├── database.py     # Cliente ChromaDB y Embeddings
│   ├── mcp_server.py   # Servidor de herramientas MCP
│   ├── pipeline.py     # Orquestador de indexación y agente
│   ├── main.py         # Punto de entrada CLI
│   └── streamlit_app.py # Punto de entrada Web
├── tests/              # Suite de pruebas unitarias (pytest)
├── ARQUITECTURA.md     # Documentación de arquitectura global
└── docker-compose.yml  # Configuración de contenedores
```

---

## 🧪 Pruebas y Calidad

El proyecto cuenta con una cobertura de pruebas exhaustiva mediante `pytest`.

```bash
# Ejecutar todas las pruebas
python -m pytest tests/ -v
```

El pipeline de **CI/CD** configurado en GitHub Actions valida automáticamente:
- Estándares de código con **Ruff**.
- Ejecución de pruebas unitarias y reporte de cobertura.
- Construcción exitosa de la imagen Docker.

---

## 📖 Documentación Adicional

Para más detalles sobre cada módulo, consulta la carpeta `docs/`:
- [Crawler y Scraping](docs/crawler.md)
- [Base de Datos Vectorial](docs/database.md)
- [Servidor MCP y Herramientas](docs/mcp_server.md)
- [Pipeline y Lógica del Agente](docs/pipeline.md)
- [Interfaz Web (Streamlit)](docs/streamlit_app.md)
- [Interfaz de Comandos (CLI)](docs/main.md)

---

## 🚀 Siguientes Pasos (Roadmap Arquitectónico)



---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulte el archivo `LICENSE` para más detalles (si aplica).
