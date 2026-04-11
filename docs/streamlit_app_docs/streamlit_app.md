# Interfaz Web (`streamlit_app.py`)

## Descripción
`streamlit_app.py` proporciona una interfaz gráfica moderna y responsiva para el Asistente Bancolombia. Utiliza el framework **Streamlit** para crear una experiencia de chat web interactiva y persistente.

## Características Principales

### Gestión de Event Loop Asíncrono
Streamlit opera bajo un modelo de ejecución propio que puede entrar en conflicto con la naturaleza asíncrona (`asyncio`) de LangChain y MCP. Para solucionar esto:
-   **Loop en Thread Background:** Se crea un `asyncio event loop` independiente en un hilo separado (daemon thread).
-   **`run_async(coro)`:** Función puente que envía tareas al hilo de fondo y bloquea el hilo de Streamlit hasta obtener el resultado, permitiendo integrar código asíncrono en una UI síncrona.

### Persistencia del Agente
Utiliza el decorador `@st.cache_resource` para inicializar el pipeline y el agente una única vez al inicio de la aplicación. Esto optimiza el rendimiento, ya que no es necesario volver a cargar los modelos de embeddings o establecer la conexión MCP en cada interacción del usuario.

### Historial de Conversación
Gestiona el estado de la sesión (`st.session_state`) para almacenar y renderizar los mensajes intercambiados. Las fuentes consultadas se guardan directamente como parte del contenido del mensaje del asistente en formato Markdown para que persistan correctamente al recargar la página o enviar nuevas preguntas.

## Flujo de Usuario

1.  **Carga Inicial:** Se verifica la existencia de datos y se inicializa el agente (mostrando spinners de progreso).
2.  **Interfaz de Chat:** Presenta una caja de texto (`st.chat_input`) donde el usuario formula su consulta.
3.  **Procesamiento:** El sistema envía la pregunta al agente a través del event loop de fondo, capturando tanto la respuesta textual como las fuentes estructuradas desde los mensajes de las herramientas MCP.
4.  **Respuesta:** Renderiza la respuesta del asistente y despliega una lista de enlaces interactivos a las fuentes de Bancolombia consultadas.

## Decisiones de Diseño
-   **`thread_id` dinámico:** Se asigna un identificador de hilo único por cada sesión del navegador, lo que permite que el sistema de memoria (middleware de resumen) aísle el contexto de cada usuario.
-   **Nueva Conversación:** Botón en la barra lateral (sidebar) para resetear el historial y el `thread_id`, permitiendo iniciar un hilo de conversación desde cero.
-   **Auto-Crawling Visual:** Si los datos no están presentes, se utiliza `st.status()` para mostrar visualmente el progreso del crawler antes de permitir el acceso al chat.
