import os
import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver

from database import VectorDBClient

class BancolombiaPipeline:
    def __init__(self, input_file: str, db_dir: str):
        if not input_file or not isinstance(input_file, str):
            raise ValueError("input_file debe ser una ruta de archivo válida y no vacía.")
        if not db_dir or not isinstance(db_dir, str):
            raise ValueError("db_dir debe ser una ruta de directorio válida y no vacía.")
        self.input_file = input_file
        # El pipeline recibe el cliente de DB, no lo crea internamente
        self.db_client = VectorDBClient(db_dir)
        self.vector_store = self.db_client.get_store()

    def indexar_datos(self, force_reindex: bool = False) -> int:
        """Lee el JSONL, filtra registros válidos e indexa en ChromaDB.

        Args:
            force_reindex: Si True, elimina la colección existente y re-indexa todo.

        Returns:
            Número de páginas procesadas e indexadas.

        Raises:
            FileNotFoundError: Si input_file no existe.
        """
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Archivo {self.input_file} no encontrado.")

        # Eliminar colección previa y reinicializar el store limpio
        if force_reindex:
            self.vector_store.delete_collection()
            self.vector_store = self.db_client.get_store()

        total_processed = 0
        batch = []
        batch_size = 50  # Indexamos de a 50 para optimizar llamadas a la DB

        existing_data = self.vector_store.get(include=["metadatas"])
        existing_urls = {m["url"] for m in existing_data["metadatas"] if m and "url" in m}

        # LEER LÍNEA POR LÍNEA (uso eficiente de memoria)
        with open(self.input_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    p = json.loads(line)
                except json.JSONDecodeError as exc:
                    import logging as _logging
                    _logging.getLogger(__name__).warning(
                        f"Línea {line_num} ignorada (JSON inválido): {exc}"
                    )
                    continue

                # Validar campos obligatorios
                url = p.get("url", "").strip()
                titulo = p.get("titulo", "").strip()
                fit_markdown = p.get("fit_markdown", "").strip()

                if not url:
                    continue  # Registro sin URL no es indexable
                if url in existing_urls:
                    continue  # Ya está en la base de datos
                if not fit_markdown:
                    continue  # Sin contenido no tiene valor semántico

                doc = Document(
                    page_content=fit_markdown,
                    metadata={
                        "url": url,
                        "titulo": titulo or "Sin título",
                        "categoria": p.get("categoria", "Otros / Landing") or "Otros / Landing",
                        "scraped_at": p.get("scraped_at", "Fecha no disponible") or "Fecha no disponible",
                    },
                )
                batch.append(doc)

                if len(batch) >= batch_size:
                    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
                    splits = splitter.split_documents(batch)
                    self.vector_store.add_documents(splits)
                    total_processed += len(batch)
                    batch = []
                    print(f"Progreso: {total_processed} páginas indexadas...")

        # Procesar el último lote restante
        if batch:
            splits = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300).split_documents(batch)
            self.vector_store.add_documents(splits)
            total_processed += len(batch)

        return total_processed

    async def configurar_agente(self):
        """Instancia el modelo, herramientas MCP y el Agente."""
        model = init_chat_model("google_genai:gemini-3.1-flash-lite-preview")

        mcp_server_path = str(Path(__file__).resolve().parent / "mcp_server.py")
        client = MultiServerMCPClient(
            {
                "bancolombia_tools": {
                    "transport": "stdio",
                    "command": "python",
                    "args": [mcp_server_path],
                }
            }
        )

        tools = await client.get_tools()

        return create_agent(
            model=model,
            tools=tools,
            middleware=[
                SummarizationMiddleware(
                    model="google_genai:gemini-3.1-flash-lite-preview",
                    trigger=("tokens", 3000),
                    keep=("messages", 10),
                )
            ],
            checkpointer=InMemorySaver(),
        )
