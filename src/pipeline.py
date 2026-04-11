import os
import json
import sys
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

# Configuración vía Variables de Entorno
DEFAULT_BATCH_SIZE = int(os.getenv("INDEX_BATCH_SIZE", "50"))
DEFAULT_CHUNK_SIZE = int(os.getenv("INDEX_CHUNK_SIZE", "1500"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("INDEX_CHUNK_OVERLAP", "300"))
LLM_MODEL_NAME = os.getenv("LLM_MODEL", "google_genai:gemini-3.1-flash-lite-preview")
HISTORY_SUMMARIZATION_THRESHOLD = int(os.getenv("HISTORY_THRESHOLD", "3000"))
HISTORY_KEEP_COUNT = int(os.getenv("HISTORY_KEEP", "10"))

SYSTEM_PROMPT = os.getenv(
    "AGENT_SYSTEM_PROMPT",
    """Eres un asistente especializado exclusivamente en el Grupo Bancolombia.

Tu base de conocimiento contiene información extraída del sitio oficial de Bancolombia \
sobre productos, servicios, educación financiera, presencia internacional e información \
institucional.

Reglas que debes seguir siempre:
1. Solo responde preguntas relacionadas con Bancolombia: productos (cuentas, créditos, \
inversiones, seguros), servicios digitales, información corporativa o educación financiera.
2. Para cualquier pregunta sobre Bancolombia, usa SIEMPRE la herramienta \
search_knowledge_base antes de responder. No inventes información.
3. Cita las fuentes (URLs) que te retorne la herramienta en cada respuesta.
4. Si el usuario pregunta sobre un tema ajeno a Bancolombia (política, deportes, \
recetas, etc.), responde educadamente que solo puedes ayudar con temas relacionados \
con Bancolombia y ofrece orientarlo sobre los servicios del banco.
5. Si la base de conocimiento no contiene información suficiente para responder, \
dilo claramente en lugar de inventar datos.""",
)

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
        """Lee el JSONL, filtra registros válidos e indexa en ChromaDB de forma eficiente."""
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Archivo {self.input_file} no encontrado.")

        if force_reindex:
            self.vector_store.delete_collection()
            self.vector_store = self.db_client.get_store()

        total_processed = 0
        batch = []
        batch_size = DEFAULT_BATCH_SIZE

        # LEER LÍNEA POR LÍNEA
        with open(self.input_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line: continue

                try:
                    p = json.loads(line)
                except json.JSONDecodeError: continue

                url = p.get("url", "").strip()
                fit_markdown = p.get("fit_markdown", "").strip()

                if not url or not fit_markdown:
                    continue
                
                # Deduplicación quirúrgica: Consultar solo por esta URL (O(1) en RAM)
                res = self.vector_store.get(where={"url": url}, limit=1)
                if res["ids"]:
                    continue

                doc = Document(
                    page_content=fit_markdown,
                    metadata={
                        "url": url,
                        "titulo": p.get("titulo", "Sin título") or "Sin título",
                        "categoria": p.get("categoria", "Otros / Landing") or "Otros / Landing",
                        "scraped_at": p.get("scraped_at", "No disponible") or "No disponible",
                    },
                )
                batch.append(doc)

                if len(batch) >= batch_size:
                    self._process_batch(batch)
                    total_processed += len(batch)
                    batch = []
                    print(f"Progreso: {total_processed} páginas indexadas...")

        if batch:
            self._process_batch(batch)
            total_processed += len(batch)

        return total_processed

    def _process_batch(self, batch):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP
        )
        splits = splitter.split_documents(batch)
        self.vector_store.add_documents(splits)

    async def configurar_agente(self):
        """Instancia el modelo, herramientas MCP y el Agente."""
        model = init_chat_model(LLM_MODEL_NAME)

        mcp_server_path = str(Path(__file__).resolve().parent / "mcp_server.py")
        client = MultiServerMCPClient(
            {
                "bancolombia_tools": {
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [mcp_server_path],
                }
            }
        )

        tools = await client.get_tools()

        return create_agent(
            model=model,
            tools=tools,
            prompt=SYSTEM_PROMPT,
            middleware=[
                SummarizationMiddleware(
                    model=LLM_MODEL_NAME,
                    trigger=("tokens", HISTORY_SUMMARIZATION_THRESHOLD),
                    keep=("messages", HISTORY_KEEP_COUNT),
                )
            ],
            checkpointer=InMemorySaver(),
        )
