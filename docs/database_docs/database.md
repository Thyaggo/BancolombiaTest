# Base de Datos Vectorial (`database.py`)

## Descripción
Este componente gestiona la conexión a la base de datos vectorial **ChromaDB** y el modelo de **Embeddings**. Es el núcleo de la recuperación semántica del sistema (Retrieval).

## Clase `VectorDBClient`
Implementa un patrón **Singleton Lazy** para asegurar que solo exista una instancia activa de la base de datos y que esta se inicialice solo cuando sea necesario.

### Atributos
-   `db_path`: Ruta física donde se almacenan los archivos de ChromaDB.
-   `EMBEDDINGS_MODEL`: Modelo multilingüe optimizado para el español (`paraphrase-multilingual-MiniLM-L12-v2`).
-   `COLLECTION_NAME`: El nombre de la colección principal (`bancolombia_docs`).

### Métodos Principales

#### `get_store()`
Retorna la instancia de `Chroma`. Si no existe aún, la crea utilizando los parámetros configurados. Este método permite que otros componentes realicen operaciones de búsqueda e indexación.

#### `get_embeddings_name()`
Retorna el identificador del modelo de embeddings utilizado. Este dato se usa para fines informativos y estadísticas del sistema.

## Decisiones Técnicas
-   **Modelo de Embeddings:** Se seleccionó un modelo de Sentence Transformers (`HuggingFaceEmbeddings`) que produce vectores de 384 dimensiones. Este modelo es altamente eficiente y está optimizado para capturar el significado semántico en múltiples idiomas, incluyendo el español de forma robusta.
-   **Persistencia:** ChromaDB se utiliza en modo cliente/servidor interno con almacenamiento en disco, lo que permite que el conocimiento persista después de reiniciar la aplicación o el contenedor Docker.
-   **Validación de Datos:** El constructor valida rigurosamente que la ruta proporcionada sea una cadena no vacía antes de proceder a la inicialización.
