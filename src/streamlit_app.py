import sys
import os
import asyncio
import threading
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Asegurar que src/ esté en sys.path para importar pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import BancolombiaPipeline

# ── Rutas absolutas relativas al proyecto ────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = str(PROJECT_ROOT / "resultados_bancolombia.jsonl")
DB_PATH = str(PROJECT_ROOT / "chroma_banco_db")

# ── Event loop en thread daemon ──────────────────────────────────────────────
# Streamlit tiene su propio event loop; no podemos usar asyncio.run().
# Creamos un loop separado en un thread background y enviamos coroutines ahí.
_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


def run_async(coro):
    """Ejecuta una coroutine en el event loop background y bloquea hasta obtener resultado."""
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result()


def _extract_text_from_content(content) -> str:
    """Extrae texto legible del campo content de un AIMessage.

    content puede ser:
      - str: texto directo
      - list[dict]: lista de ContentBlocks (ej. [{'type': 'text', 'text': '...'}])
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


# ── Inicialización única del agente ──────────────────────────────────────────
@st.cache_resource(show_spinner="Inicializando agente (primera vez, puede tardar)...")
def init_agent():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("Falta GOOGLE_API_KEY en el archivo .env")
        st.stop()

    pipe = BancolombiaPipeline(INPUT_JSON, DB_PATH)
    pipe.indexar_datos()
    agent = run_async(pipe.configurar_agente())
    return agent


# ── Consultar agente ─────────────────────────────────────────────────────────
def query_agent(agent, question: str, thread_id: str) -> dict:
    """Ejecuta una pregunta contra el agente y retorna respuesta + fuentes.

    Retorna dict: {"respuesta": str, "fuentes": list[dict]}
    donde cada fuente es {"titulo": str, "url": str}.
    """
    async def _stream():
        config = {"configurable": {"thread_id": thread_id}}
        full_response = ""
        source_list: list[dict] = []
        seen_urls: set[str] = set()

        async for event in agent.astream(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
        ):
            # ── Capturar fuentes desde las respuestas de los tools MCP ──
            if "tools" in event:
                for msg in event["tools"]["messages"]:
                    try:
                        fuentes = msg.artifact["structured_content"]["fuentes"]
                        for fuente in fuentes:
                            url = fuente.get("url", "")
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                source_list.append(fuente)
                    except (KeyError, TypeError, AttributeError):
                        continue

            # ── Capturar la respuesta final del modelo ──
            if "model" in event:
                try:
                    last_msg = event["model"]["messages"][-1]
                    text = _extract_text_from_content(last_msg.content)
                    if text.strip():
                        full_response = text
                except (KeyError, IndexError, TypeError):
                    continue

        return {"respuesta": full_response, "fuentes": source_list}

    return run_async(_stream())


# ── UI ───────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bancolombia Assistant", page_icon="🏦", layout="centered"
)
st.title("🏦 Asistente Bancolombia")
st.caption("Consulta información sobre productos, servicios y más de Bancolombia.")

# Estado de sesión
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit_session_001"

# Sidebar
with st.sidebar:
    st.header("Opciones")
    if st.button("Nueva conversación"):
        st.session_state.messages = []
        st.session_state.thread_id = f"streamlit_session_{id(object())}"
        st.rerun()

# Inicializar agente (cacheado — solo corre la primera vez)
agent = init_agent()

# Renderizar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input del usuario
if prompt := st.chat_input("¿En qué puedo ayudarte?"):
    # Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generar respuesta del agente
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            result = query_agent(agent, prompt, st.session_state.thread_id)
            respuesta = result["respuesta"]
            fuentes = result["fuentes"]

            st.markdown(respuesta)

            if fuentes:
                st.markdown("---")
                st.markdown("**Fuentes consultadas:**")
                for fuente in fuentes:
                    titulo = fuente.get("titulo", "Sin título")
                    url = fuente.get("url", "")
                    st.markdown(f"- [{titulo}]({url})")

    # Guardar en historial incluyendo fuentes como markdown
    content_for_history = respuesta
    if fuentes:
        links = "\n".join(
            f"- [{f.get('titulo', 'Sin título')}]({f.get('url', '')})"
            for f in fuentes
        )
        content_for_history += f"\n\n---\n**Fuentes consultadas:**\n{links}"
    st.session_state.messages.append({"role": "assistant", "content": content_for_history})
