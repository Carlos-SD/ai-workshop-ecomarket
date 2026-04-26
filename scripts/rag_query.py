import os
import sys
from pathlib import Path
from datetime import datetime

# LangChain imports
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from dotenv import load_dotenv


# Global configuration
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "rag_query_prompt.txt"
LOGS_DIR = PROJECT_ROOT / "logs"

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
COLLECTION_NAME = "ecomarket_knowledge_base"

# Similarity distance threshold for fallback detection.
# In ChromaDB with normalized embeddings, lower distance = more similar.
# If the best score exceeds this value, the query falls back.
RELEVANCE_THRESHOLD = 1.2

# Number of chunks to retrieve per query
TOP_K = 4


def load_environment():
    """Load environment variables and verify the API key is present."""
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in .env file")
        print("Make sure your API key is configured in .env")
        sys.exit(1)

    return api_key


def load_vectorstore():
    """Load the knowledge base from ChromaDB."""
    if not CHROMA_DIR.exists():
        print("ERROR: Knowledge base not found.")
        print("Please run first: python scripts/build_knowledge_base.py")
        sys.exit(1)

    print("Loading embeddings model...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    print("Loading knowledge base...")
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR)
    )

    return vectorstore


def load_prompt_template():
    """Load the prompt template from the external file."""
    if not PROMPT_PATH.exists():
        print(f"ERROR: Prompt not found at {PROMPT_PATH}")
        sys.exit(1)

    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def log_unanswered_question(question, best_score):
    """
    Fallback layer 4: Log questions the system could not answer.
    These logs help identify gaps in the knowledge base over time.
    """
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / "unanswered_questions.log"

    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().isoformat()
        f.write(f"{timestamp} | Score: {best_score:.4f} | Question: {question}\n")


def get_fallback_response():
    """
    Fallback layer 3: Structured message when no relevant information is found.
    Instead of saying just 'I don't know', we guide the user to what we can help with.
    """
    return """Lo siento, no tengo información específica sobre tu consulta en este momento.

Puedo ayudarte con:
- Estado y seguimiento de pedidos
- Políticas de devolución de productos
- Información sobre nuestros productos sostenibles
- Tiempos y costos de envío
- Preguntas frecuentes sobre cuenta, pagos y soporte

Si tu consulta es sobre otro tema, te recomiendo:
- Visitar nuestra página web: ecomarket.com
- Escribir a soporte@ecomarket.com
- Contactarnos por WhatsApp al +57 300 123 4567

¿Hay algo más en lo que pueda ayudarte?"""


def format_retrieved_context(documents):
    """
    Format retrieved chunks into readable context for the LLM.
    Each chunk is labeled with its source for traceability.
    """
    if not documents:
        return "No relevant information found in the knowledge base."

    context_parts = []
    for i, doc in enumerate(documents, 1):
        source = doc.metadata.get("source", "unknown")
        tipo = doc.metadata.get("tipo", "unknown")

        context_parts.append(
            f"[Fragment {i} - Source: {source} - Type: {tipo}]\n{doc.page_content}"
        )

    return "\n\n---\n\n".join(context_parts)


def query_rag(question, vectorstore, llm, prompt_template, verbose=True):
    """
    Main RAG query function.

    Args:
        question: Customer question in Spanish
        vectorstore: ChromaDB knowledge base
        llm: Language model (Gemini)
        prompt_template: Prompt template string
        verbose: If True, prints process information

    Returns:
        dict with the answer and process metadata
    """
    # Step 1: Similarity search in the knowledge base
    if verbose:
        print(f"\n[1/4] Searching for relevant information...")

    # Retrieve chunks with their distance scores
    results_with_scores = vectorstore.similarity_search_with_score(
        question,
        k=TOP_K
    )

    if not results_with_scores:
        if verbose:
            print("[!] No relevant documents found")
        log_unanswered_question(question, 999.0)
        return {
            "answer": get_fallback_response(),
            "retrieved_documents": [],
            "best_score": None,
            "fallback_used": True
        }

    # Fallback layer 1: Check retrieval quality via distance score
    best_score = results_with_scores[0][1]

    if verbose:
        print(f"[2/4] Best similarity score: {best_score:.4f}")
        print(f"      (Relevance threshold: {RELEVANCE_THRESHOLD})")

    # If the best result is not relevant enough, activate fallback
    if best_score > RELEVANCE_THRESHOLD:
        if verbose:
            print("[!] Retrieved information is not relevant enough")
            print("[!] Activating fallback")
        log_unanswered_question(question, best_score)
        return {
            "answer": get_fallback_response(),
            "retrieved_documents": [doc for doc, _ in results_with_scores],
            "best_score": best_score,
            "fallback_used": True
        }

    # Step 2: Format the retrieved context
    retrieved_docs = [doc for doc, _ in results_with_scores]
    context = format_retrieved_context(retrieved_docs)

    if verbose:
        print(f"[3/4] Context ready ({len(retrieved_docs)} fragments)")
        print(f"      Sources: {set(doc.metadata.get('source') for doc in retrieved_docs)}")

    # Step 3: Build the augmented prompt and call the LLM.
    # Fallback layer 2: The prompt explicitly instructs the LLM not to hallucinate.
    if verbose:
        print(f"[4/4] Generating response with Gemini...")

    prompt = PromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "context": context,
        "question": question
    })

    return {
        "answer": answer,
        "retrieved_documents": retrieved_docs,
        "best_score": best_score,
        "fallback_used": False
    }


def main():
    """Main interactive loop."""
    print("=" * 60)
    print("ECOMARKET - RAG CUSTOMER SERVICE SYSTEM")
    print("=" * 60)
    print()

    # Load configuration
    load_environment()

    # Load system components
    vectorstore = load_vectorstore()
    prompt_template = load_prompt_template()

    # Initialize the LLM (Gemini).
    # Low temperature for more consistent, factual responses.
    print("Initializing Gemini model...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        max_output_tokens=600,
    )

    print("\nSystem ready. Type your question in Spanish.")
    print("Type 'salir' to exit.\n")
    print("-" * 60)

    # Interactive query loop
    while True:
        try:
            question = input("\nTu pregunta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nHasta luego!")
            break

        if not question:
            continue

        if question.lower() in ["salir", "exit", "quit"]:
            print("\nHasta luego!")
            break

        # Process the question
        result = query_rag(question, vectorstore, llm, prompt_template)

        # Display the response
        print()
        print("=" * 60)
        print("RESPONSE:")
        print("=" * 60)
        print(result["answer"])
        print()

        # Show process metadata (useful for debugging)
        if not result["fallback_used"]:
            print("-" * 60)
            print(f"Fragments consulted: {len(result['retrieved_documents'])}")
            print(f"Best score: {result['best_score']:.4f}")
            print(f"Sources: {set(doc.metadata.get('source') for doc in result['retrieved_documents'])}")
        else:
            print("-" * 60)
            print("(Fallback response used - question logged for improvement)")


if __name__ == "__main__":
    main()
