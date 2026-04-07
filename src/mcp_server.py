from pathlib import Path
from mcp.server.fastmcp import FastMCP
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Fix #3: Ruta absoluta relativa al directorio del proyecto (padre de src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "chroma_banco_db")

# Fix #2: Usar los mismos embeddings que el pipeline de indexación
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# Fix #1: Nombre de colección alineado con pipeline.py ("bancolombia_docs")
vector_store = Chroma(
    collection_name="bancolombia_docs",
    embedding_function=embeddings,
    persist_directory=DB_PATH,
)

mcp = FastMCP("BancolombiaKnowledgeServer")


@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """
    Busca información técnica, comercial o de procesos sobre Bancolombia.
    Úsala cuando el usuario haga preguntas generales sobre el banco.
    """
    try:
        results = vector_store.similarity_search(query, k=3)

        if not results:
            return "No se encontró información relevante."

        fragments = []
        for doc in results:
            url = doc.metadata.get("url", "Sin URL")
            titulo = doc.metadata.get("titulo", "Sin título")
            fragments.append(f"[{titulo}]({url})\n{doc.page_content}")

        return "\n\n---\n\n".join(fragments)

    except Exception as e:
        return f"Error técnico al consultar la base de datos: {str(e)}"


@mcp.tool()
def get_article_by_url(url: str) -> str:
    """
    Recupera el contenido específico de un artículo o página de Bancolombia mediante su URL.
    Úsala solo si el usuario proporciona una URL específica o pregunta por un enlace concreto.
    """
    try:
        # Fix #8: Recuperar todos los chunks de la URL, no solo 1
        results = vector_store.get(where={"url": url})

        documents = results.get("documents", [])
        if not documents:
            return "No se encontró ningún artículo con esa URL."

        return "\n\n".join(documents)

    except Exception as e:
        return f"Error al recuperar el artículo por URL: {str(e)}"


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
