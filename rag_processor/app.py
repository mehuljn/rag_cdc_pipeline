# rag_processor/app.py
import os
import json
import time
from kafka import KafkaConsumer

__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai

__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
CHROMADB_HOST = os.getenv('CHROMADB_HOST', 'localhost')
CHROMADB_PORT = int(os.getenv('CHROMADB_PORT', 8000))
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DEBEZIUM_TOPIC = 'mysql_server.rag_db.documents' # This topic name is derived from database.server.name.database_name.table_name

COLLECTION_NAME = 'rag_documents'

# --- Initialize Gemini Embedding Model ---
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)
genai.configure(api_key=GEMINI_API_KEY)

# Custom embedding function for ChromaDB using Gemini
class GeminiEmbeddingFunction1(embedding_functions.EmbeddingFunction):
    def __call__(self, texts):
        model = genai.get_model('embedding-001')
        embeddings = []
        for text in texts:
            try:
                result = model.embed_content(model="models/embedding-001", content=text)
                embeddings.append(result['embedding'])
            except Exception as e:
                print(f"Error generating embedding for text: '{text[:50]}...' - {e}")
                embeddings.append([0.0] * 768) # Return a zero vector or handle error appropriately
        return embeddings

# This updated class should be used in both rag_processor/app.py and rag_frontend/app.py

class GeminiEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __call__(self, texts):
        embeddings = []
        for text in texts:
            try:
                # Correct way to call embed_content
                result = genai.embed_content(model="models/embedding-001", content=text)
                embeddings.append(result['embedding'])
            except Exception as e:
                # Removed the 'model' variable from the error message as it's not used now
                print(f"Error generating embedding for text: '{text[:50]}...' - {e}")
                # For Streamlit frontend, consider using st.error if relevant
                # if 'streamlit' in globals():
                #     st.error(f"Error generating embedding for text: '{text[:50]}...' - {e}")
                embeddings.append([0.0] * 768) # Return a zero vector or handle error appropriately
        return embeddings

gemini_ef = GeminiEmbeddingFunction()

#gemini_ef = embedding_functions.GoogleGenerativeAIEmbeddingFunction(
#    api_key=GEMINI_API_KEY, task_type="RETRIEVAL_DOCUMENT"
#)


# --- Initialize ChromaDB Client ---
try:
    chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    print(f"Connected to ChromaDB at {CHROMADB_HOST}:{CHROMADB_PORT}")
except Exception as e:
    print(f"Error connecting to ChromaDB: {e}")
    exit(1)

# Get or create the collection
try:
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=gemini_ef # Use the custom Gemini embedding function
    )
    print(f"ChromaDB collection '{COLLECTION_NAME}' ready.")
except Exception as e:
    print(f"Error getting/creating ChromaDB collection: {e}")
    exit(1)


# --- Kafka Consumer Setup ---
consumer = None
while consumer is None:
    try:
        consumer = KafkaConsumer(
            DEBEZIUM_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest', # Start reading from the beginning if no offset is stored
            enable_auto_commit=True,
            group_id='rag-processor-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print(f"Kafka consumer connected to topic: {DEBEZIUM_TOPIC}")
    except Exception as e:
        print(f"Waiting for Kafka to be ready... {e}")
        time.sleep(5) # Wait before retrying

# --- CDC Event Processing Loop ---
print("Listening for MySQL CDC events...")
for message in consumer:
    try:
        payload = message.value.get('payload')
        if not payload:
            print("Skipping message with no payload.")
            continue

        op = payload.get('op') # Operation type: c (create), u (update), d (delete), r (read/snapshot)

        if op == 'c' or op == 'r': # Create or initial snapshot read
            document_data = payload.get('after')
            if document_data:
                doc_id = str(document_data['id'])
                doc_content = document_data['content']
                doc_title = document_data['title']
                print(f"Processing CREATE/READ event for ID: {doc_id}, Title: '{doc_title}'")

                # Add/Update document in ChromaDB
                collection.upsert(
                    documents=[doc_content],
                    metadatas=[{"id": doc_id, "title": doc_title}],
                    ids=[doc_id]
                )
                print(f"Upserted document ID {doc_id} to ChromaDB.")

        elif op == 'u': # Update
            document_data_before = payload.get('before')
            document_data_after = payload.get('after')
            if document_data_before and document_data_after:
                doc_id = str(document_data_after['id'])
                doc_content = document_data_after['content']
                doc_title = document_data_after['title']
                print(f"Processing UPDATE event for ID: {doc_id}, Title: '{doc_title}'")

                # Update document in ChromaDB (upsert handles this)
                collection.upsert(
                    documents=[doc_content],
                    metadatas=[{"id": doc_id, "title": doc_title}],
                    ids=[doc_id]
                )
                print(f"Upserted (updated) document ID {doc_id} to ChromaDB.")

        elif op == 'd': # Delete
            document_data = payload.get('before')
            if document_data:
                doc_id = str(document_data['id'])
                print(f"Processing DELETE event for ID: {doc_id}")

                # Delete document from ChromaDB
                collection.delete(ids=[doc_id])
                print(f"Deleted document ID {doc_id} from ChromaDB.")

        else:
            print(f"Unhandled operation type: {op}")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Kafka message: {e}")
        print(f"Raw message value: {message.value}")
    except Exception as e:
        print(f"An error occurred during message processing: {e}")
        import traceback
        traceback.print_exc()

# --- Simple RAG Query Function (for demonstration) ---
def query_rag(query_text, n_results=2):
    print(f"\n--- Performing RAG Query: '{query_text}' ---")
    try:
        # ChromaDB will use the configured GeminiEmbeddingFunction to embed the query
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        if results and results['documents']:
            print("Retrieved Documents:")
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                meta = results['metadatas'][0][i]
                dist = results['distances'][0][i]
                print(f"  ID: {meta.get('id')}, Title: '{meta.get('title')}'")
                print(f"  Content: '{doc[:100]}...'")
                print(f"  Distance: {dist:.4f}\n")
        else:
            print("No relevant documents found.")
    except Exception as e:
        print(f"Error during RAG query: {e}")

# You can uncomment and use this for manual testing after the pipeline is running
# time.sleep(30) # Give some time for initial data to be processed
# query_rag("What is Sun Tzu's book about?")
# query_rag("Tell me about a dystopian novel.")
# query_rag("Who wrote Sapiens?")
