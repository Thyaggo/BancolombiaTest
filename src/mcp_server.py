import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from database import VectorDBClient

# Configuración vía Variables de Env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "chroma_banco_db"))
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "BancolombiaKnowledgeServer")
SEARCH_K_VALUE = int(os.getenv("SEARCH_K_VALUE", "3"))

db_client = VectorDBClient(DB_PATH)
vector_store = db_client.get_store()

mcp = FastMCP(MCP_SERVER_NAME)

# Definición de modelos Pydantic para las respuestas de los tools
class KnowledgeBaseResponse(BaseModel):
    contenido: str
    fuentes: list[dict[str, str]] | list

@mcp.tool()
def search_knowledge_base(query: str) -> KnowledgeBaseResponse:
    """
    Busca información técnica, comercial o de procesos sobre Bancolombia.
    Úsala cuando el usuario haga preguntas generales sobre el banco.

    Retorna JSON con:
      - contenido: texto con los fragmentos relevantes encontrados.
      - fuentes: lista de objetos {titulo, url} de las páginas consultadas.
    """
    if not query or not isinstance(query, str) or not query.strip():
        return KnowledgeBaseResponse(
            contenido="La consulta no puede estar vacía.",
            fuentes=[],
        )

    try:
        results = vector_store.similarity_search(query.strip(), k=SEARCH_K_VALUE)

        if not results:
            return KnowledgeBaseResponse(
                contenido="No se encontraron resultados relevantes en la base de datos.",
                fuentes=[],
            )

        fragments = []
        fuentes_seen: dict[str, str] = {}  # url -> titulo (dedup)
        for doc in results:
            url = doc.metadata.get("url", "")
            titulo = doc.metadata.get("titulo", "Sin título")
            fragments.append(doc.page_content)
            if url and url not in fuentes_seen:
                fuentes_seen[url] = titulo

        fuentes = [{"titulo": t, "url": u} for u, t in fuentes_seen.items()]

        return KnowledgeBaseResponse(
            contenido="\n\n".join(fragments),
            fuentes=fuentes,
        )

    except Exception as e:
        return KnowledgeBaseResponse(
            contenido=f"Error al buscar en la base de datos: {str(e)}",
            fuentes=[],
        )


@mcp.tool()
def get_article_by_url(url: str) -> str:
    """
    Recupera el contenido específico de un artículo o página de Bancolombia mediante su URL.
    Úsala solo si el usuario proporciona una URL específica o pregunta por un enlace concreto.

    Retorna JSON con:
      - contenido: texto completo del artículo.
      - fuentes: lista con un objeto {titulo, url} de la página consultada.
    """
    if not url or not isinstance(url, str) or not url.strip():
        return json.dumps(
            {"contenido": "La URL no puede estar vacía.", "fuentes": []},
            ensure_ascii=False,
        )

    url = url.strip()

    try:
        results = vector_store.get(where={"url": url}, include=["documents", "metadatas"])

        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        if not documents:
            return json.dumps(
                {"contenido": "No se encontró ningún artículo con esa URL.", "fuentes": []},
                ensure_ascii=False,
            )

        titulo = "Sin título"
        if metadatas and metadatas[0]:
            titulo = metadatas[0].get("titulo", "Sin título") or "Sin título"

        return json.dumps(
            {
                "contenido": "\n\n".join(documents),
                "fuentes": [{"titulo": titulo, "url": url}],
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {"contenido": f"Error al recuperar el artículo por URL: {str(e)}", "fuentes": []},
            ensure_ascii=False,
        )


@mcp.tool()
def list_categories() -> str:
    """Usa esta herramienta para listar las categorías de los artículos guardados en la base de datos."""
    # Lista maestra de categorías definidas en el crawler
    expected_categories = [
        "Institucional / Corporativo",
        "Inversionistas y Subsidiarias Financieras",
        "Blog / Educación Financiera",
        "Tu360 (Comercio y Marketplace)",
        "Presencia Internacional",
        "Productos y Servicios",
        "Canales Digitales / Sucursales Virtuales",
        "Otros / Landing"
    ]
    
    found_categories = []
    
    try:
        # Alternativa 3: Verificación selectiva quirúrgica (RAM eficiente)
        for cat in expected_categories:
            # Consultamos solo si existe AL MENOS un documento para esta categoría
            res = vector_store.get(where={"categoria": cat}, limit=1)
            if res["ids"]:
                found_categories.append(cat)

        if not found_categories:
            return "No se encontraron categorías con documentos indexados."

        return "Categorías disponibles en la base de datos:\n" + "\n".join(
            f"- {c}" for c in sorted(found_categories)
        )

    except Exception as e:
        return f"Error al listar categorías de forma segura: {str(e)}"

@mcp.resource("knowledgebase://stats")
def get_knowledge_base_stats() -> str:
    try:
        # Conteo total de chunks indexados
        doc_count = vector_store._collection.count()

        # Fecha de último scraping: muestra de 1 documento (eficiente)
        sample_data = vector_store.get(limit=1, include=["metadatas"])
        last_update = "No disponible"
        if sample_data["metadatas"]:
            last_update = sample_data["metadatas"][0].get("scraped_at", "No disponible")

        # Categorías disponibles: verificación quirúrgica por categoría conocida
        # O(k) queries con limit=1 en lugar de traer todos los metadatos
        expected_categories = [
            "Institucional / Corporativo",
            "Inversionistas y Subsidiarias Financieras",
            "Blog / Educación Financiera",
            "Tu360 (Comercio y Marketplace)",
            "Presencia Internacional",
            "Productos y Servicios",
            "Canales Digitales / Sucursales Virtuales",
            "Otros / Landing",
        ]
        categorias_disponibles = [
            cat for cat in expected_categories
            if vector_store.get(where={"categoria": cat}, limit=1)["ids"]
        ]

        stats = {
            "documentos_indexados": doc_count,
            "categorias_disponibles": categorias_disponibles,
            "fecha_ultima_actualizacion": last_update,
            "modelo_embeddings": db_client.get_embeddings_name(),
        }
        return json.dumps(stats, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Error al recuperar estadísticas: {str(e)}"})

if __name__ == "__main__":
    mcp.run(transport="stdio")
