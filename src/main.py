import asyncio
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from pipeline import BancolombiaPipeline
from crawler import run_crawler

# ── Rutas de datos ─────────────────────────────────────────────────────────────
# En Docker se inyectan DATA_DIR y DB_PATH vía variables de entorno (docker-compose).
# Localmente, si no están definidas, se usan los paths por defecto junto al proyecto.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT)))
INPUT_JSON = str(_DATA_DIR / "resultados_bancolombia.jsonl")
DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "chroma_banco_db"))


# def _extract_sources_from_tool(content: str) -> list[dict]:
#     """Extrae la lista de fuentes desde el JSON estructurado de un ToolMessage.

#     Los tools MCP (search_knowledge_base, get_article_by_url) retornan JSON con
#     el campo "fuentes": [{"titulo": "...", "url": "..."}].
#     Si el contenido no es JSON válido o no tiene fuentes, retorna lista vacía.
#     """
#     try:
#         data = json.loads(content)
#         return data.get("fuentes", [])
#     except (json.JSONDecodeError, TypeError, AttributeError):
#         return []


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


async def _ensure_data_file() -> None:
    """Verifica que el JSONL exista y tenga contenido; si no, ejecuta el crawler."""
    jsonl_path = Path(INPUT_JSON)
    if jsonl_path.exists() and jsonl_path.stat().st_size > 0:
        return

    action = "creando" if not jsonl_path.exists() else "regenerando (archivo vacío)"
    print(f"\n[INFO] Datos no encontrados — {action} la base de conocimiento...")
    print("[INFO] Ejecutando crawler de Bancolombia. Esto puede tardar varios minutos...\n")

    pages = await run_crawler(INPUT_JSON)
    if pages == 0:
        print("[ERROR] El crawler finalizó sin guardar páginas. Verifica la conectividad.")
        sys.exit(1)
    print(f"\n[INFO] Datos listos: {pages} páginas descargadas.\n")


async def run_system():
    load_dotenv()

    # Validar API Key
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: Falta GOOGLE_API_KEY en el archivo .env")
        sys.exit(1)

    # Verificar / generar datos
    await _ensure_data_file()

    # Inicializar la lógica del pipeline
    pipe = BancolombiaPipeline(INPUT_JSON, DB_PATH)

    try:
        # print("--- Fase de Indexación ---")
        # num_chunks = pipe.indexar_datos()
        # print(f"Éxito: {num_chunks} fragmentos listos en la base de datos.")

        print("\n--- Fase de Inicialización del Agente ---")
        agent = await pipe.configurar_agente()
        print("Agente conectado y listo.")

        # Bucle de interacción
        print("\n" + "=" * 40)
        print("Chat de Consultas Bancolombia (escribe 'salir' para finalizar)")
        print("=" * 40)

        config = {"configurable": {"thread_id": "user_session_001"}}

        while True:
            pregunta = input("\nPregunta: ").strip()

            if pregunta.lower() in ["salir", "exit", "quit"]:
                print("Cerrando sistema...")
                break

            if not pregunta:
                continue

            # Acumular fuentes {titulo, url} de los tools por cada pregunta
            source_list: list[dict] = []
            seen_urls: set[str] = set()

            # Ejecución por streaming para mejor feedback visual
            async for event in agent.astream(
                {"messages": [{"role": "user", "content": pregunta}]},
                config=config,
            ):
                # ── Capturar fuentes desde las respuestas JSON de los tools MCP ──
                if "tools" in event:
                    for msg in event["tools"]["messages"]:
                        for fuente in msg.artifact['structured_content']['fuentes']:
                            url = fuente.get("url", "")
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                source_list.append(fuente)

                # ── Capturar y mostrar la respuesta final del modelo ──
                if "model" in event:
                    try:
                        last_msg = event["model"]["messages"][-1]
                        respuesta = _extract_text_from_content(last_msg.content)

                        # Solo imprimir si hay texto real (ignorar tool_calls sin texto)
                        if respuesta.strip():
                            print(f"\nAsistente: {respuesta}")
                    except (KeyError, IndexError, TypeError):
                        continue

            # ── Mostrar fuentes consultadas ──
            if source_list:
                print("\nFuentes consultadas:")
                for fuente in source_list:
                    titulo = fuente.get("titulo", "Sin título")
                    url = fuente.get("url", "")
                    print(f"  - {titulo}: {url}")

    except Exception as e:
        print(f"\n[FALLO CRÍTICO]: {str(e)}")


if __name__ == "__main__":
    try:
        asyncio.run(run_system())
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario.")
