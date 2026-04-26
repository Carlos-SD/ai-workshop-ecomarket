"""
RAG system evaluation script for EcoMarket.

This script runs a set of test questions against the RAG system and measures:
1. Retrieval quality: is it fetching documents from the correct sources?
2. Fallback handling: does the system recognize when it lacks information?
3. Average response time

Results are saved to evaluation/results.json for further analysis.

Before running:
  1. python scripts/build_knowledge_base.py
  2. Set GOOGLE_API_KEY in .env
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Import functions from the rag_query module
sys.path.insert(0, str(Path(__file__).parent))
from rag_query import (
    load_environment,
    load_vectorstore,
    load_prompt_template,
    query_rag,
    RELEVANCE_THRESHOLD,
)

from langchain_google_genai import ChatGoogleGenerativeAI


PROJECT_ROOT = Path(__file__).parent.parent
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
TEST_QUESTIONS_PATH = EVALUATION_DIR / "test_questions.json"
RESULTS_PATH = EVALUATION_DIR / "results.json"


def load_test_questions():
    """Load the test question set from the evaluation directory."""
    if not TEST_QUESTIONS_PATH.exists():
        print(f"ERROR: Test questions file not found at {TEST_QUESTIONS_PATH}")
        sys.exit(1)

    with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_retrieval(result, expected_sources):
    """
    Check whether the retrieval fetched at least one document
    from the expected sources.

    Args:
        result: Output from query_rag
        expected_sources: List of expected source names (e.g. ["faqs", "shipping_policy"])

    Returns:
        dict with retrieval metrics
    """
    if not result["retrieved_documents"]:
        return {
            "retrieved_correct_source": False,
            "expected_sources": expected_sources,
            "actual_sources": []
        }

    actual_sources = list(set(
        doc.metadata.get("source")
        for doc in result["retrieved_documents"]
    ))

    # Pass if at least one expected source was retrieved
    correct = any(src in actual_sources for src in expected_sources)

    return {
        "retrieved_correct_source": correct,
        "expected_sources": expected_sources,
        "actual_sources": actual_sources
    }


def run_evaluation():
    """Run the full RAG evaluation pipeline."""
    print("=" * 60)
    print("ECOMARKET RAG SYSTEM EVALUATION")
    print("=" * 60)
    print()

    # Load configuration and system components
    load_environment()

    print("Loading RAG system...")
    vectorstore = load_vectorstore()
    prompt_template = load_prompt_template()

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        max_output_tokens=600,
    )

    # Load test questions
    print("Loading test questions...")
    test_data = load_test_questions()
    questions = test_data["questions"]
    print(f"Total questions to evaluate: {len(questions)}")
    print()

    # Evaluation loop
    results = []

    # Global metrics
    total_questions = len(questions)
    correct_retrievals = 0
    fallbacks_used = 0
    fallbacks_expected = 0
    fallback_correct = 0
    total_time = 0

    print("Running evaluation...")
    print("-" * 60)

    for i, q in enumerate(questions, 1):
        print(f"\n[{i}/{total_questions}] {q['question'][:60]}...")

        # Run query and measure elapsed time
        start_time = time.time()
        result = query_rag(
            question=q["question"],
            vectorstore=vectorstore,
            llm=llm,
            prompt_template=prompt_template,
            verbose=False
        )
        elapsed = time.time() - start_time
        total_time += elapsed

        # Evaluate retrieval quality
        retrieval_eval = evaluate_retrieval(result, q.get("expected_sources", []))

        # Evaluate fallback handling
        should_fallback = q.get("should_fallback", False)
        used_fallback = result["fallback_used"]

        if should_fallback:
            fallbacks_expected += 1
            if used_fallback:
                fallback_correct += 1

        if used_fallback:
            fallbacks_used += 1

        if retrieval_eval["retrieved_correct_source"] and not should_fallback:
            correct_retrievals += 1

        # Store individual result
        result_entry = {
            "question": q["question"],
            "category": q["category"],
            "expected_sources": q.get("expected_sources", []),
            "should_fallback": should_fallback,
            "actual_sources": retrieval_eval["actual_sources"],
            "fallback_used": used_fallback,
            "best_score": result["best_score"],
            "answer": result["answer"][:300] + "..." if len(result["answer"]) > 300 else result["answer"],
            "elapsed_seconds": round(elapsed, 2),
            "retrieval_correct": retrieval_eval["retrieved_correct_source"],
            "fallback_correct": (should_fallback == used_fallback)
        }
        results.append(result_entry)

        # Visual status per question
        retrieval_status = "OK" if retrieval_eval["retrieved_correct_source"] or should_fallback else "FAIL"
        fallback_status = "OK" if (should_fallback == used_fallback) else "FAIL"
        print(f"     Retrieval: {retrieval_status} | Fallback: {fallback_status} | Time: {elapsed:.2f}s")

    # Compute final metrics
    print()
    print("=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    # Questions that should NOT use fallback
    answerable_questions = total_questions - fallbacks_expected
    retrieval_accuracy = (correct_retrievals / answerable_questions * 100) if answerable_questions else 0

    # Fallback handling accuracy
    fallback_accuracy = (fallback_correct / fallbacks_expected * 100) if fallbacks_expected else 0

    # Average response time
    avg_time = total_time / total_questions if total_questions else 0

    summary = {
        "evaluation_date": datetime.now().isoformat(),
        "total_questions": total_questions,
        "answerable_questions": answerable_questions,
        "fallback_questions": fallbacks_expected,
        "metrics": {
            "retrieval_accuracy_percent": round(retrieval_accuracy, 2),
            "correct_retrievals": correct_retrievals,
            "fallback_accuracy_percent": round(fallback_accuracy, 2),
            "fallback_correct": fallback_correct,
            "fallback_expected": fallbacks_expected,
            "fallback_used_total": fallbacks_used,
            "avg_response_time_seconds": round(avg_time, 2),
            "relevance_threshold": RELEVANCE_THRESHOLD
        },
        "detailed_results": results
    }

    # Print summary
    print(f"\nTotal questions evaluated: {total_questions}")
    print(f"  - Answerable questions: {answerable_questions}")
    print(f"  - Expected fallback questions: {fallbacks_expected}")
    print()
    print(f"Retrieval quality: {retrieval_accuracy:.1f}%")
    print(f"  ({correct_retrievals} of {answerable_questions} questions retrieved the correct source)")
    print()
    print(f"Fallback handling: {fallback_accuracy:.1f}%")
    print(f"  ({fallback_correct} of {fallbacks_expected} fallback cases detected correctly)")
    print()
    print(f"Average response time: {avg_time:.2f} seconds")
    print()

    # Save results to file
    EVALUATION_DIR.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Detailed results saved to: {RESULTS_PATH}")
    print()


if __name__ == "__main__":
    run_evaluation()
