import streamlit as st
import mysql.connector
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import chromadb
from chromadb.utils import embedding_functions
import os
import google.generativeai as genai
from typing import List

# --- Streamlit UI Configuration (MUST BE FIRST ST. COMMANDS) ---
st.set_page_config(layout="wide")
st.title("RAG Pipeline Frontend")

# --- Configuration ---
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'root_password')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'rag_db')

CHROMADB_HOST = os.getenv('CHROMADB_HOST', 'localhost')
CHROMADB_PORT = int(os.getenv('CHROMADB_PORT', 8000))
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
COLLECTION_NAME = 'rag_documents' # Should match processor


model = genai.GenerativeModel("models/gemini-2.0-flash")


def build_prompt(query: str, context: List[str]) -> str:
    """
    Builds a prompt for the LLM. #

    This function builds a prompt for the LLM. It takes the original query,
    and the returned context, and asks the model to answer the question based only
    on what's in the context, not what's in its weights.

    Args:
    query (str): The original query.
    context (List[str]): The context of the query, returned by embedding search.

    Returns:
    A prompt for the LLM (str).
    """

    base_prompt = {
        "content": "I am going to ask you a question, which I would like you to answer"
        " based only on the provided context, and not any other information."
        " If there is not enough information in the context to answer the question,"
        ' say "I am not sure", then try to make a guess.'
        " Break your answer up into nicely readable paragraphs.",
    }
    user_prompt = {
        "content": f" The question is '{query}'. Here is all the context you have:"
        f'{(" ").join(context)}',
    }

    # combine the prompts to output a single prompt string
    system = f"{base_prompt['content']} {user_prompt['content']}"

    return system


def get_gemini_response(query: str, context: List[str]) -> str:
    """
    Queries the Gemini API to get a response to the question.

    Args:
    query (str): The original query.
    context (List[str]): The context of the query, returned by embedding search.

    Returns:
    A response to the question.
    """

    response = model.generate_content(build_prompt(query, context))

    return response.text

# --- Initialize Gemini Embedding Model ---
if not GEMINI_API_KEY:
    st.error("Error: GEMINI_API_KEY environment variable not set. Please set it in Dockerfile or docker-compose.yml.")
    st.stop() # Stop execution if API key is missing
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
                st.error(f"Error generating embedding for text: '{text[:50]}...' - {e}")
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


# --- Initialize ChromaDB Client ---
try:
    chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    st.success(f"Connected to ChromaDB at {CHROMADB_HOST}:{CHROMADB_PORT}")
except Exception as e:
    st.error(f"Error connecting to ChromaDB: {e}")
    st.stop() # Stop execution if ChromaDB connection fails

# Get or create the collection
try:
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=gemini_ef # Ensure the same embedding function is used for querying
    )
    st.success(f"ChromaDB collection '{COLLECTION_NAME}' ready for RAG.")
except Exception as e:
    st.error(f"Error accessing ChromaDB collection '{COLLECTION_NAME}': {e}")
    st.info("Ensure the rag_processor has started and populated the collection.")
    st.stop() # Stop execution if collection access fails

# Peek the collection
try:
    peek = collection.peek()
    st.success(f"ChromaDB collection peek  '{COLLECTION_NAME}' '{peek}' ready for RAG.")
except Exception as e:
    st.error(f"Error accessing ChromaDB collection '{COLLECTION_NAME}': {e}")
    st.info("Ensure the rag_processor has started and populated the collection.")
    st.stop() # Stop execution if collection access fails

