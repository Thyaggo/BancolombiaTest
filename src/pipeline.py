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


class BancolombiaPipeline:
    def __init__(self, input_file, db_dir):
        self.input_file = input_file
        self.db_dir = db_dir
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

    def indexar_datos(self):
        """Carga el JSON y lo vectoriza en ChromaDB."""
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Archivo {self.input_file} no encontrado.")

        with open(self.input_file, "r", encoding="utf-8") as f:
            datos = json.load(f)

        docs = [
            Document(
                page_content=p["raw_markdown"],
                metadata={
                    "url": p["url"],
                    "titulo": p["titulo"],
                    "categoria": p.get("categoria", "Otros / Landing"),
                },
            )
            for p in datos.get("pages", [])
            if p.get("raw_markdown")
        ]

        splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
        splits = splitter.split_documents(docs)

        # Re-indexación limpia
        vector_store = Chroma(
            collection_name="bancolombia_docs",
            embedding_function=self.embeddings,
            persist_directory=self.db_dir,
        )
        vector_store.delete_collection()

        vector_store = Chroma(
            collection_name="bancolombia_docs",
            embedding_function=self.embeddings,
            persist_directory=self.db_dir,
        )
        vector_store.add_documents(splits)
        return len(splits)

    async def configurar_agente(self):
        """Instancia el modelo, herramientas MCP y el Agente."""
        model = init_chat_model("google_genai:gemini-3-flash-preview")

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
                    model="google_genai:gemini-3-flash-preview",
                    trigger=("tokens", 3000),
                    keep=("messages", 10),
                )
            ],
            checkpointer=InMemorySaver(),
        )
