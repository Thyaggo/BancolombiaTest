import json
from pydantic import BaseModel
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from database import VectorDBClient
from langchain_chroma import Chroma

# Fix #3: Ruta absoluta relativa al directorio del proyecto (padre de src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "chroma_banco_db")

db_client = VectorDBClient(DB_PATH)
vector_store = db_client.get_store()

mcp = FastMCP("BancolombiaKnowledgeServer")

# Fix #2: Definición de modelos Pydantic para las respuestas de los tools
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
    try:
        results = vector_store.similarity_search(query, k=3)

        if not results:
            return KnowledgeBaseResponse(
                contenido="No se encontraron resultados relevantes en la base de datos.",
                fuentes=[]
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
            fuentes=fuentes
        )

    except Exception as e:
        return KnowledgeBaseResponse(
            contenido=f"Error al buscar en la base de datos: {str(e)}",
            fuentes=[]
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
        if metadatas:
            titulo = metadatas[0].get("titulo", "Sin título")

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
    try:
        # Fix #7: Implementación real — extrae categorías únicas de los metadatos
        all_data = vector_store.get(include=["metadatas"])
        metadatas = all_data.get("metadatas", [])

        if not metadatas:
            return "No hay datos indexados en la base de datos."

        categories = set()
        for meta in metadatas:
            cat = meta.get("categoria")
            if cat:
                categories.add(cat)

        if not categories:
            return "No se encontraron categorías en los metadatos. Los documentos no tienen el campo 'categoria'."

        return "Categorías disponibles:\n" + "\n".join(
            f"- {c}" for c in sorted(categories)
        )

    except Exception as e:
        return f"Error al listar categorías: {str(e)}"

@mcp.resource("knowledge-base://stats")
def get_knowledge_base_stats() -> str:
    try:
        # 1. Conteo rápido (O(1) en la mayoría de implementaciones vectoriales)
        doc_count = vector_store._collection.count()
        
        # 2. EFICIENCIA: Recuperar SOLO un documento para sacar la fecha y categorías
        # En lugar de .get(include=["metadatas"]), pedimos un sample de 1.
        sample_data = vector_store.get(limit=1, include=["metadatas"])
        
        last_update = "No disponible"
        if sample_data["metadatas"]:
            last_update = sample_data["metadatas"][0].get("scraped_at", "Fecha no disponible")

        # 3. Para las categorías, si son pocas, podrías guardarlas en un JSON aparte 
        # durante la indexación para no tener que iterar la DB aquí.
        # Por ahora, si quieres ser eficiente, recupera una muestra representativa, no TODO.
        
        stats = {
            "documentos_indexados": doc_count,
            "fecha_muestra_scraped": last_update,
            "modelo_embeddings": db_client.get_embeddings_name()
        }
        return json.dumps(stats, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Error al recuperar estadísticas: {str(e)}"})

if __name__ == "__main__":
    mcp.run(transport="stdio")
