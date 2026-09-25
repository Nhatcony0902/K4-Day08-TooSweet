"""Optional LLM-based Ragas evaluation using Gemini.

Install with ``pip install -e ".[evaluation,providers]"`` and set
``GEMINI_API_KEY`` before running. This script is intentionally separate from the
deterministic offline evaluator because it performs paid/network API calls.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from .config import load_dotenv
from .evaluate import DATASET_PATH, _answer
from .task9_retrieval_pipeline import retrieve


ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "group_project" / "evaluation" / "ragas_results.json"


async def main() -> None:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for Ragas evaluation")

    try:
        from google import genai
        from ragas.embeddings import GoogleEmbeddings
        from ragas.llms import llm_factory
        from ragas.metrics.collections import (
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )
    except ImportError as error:
        raise RuntimeError(
            'Install optional dependencies with: pip install -e ".[evaluation,providers]"'
        ) from error

    model = os.getenv("RAGAS_EVALUATOR_MODEL", "gemini-2.5-flash")
    embedding_model = os.getenv("RAGAS_EMBEDDING_MODEL", "gemini-embedding-001")
    client = genai.Client(api_key=api_key)
    llm = llm_factory(model, provider="google", client=client)
    embeddings = GoogleEmbeddings(client=client, model=embedding_model)
    metrics = {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevance": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
    }
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    output = []
    for strategy, use_reranking in (("dense_only", False), ("hybrid_rrf", True)):
        for item in dataset:
            chunks = retrieve(
                item["question"], top_k=5, score_threshold=-1.0,
                use_reranking=use_reranking,
            )
            response = _answer(item["question"], chunks)
            contexts = [chunk["content"] for chunk in chunks]
            common = {
                "user_input": item["question"],
                "response": response,
                "retrieved_contexts": contexts,
            }
            scores = {
                "faithfulness": (await metrics["faithfulness"].ascore(**common)).value,
                "answer_relevance": (
                    await metrics["answer_relevance"].ascore(
                        user_input=item["question"], response=response
                    )
                ).value,
                "context_precision": (
                    await metrics["context_precision"].ascore(
                        **common, reference=item["expected_answer"]
                    )
                ).value,
                "context_recall": (
                    await metrics["context_recall"].ascore(
                        **common, reference=item["expected_answer"]
                    )
                ).value,
            }
            output.append({"strategy": strategy, "question": item["question"], "scores": scores})
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
