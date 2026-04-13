import asyncio
import os
import threading
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from crawler import run_crawler
from pipeline import BancolombiaPipeline

# ── Rutas de datos ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = Path(os.getenv("DATA_DIR") or str(PROJECT_ROOT))
INPUT_JSON = os.getenv("CRAWLER_OUTPUT_FILE") or str(_DATA_DIR / "resultados_bancolombia.jsonl")
DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "chroma_banco_db"))
STREAMLIT_SESSION_PREFIX = os.getenv("STREAMLIT_SESSION_PREFIX", "streamlit_session")

# ── Event loop en thread daemon ──────────────────────────────────────────────
# Streamlit re-ejecuta el script en cada rerender, por lo que cualquier
# variable de módulo (como _loop) se recrea en cada pasada. Usar
# @st.cache_resource garantiza que el loop se cree UNA SOLA VEZ por
# lifetime de la app, evitando el "Future attached to a different loop"
# que ocurre cuando el agente (también cacheado) usa sesiones aiohttp
# ligadas al loop original mientras run_async ya apunta a uno nuevo.
@st.cache_resource
def _get_event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return loop


def run_async(coro):
    """Ejecuta una coroutine en el event loop background y bloquea hasta obtener resultado."""
    return asyncio.run_coroutine_threadsafe(coro, _get_event_loop()).result()


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


def _ensure_data_file() -> bool:
    """Verifica que el JSONL exista y tenga contenido; si no, ejecuta el crawler.

    Returns:
        True si el archivo está listo para usarse, False si el crawler falló.
    """
    jsonl_path = Path(INPUT_JSON)

    if jsonl_path.is_file() and jsonl_path.stat().st_size > 0:
        return True

    if jsonl_path.is_dir():
        st.error(
            f"La ruta '{INPUT_JSON}' apunta a un directorio, no a un archivo JSONL. "
            "Revisa DATA_DIR y CRAWLER_OUTPUT_FILE en tu archivo .env."
        )
        return False

    # Archivo ausente o vacío → lanzar crawler
    action = "creando" if not jsonl_path.exists() else "regenerando (archivo vacío)"
    with st.status(f"Datos no encontrados — {action} la base de conocimiento...", expanded=True) as status:
        st.write("Ejecutando crawler de Bancolombia. Esto puede tardar varios minutos...")
        try:
            pages = run_async(run_crawler(INPUT_JSON))
            if pages == 0:
                status.update(label="El crawler no obtuvo páginas.", state="error")
                st.error("El crawler finalizó sin guardar páginas. Verifica la conectividad.")
                return False
            status.update(
                label=f"Datos listos: {pages} páginas descargadas.",
                state="complete",
            )
            return True
        except Exception as exc:
            status.update(label="Error durante el crawler.", state="error")
            st.error(f"El crawler falló: {exc}")
            return False


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
    st.session_state.thread_id = str(uuid.uuid4())

# Sidebar
with st.sidebar:
    st.header("Opciones")
    if st.button("Nueva conversación"):
        st.session_state.messages = []
        # Generamos un nuevo UUID para resetear el hilo en el agente
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

# Verificar datos antes de inicializar el agente
if not _ensure_data_file():
    st.stop()

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

            st.markdown(respuesta)

    # Guardar en historial incluyendo fuentes como markdown
    content_for_history = respuesta
    # if fuentes:
    #     links = "\n".join(
    #         f"- [{f.get('titulo', 'Sin título')}]({f.get('url', '')})"
    #         for f in fuentes
    #     )
    #     content_for_history += f"\n\n---\n**Fuentes consultadas:**\n{links}"
    st.session_state.messages.append({"role": "assistant", "content": content_for_history})
