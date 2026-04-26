"""
Script to build the RAG knowledge base for EcoMarket.

This script:
1. Loads documents from the data/ folder
2. Splits them into chunks using document-specific strategies
3. Generates embeddings with a multilingual model
4. Stores the chunks and embeddings in ChromaDB

Run this script once (or whenever documents change) before using rag_query.py.
"""

import json
import os
import sys
from pathlib import Path

# LangChain imports
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# Global configuration
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

# Multilingual embeddings model (runs locally, free, supports Spanish)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# ChromaDB collection name
COLLECTION_NAME = "ecomarket_knowledge_base"


def load_faqs():
    """
    Loads FAQs and applies per-entry chunking.
    Each FAQ (question + answer) becomes an independent chunk.
    """
    faqs_path = DATA_DIR / "faqs.json"

    if not faqs_path.exists():
        print(f"Warning: {faqs_path} not found, skipping FAQs")
        return []

    with open(faqs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for faq in data["faqs"]:
        # Chunk format: question and answer together
        content = f"Pregunta: {faq['pregunta']}\nRespuesta: {faq['respuesta']}"

        doc = Document(
            page_content=content,
            metadata={
                "source": "faqs",
                "id": faq["id"],
                "categoria": faq["categoria"],
                "tipo": "faq"
            }
        )
        documents.append(doc)

    print(f"FAQs loaded: {len(documents)} chunks")
    return documents


def load_return_policies():
    """
    Loads return policies and applies per-product chunking.
    Each product becomes an independent chunk with its full return information.
    """
    policies_path = DATA_DIR / "return_policies.json"

    if not policies_path.exists():
        print(f"Warning: {policies_path} not found, skipping return policies")
        return []

    with open(policies_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for product in data["return_policies"]:
        # Build chunk content depending on whether the product is returnable
        if product.get("returnable"):
            content = (
                f"Producto: {product['name']}\n"
                f"Categoría: {product['category']}\n"
                f"Retornable: Sí\n"
                f"Plazo de devolución: {product['return_period_days']} días\n"
                f"Condiciones: {product['conditions']}"
            )
        else:
            content = (
                f"Producto: {product['name']}\n"
                f"Categoría: {product['category']}\n"
                f"Retornable: No\n"
                f"Razón: {product['reason']}"
            )

        doc = Document(
            page_content=content,
            metadata={
                "source": "return_policies",
                "product_name": product["name"],
                "category": product["category"],
                "returnable": product.get("returnable", False),
                "tipo": "politica_devolucion"
            }
        )
        documents.append(doc)

    print(f"Return policies loaded: {len(documents)} chunks")
    return documents


def load_product_catalog():
    """
    Loads the product catalog and applies per-product chunking.
    Each product becomes a chunk with its full information
    (name, description, features, price, etc.).
    """
    catalog_path = DATA_DIR / "product_catalog.json"

    if not catalog_path.exists():
        print(f"Warning: {catalog_path} not found, skipping catalog")
        return []

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for product in data["productos"]:
        # Build a complete chunk per product
        caracteristicas = "\n- ".join(product.get("caracteristicas", []))
        certificaciones = ", ".join(product.get("certificaciones", []))

        content = (
            f"Producto: {product['nombre']}\n"
            f"Categoría: {product['categoria']}\n"
            f"Precio: ${product['precio_cop']:,} COP "
            f"(${product['precio_usd']} USD)\n"
            f"Material principal: {product['material_principal']}\n"
            f"Descripción: {product['descripcion']}\n"
            f"Características:\n- {caracteristicas}\n"
            f"Certificaciones: {certificaciones}\n"
            f"Stock disponible: {product['stock']} unidades"
        )

        # Append optional fields if present
        if "garantia_meses" in product:
            content += f"\nGarantía: {product['garantia_meses']} meses"

        if "fragancias" in product:
            content += f"\nFragancias disponibles: {', '.join(product['fragancias'])}"

        if "color_disponible" in product:
            content += f"\nColores disponibles: {', '.join(product['color_disponible'])}"

        doc = Document(
            page_content=content,
            metadata={
                "source": "product_catalog",
                "id": product["id"],
                "nombre": product["nombre"],
                "categoria": product["categoria"],
                "precio_cop": product["precio_cop"],
                "tipo": "producto"
            }
        )
        documents.append(doc)

    print(f"Product catalog loaded: {len(documents)} chunks")
    return documents


def load_shipping_policy():
    """
    Loads the shipping policy and applies recursive section-based chunking.
    This document is longer and narrative, so it needs a splitter that
    respects its structure (headings, paragraphs, etc.).
    """
    policy_path = DATA_DIR / "shipping_policy.md"

    if not policy_path.exists():
        print(f"Warning: {policy_path} not found, skipping shipping policy")
        return []

    with open(policy_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Configure the splitter to respect the Markdown structure.
    # Separators are tried in order: section headings first, then
    # paragraphs, then sentences, and finally individual words.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=[
            "\n## ",   # Split on main sections first
            "\n### ",  # Then on subsections
            "\n\n",    # Then on paragraphs
            "\n",      # Then on lines
            ". ",      # Then on sentences
            " "        # Last resort: words
        ],
        length_function=len,
    )

    chunks = text_splitter.split_text(content)

    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "source": "shipping_policy",
                "chunk_id": f"shipping_{i}",
                "tipo": "politica_envio"
            }
        )
        documents.append(doc)

    print(f"Shipping policy loaded: {len(documents)} chunks")
    return documents


