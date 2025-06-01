# 🚀 Real-time RAG Pipeline with MySQL CDC, ChromaDB, and Gemini AI 🚀

This project presents a robust and dynamic Retrieval Augmented Generation (RAG) pipeline designed to provide real-time, AI-powered answers based on a continuously updated knowledge base. It showcases a powerful integration of MySQL's Change Data Capture (CDC) via Debezium and Kafka to maintain a fresh vector store in ChromaDB, which then leverages Google's cutting-edge Gemini AI API for both intelligent embeddings and generative responses. An interactive Streamlit frontend allows users to easily query the system and see the RAG capabilities in action.

![RAG CDC Pipeline](https://github.com/mehuljn/rag_cdc_pipeline/blob/main/image.jpg?raw=true)

---

## ✨ Features

* **Real-time Knowledge Base:** Automatically updates the ChromaDB vector store with changes detected in the MySQL database using **Debezium** for Change Data Capture (CDC) and **Kafka** for streaming events.
* **Gemini AI Powered:** Utilizes the **Google Gemini AI API** (`embedding-001` model) for generating state-of-the-art semantic embeddings for documents and queries. It also uses the `gemini-pro` generative model to synthesize natural language answers from retrieved context.
* **Retrieval Augmented Generation (RAG):** Combines efficient information retrieval from a vector database with a large language model (LLM) to provide accurate, context-aware, and up-to-date responses.
* **Interactive Web Frontend:** A user-friendly **Streamlit** application provides an intuitive interface to view current documents in MySQL, add new data (triggering CDC), and query the RAG system interactively.
* **Modular & Containerized:** The entire pipeline is orchestrated using **Docker Compose**, with each component running as a separate service for scalability, isolation, and easy deployment.
* **Built with Gemini AI Prompts and verified with human testing! :)** This project's iterative development was significantly guided by prompt engineering with Gemini itself, with human experts providing rigorous validation and refinement.

---

## 🏛️ Architecture Overview

The pipeline operates in a continuous loop:

1.  **MySQL:** The primary data source, containing documents (e.g., articles, knowledge base entries).
2.  **Debezium Connector:** Continuously monitors the MySQL database's transaction log (binlog) for changes (inserts, updates, deletes) on the `documents` table.
3.  **Kafka:** Debezium streams these change events as messages to a dedicated Kafka topic.
4.  **RAG Processor:** A Python application that acts as a Kafka consumer. It subscribes to the Debezium topic, receives change events, uses **Gemini AI** to generate embeddings for the document content, and then performs corresponding upsert or delete operations in **ChromaDB**.
5.  **ChromaDB:** The open-source vector database that stores the vectorized embeddings of your documents along with their metadata.
6.  **RAG Frontend (Streamlit):** A web application that allows users to:
    * View current documents in MySQL.
    * Add new documents (which trigger the CDC process).
    * Enter natural language queries.
    * The frontend uses **Gemini AI** to embed the user's query, searches **ChromaDB** for relevant documents, and then passes these retrieved documents as context to the **Gemini Pro** generative model to synthesize a final answer.

+-----------+       +-----------+       +-------+       +---------------+      +----------+      +----------------+
|  MySQL    |  <--  |  Debezium |  -->  | Kafka |  -->  | RAG Processor |  --> | ChromaDB | <--  | RAG Frontend   |
| (Documents)|       |  (CDC)    |       |       |       | (Gemini Embed) |      | (Vector  |      | (Gemini Query, |
+-----------+       +-----------+       +-------+       +---------------+      |  Store)  |      |  Gemini Gen)   |
+----------+      +----------------+

---

## ⚙️ Technologies Used

* **Database:** MySQL 8.0
* **CDC Platform:** Debezium Connect 2.4
* **Message Broker:** Apache Kafka 7.4.0 (via Confluent Platform)
* **Vector Database:** ChromaDB 0.5.0
* **AI Models:** Google Gemini AI API (`embedding-001`, `gemini-pro`)
* **Programming Language:** Python 3.10
* **Web Framework:** Streamlit 1.22.0
* **Containerization:** Docker & Docker Compose
* **Python Libraries:** `mysql-connector-python`, `kafka-python`, `chromadb`, `google-generative-ai`, `streamlit`, `numpy`

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

* **Docker Desktop:** This includes Docker Engine and Docker Compose, essential for running our containerized services.
    * [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
* **Google Gemini AI API Key:** You'll need an active API key to utilize Gemini's embedding and generative capabilities.
    * [Get your Gemini API Key](https://ai.google.dev/)

---

## 🚀 Setup & Installation

Follow these steps to get the RAG pipeline up and running on your local machine:

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/mehuljn/rag_cdc_pipeline.git](https://github.com/mehuljn/rag_cdc_pipeline.git)
    cd rag_cdc_pipeline # Navigate into the cloned directory
    ```

2.  **Set Your Gemini API Key:**
    The `rag_processor` and `rag_frontend` services require your `GEMINI_API_KEY`. It's recommended to set it as an environment variable in your shell.

    ```bash
    export GEMINI_API_KEY="YOUR_ACTUAL_GOOGLE_GEMINI_API_KEY_HERE"
    ```
    *Replace `"YOUR_ACTUAL_GOOGLE_GEMINI_API_KEY_HERE"` with your real API key.* This variable will be automatically passed to the Docker containers via `docker-compose.yml`.

3.  **Build and Run the Services:**
    From the root directory of the repository (`rag_cdc_pipeline/`), execute the following command:

    ```bash
    docker compose up --build -d
    ```
    * `--build`: This forces Docker Compose to rebuild the `rag_processor` and `rag_frontend` images, ensuring all dependencies (including specific `chromadb` and `numpy` versions) are correctly installed.
    * `-d`: Runs the containers in detached mode (in the background).

    **Initial Setup Time:** Please allow a few minutes for all services to start up. Kafka, Debezium, and MySQL need time to initialize. The `debezium_connector_configurator` service will automatically set up the MySQL Debezium connector for `rag_db.documents`. Restart this container with docker compose restart debezium_connector_configurator and recheck logs.

---

## 💡 Usage

Once all services are up and running, you can interact with the RAG pipeline through the Streamlit frontend.

1.  **Access the Streamlit Frontend:**
    Open your web browser and navigate to:
    ```
    http://localhost:8501
    ```

2.  **Explore MySQL Documents:**
    The "MySQL Documents" section will display the initial data loaded from `mysql/init.sql`. You can click "Refresh MySQL Documents" to reload the view.

3.  **Add New Documents (Test CDC):**
    Use the "Add New Document to MySQL" form to add new entries to your database.
    * Enter a `Title` and `Content`.
    * Click "Add Document to MySQL".
    * You'll see a success message. Behind the scenes, Debezium captures this change, streams it to Kafka, and your `rag_processor` will consume it, generate embeddings, and update ChromaDB in near real-time.

4.  **Ask a Question (RAG with Gemini):**
    In the "Ask a question (RAG with ChromaDB and Gemini)" section:
    * Enter your query (e.g., "What is Sun Tzu's book about?", "Tell me about an astronaut on Mars?").
    * Click "Get AI Answer".

    The application will:
    * Embed your query using **Gemini AI**.
    * Search ChromaDB for the most relevant document chunks.
    * Pass these retrieved chunks as context to the **Gemini Pro** generative model.
    * Display the AI-generated answer.
    * Show the source documents that were used to formulate the answer.

    Try adding a new document and then immediately querying for its content to see the real-time RAG updates in action!

