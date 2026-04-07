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
INPUT_JSON = str(PROJECT_ROOT / "resultados_bancolombia.json")
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
def query_agent(agent, question: str, thread_id: str) -> str:
    async def _stream():
        config = {"configurable": {"thread_id": thread_id}}
        full_response = ""
        async for event in agent.astream(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
        ):
            if "agent" in event:
                full_response = event["agent"]["messages"][-1].content
        return full_response

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
            response = query_agent(agent, prompt, st.session_state.thread_id)
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