def build_knowledge_base():
    """
    Main function that orchestrates the full knowledge base construction.
    """
    print("=" * 60)
    print("BUILDING ECOMARKET KNOWLEDGE BASE")
    print("=" * 60)
    print()

    # Step 1: Load all documents with their specific chunking strategies
    print("Step 1: Loading documents and applying chunking...")
    print("-" * 60)

    all_documents = []
    all_documents.extend(load_faqs())
    all_documents.extend(load_return_policies())
    all_documents.extend(load_product_catalog())
    all_documents.extend(load_shipping_policy())

    if not all_documents:
        print("\nError: No documents were loaded. Check that files exist in data/")
        sys.exit(1)

    print(f"\nTotal chunks generated: {len(all_documents)}")
    print()

    # Step 2: Initialize the embeddings model
    print("Step 2: Loading multilingual embeddings model...")
    print(f"Model: {EMBEDDING_MODEL}")
    print("(First run may take several minutes to download the model)")
    print("-" * 60)

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    print("Embeddings model loaded successfully")
    print()

    # Step 3: Create or replace the ChromaDB collection
    print("Step 3: Indexing chunks into ChromaDB...")
    print(f"Storage directory: {CHROMA_DIR}")
    print("-" * 60)

    # Remove existing database to start fresh
    if CHROMA_DIR.exists():
        import shutil
        shutil.rmtree(CHROMA_DIR)
        print("Previous database removed")

    # Create the new vector store from documents
    vectorstore = Chroma.from_documents(
        documents=all_documents,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR)
    )

    print(f"Indexing complete: {len(all_documents)} chunks stored")
    print()

    # Step 4: Verification with a sample query
    print("Step 4: Verifying the knowledge base...")
    print("-" * 60)

    test_query = "¿Cómo puedo hacer seguimiento a mi pedido?"
    results = vectorstore.similarity_search(test_query, k=2)

    print(f"Test query: '{test_query}'")
    print(f"Results found: {len(results)}")

    if results:
        print(f"\nBest result (from '{results[0].metadata.get('source')}'):")
        print(f"{results[0].page_content[:200]}...")

    print()
    print("=" * 60)
    print("KNOWLEDGE BASE BUILT SUCCESSFULLY")
    print("=" * 60)
    print()
    print("You can now run:")
    print("  python scripts/rag_query.py")
    print()


if __name__ == "__main__":
    build_knowledge_base()
