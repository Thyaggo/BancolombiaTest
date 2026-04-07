import asyncio
import sys
import os
from dotenv import load_dotenv
from pipeline import BancolombiaPipeline

# Configuración de constantes
INPUT_JSON = "resultados_bancolombia.json"
DB_PATH = "./chroma_banco_db"

async def run_system():
    load_dotenv()
    
    # Validar API Key
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: Falta GOOGLE_API_KEY en el archivo .env")
        sys.exit(1)

    # Inicializar la lógica del pipeline
    pipe = BancolombiaPipeline(INPUT_JSON, DB_PATH)

    try:
        print("--- Fase de Indexación ---")
        num_chunks = pipe.indexar_datos()
        print(f"Éxito: {num_chunks} fragmentos listos en la base de datos.")

        print("\n--- Fase de Inicialización del Agente ---")
        agent = await pipe.configurar_agente()
        print("Agente conectado y listo.")

        # Bucle de interacción
        print("\n" + "="*40)
        print("Chat de Consultas Bancolombia (escribe 'salir' para finalizar)")
        print("="*40)

        config = {"configurable": {"thread_id": "user_session_001"}}

        while True:
            pregunta = input("\nPregunta: ").strip()
            
            if pregunta.lower() in ["salir", "exit", "quit"]:
                print("Cerrando sistema...")
                break
            
            if not pregunta:
                continue

            # Ejecución por streaming para mejor feedback visual
            async for event in agent.astream(
                {"messages": [{"role": "user", "content": pregunta}]}, 
                config=config
            ):
                if "agent" in event:
                    respuesta = event['agent']['messages'][-1].content
                    print(f"\nAsistente: {respuesta}")

    except Exception as e:
        print(f"\n[FALLO CRÍTICO]: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(run_system())
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario.")