# Function to get documents from MySQL
@st.cache_data(ttl=60) # Cache MySQL data for 60 seconds
def get_mysql_documents():
    conn = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, content FROM documents")
        documents = cursor.fetchall()
        return documents
    except mysql.connector.Error as err:
        st.error(f"Error connecting to MySQL: {err}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- Display MySQL Documents ---
st.header("MySQL Documents")
if st.button("Refresh MySQL Documents"):
    st.session_state['mysql_documents'] = get_mysql_documents()

if 'mysql_documents' not in st.session_state:
    st.session_state['mysql_documents'] = get_mysql_documents()

if st.session_state['mysql_documents']:
    for doc in st.session_state['mysql_documents']:
        st.write(f"**ID:** {doc['id']}, **Title:** {doc['title']}")
        st.code(doc['content'][:200] + "...")
else:
    st.info("No documents found in MySQL.")

# --- Add New Document to MySQL (for testing CDC) ---
st.header("Add New Document to MySQL")
with st.form("new_document_form"):
    new_title = st.text_input("Title")
    new_content = st.text_area("Content")
    submit_button = st.form_submit_button("Add Document to MySQL")

    if submit_button:
        conn = None
        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            cursor = conn.cursor()
            query = "INSERT INTO documents (title, content) VALUES (%s, %s)"
            cursor.execute(query, (new_title, new_content))
            conn.commit()
            st.success(f"Document '{new_title}' added to MySQL. Changes will propagate via CDC.")
            st.session_state['mysql_documents'] = get_mysql_documents() # Refresh displayed docs
        except mysql.connector.Error as err:
            st.error(f"Error adding document to MySQL: {err}")
        finally:
            if conn and conn.is_connected():
                conn.close()

# --- RAG Query Section (now using Gemini embeddings and Gemini Pro for generation) ---
st.header("Ask a question (RAG with ChromaDB and Gemini)")
query_text = st.text_input("Enter your query:", "What is Sun Tzu's book about?")

if st.button("Get AI Answer"): # Changed button text for clarity
    if query_text:
        st.subheader(f"Query: '{query_text}'")
        st.write("Searching ChromaDB for relevant documents...")

        try:
            results = collection.query(
                query_texts=[query_text],
                n_results=5, # Increased results to provide more context to the LLM
                include=['documents', 'metadatas', 'distances']
            )

            retrieved_documents = results['documents'][0] if results and results['documents'] else []
            retrieved_metadatas = results['metadatas'][0] if results and results['metadatas'] else []
            retrieved_distances = results['distances'][0] if results and results['distances'] else []

            if retrieved_documents:
                # Get the AI-generated response from Gemini Pro
                ai_response = get_gemini_response(query_text, retrieved_documents)
                st.subheader("AI-Generated Answer:")
                st.write(ai_response)
                st.markdown("---")

                st.subheader("Source Documents (from ChromaDB):")
                for i in range(len(retrieved_documents)):
                    doc = retrieved_documents[i]
                    meta = retrieved_metadatas[i]
                    dist = retrieved_distances[i]
                    st.write(f"**ID:** {meta.get('id')}, **Title:** '{meta.get('title')}'")
                    st.write(f"**Content:** {doc[:200]}...")
                    st.write(f"**Distance:** {dist:.4f}")
                    st.markdown("---")
            else:
                st.info("No relevant documents found in ChromaDB for this query. Cannot generate an AI answer.")
        except Exception as e:
            st.error(f"Error during RAG process: {e}")
            st.info("Ensure rag_processor is running and ChromaDB collection is populated.")
    else:
        st.warning("Please enter a query.")







# --- RAG Query Section (now using Gemini embeddings) ---
#st.header("Ask a question (RAG with ChromaDB and Gemini)")
#query_text = st.text_input("Enter your query:", "What is Sun Tzu's book about?")
#
#if st.button("Get Relevant Information"):
#    if query_text:
#        st.write(f"Querying ChromaDB with Gemini embeddings for: '{query_text}'")
#        try:
#            results = collection.query(
#                query_texts=[query_text],
#                n_results=2,
#                include=['documents', 'metadatas', 'distances']
#            )
#
#	    response = get_gemini_response(query, results["documents"][0]) 
#
#            if results and results['documents'] and results['documents'][0]:
#                st.subheader("Retrieved Documents:")
#                for i in range(len(results['documents'][0])):
#                    doc = results['documents'][0][i]
#                    meta = results['metadatas'][0][i]
#                    dist = results['distances'][0][i]
#                    st.write(f"**ID:** {meta.get('id')}, **Title:** '{meta.get('title')}'")
#                    st.write(f"**Content:** {doc[:200]}...")
#                    st.write(f"**Distance:** {dist:.4f}")
#                    st.markdown("---")
#            else:
#                st.info("No relevant documents found in ChromaDB or an error occurred during retrieval.")
#        except Exception as e:
#            st.error(f"Error during RAG query: {e}")
#            st.info("Ensure rag_processor is running and ChromaDB collection is populated.")
#    else:
##        st.warning("Please enter a query.")
