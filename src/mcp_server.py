from mcp.server.fastmcp import FastMCP
import chromadb

# Inicialización del servidor y base de datos (Global)
mcp = FastMCP("BancolombiaKnowledgeServer")
chroma_client = chromadb.PersistentClient(path="chroma_banco_db")
# Asegúrate de que la colección exista antes de correr el server
vector_store = chroma_client.get_or_create_collection("bancolombia")

@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """
    Busca información técnica, comercial o de procesos sobre Bancolombia. 
    Úsala cuando el usuario haga preguntas generales sobre el banco.
    """
    try:
        # Nota: Accedemos a vector_store que está en el scope global
        results = vector_store.query(
            query_texts=[query], 
            n_results=3
        )
        
        # Formateamos la salida para que la IA la entienda fácilmente
        documents = results.get('documents', [[]])[0]
        return "\n\n".join(documents) if documents else "No se encontró información relevante."
        
    except Exception as e:
        return f"Error técnico al consultar la base de datos: {str(e)}"


@mcp.tool()
def get_article_by_url(url: str) -> str:
    """
    Recupera el contenido específico de un artículo o página de Bancolombia mediante su URL.
    Úsala solo si el usuario proporciona una URL específica o pregunta por un enlace concreto.
    """
    try:
        # En Chroma nativo usamos 'where' para filtrar por metadatos
        results = vector_store.get(
            where={"url": url},
            limit=1
        )
        
        documents = results.get('documents', [])
        return documents[0] if documents else "No se encontró ningún artículo con esa URL."
        
    except Exception as e:
        return f"Error al recuperar el artículo por URL: {str(e)}"

@mcp.tool()
def list_categories() -> str: 
    """Usa esta herramienta para listar las categorias de los articulos guardados en la base de datos"""
    return "Categoria"


if __name__ == "__main__":
    mcp.run(transport="stdio")