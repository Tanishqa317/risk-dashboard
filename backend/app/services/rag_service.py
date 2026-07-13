import json
import os
from pathlib import Path
from typing import List, Optional, Dict
import numpy as np
from dotenv import load_dotenv

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
INCIDENT_REPORTS_DIR = DATA_DIR / "incident_reports"

model = None
index = None


class RAGIndex:
    def __init__(self):
        self.chunks = []
        self.embeddings = []
        self.sources = []

    def add(self, chunk_text: str, embedding: np.ndarray, source_file: str):
        self.chunks.append(chunk_text)
        self.embeddings.append(embedding)
        self.sources.append(source_file)

    def is_empty(self) -> bool:
        return len(self.chunks) == 0


def _split_into_chunks(text: str, chunk_size: int = 200) -> List[str]:
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0

    for word in words:
        current_chunk.append(word)
        current_size += 1
        if current_size >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_size = 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def build_index():
    global model, index

    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("Warning: sentence-transformers not available; RAG service disabled")
        return

    if index is not None and not index.is_empty():
        print("Index already built; skipping rebuild")
        return

    if not INCIDENT_REPORTS_DIR.exists():
        print(f"Warning: incident reports directory not found at {INCIDENT_REPORTS_DIR}")
        return

    model = SentenceTransformer("all-MiniLM-L6-v2")
    index = RAGIndex()

    txt_files = list(INCIDENT_REPORTS_DIR.glob("*.txt"))
    print(f"Loading {len(txt_files)} incident report files...")

    for file_path in txt_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            chunks = _split_into_chunks(content, chunk_size=200)

            for chunk in chunks:
                if chunk.strip():
                    embedding = model.encode(chunk)
                    index.add(chunk, embedding, file_path.name)

            print(f"Indexed {file_path.name}: {len(chunks)} chunks")
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")

    print(f"RAG index built: {len(index.chunks)} total chunks")


def retrieve_relevant(query: str, top_k: int = 5) -> List[Dict]:
    if index is None or index.is_empty():
        return []

    if model is None:
        return []

    query_embedding = model.encode(query)

    similarities = []
    for i, chunk_embedding in enumerate(index.embeddings):
        sim = np.dot(query_embedding, chunk_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding) + 1e-8
        )
        similarities.append((i, sim))

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_results = similarities[:top_k]

    results = [
        {
            "text": index.chunks[idx],
            "similarity": float(score),
            "source": index.sources[idx],
        }
        for idx, score in top_results
    ]

    return results


def analyze_patterns(unit_id: str) -> Dict:
    from app.services.correlation_service import get_risk_assessment

    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return {
            "unit_id": unit_id,
            "recurring_patterns": [],
            "prevention_priorities": [],
            "most_relevant_precedent": "Gemini API not available",
            "source_documents": [],
            "error": "Gemini API not configured",
        }

    try:
        assessment = get_risk_assessment(unit_id)
        risk_score = assessment.get("risk_score", 0)
        primary_concern = assessment.get("primary_concern", "Unknown")
        reasoning = assessment.get("reasoning", "")

        query = f"{primary_concern}. {reasoning}"
        retrieved_chunks = retrieve_relevant(query, top_k=5)

        if not retrieved_chunks:
            return {
                "unit_id": unit_id,
                "recurring_patterns": [],
                "prevention_priorities": [],
                "most_relevant_precedent": "No relevant historical incidents found",
                "source_documents": [],
                "error": "No relevant context retrieved",
            }

        context_text = "\n\n".join(
            [f"From {chunk['source']}:\n{chunk['text']}" for chunk in retrieved_chunks]
        )
        source_docs = list(set([chunk["source"] for chunk in retrieved_chunks]))

        client = genai.Client(api_key=GEMINI_API_KEY)

        system_prompt = (
            "You are a safety pattern analyst. Given current risk context and relevant historical incidents/regulatory guidance, "
            "identify recurring patterns and output ONLY valid JSON with this exact shape: "
            '{recurring_patterns: [string], prevention_priorities: [string], most_relevant_precedent: string}. '
            "Respond with ONLY the JSON object, no markdown, no preamble."
        )

        user_content = (
            f"Current Risk Context for {unit_id}:\n"
            f"Risk Score: {risk_score}\n"
            f"Primary Concern: {primary_concern}\n"
            f"Reasoning: {reasoning}\n\n"
            f"Relevant Historical Context:\n{context_text}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": user_content}]}],
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
            },
        )

        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        result = json.loads(response_text)

        return {
            "unit_id": unit_id,
            "recurring_patterns": result.get("recurring_patterns", []),
            "prevention_priorities": result.get("prevention_priorities", []),
            "most_relevant_precedent": result.get("most_relevant_precedent", ""),
            "source_documents": source_docs,
        }

    except json.JSONDecodeError as e:
        return {
            "unit_id": unit_id,
            "recurring_patterns": [],
            "prevention_priorities": [],
            "most_relevant_precedent": f"Failed to parse Gemini response: {str(e)}",
            "source_documents": [],
            "error": str(e),
        }
    except Exception as e:
        return {
            "unit_id": unit_id,
            "recurring_patterns": [],
            "prevention_priorities": [],
            "most_relevant_precedent": f"Error: {str(e)}",
            "source_documents": [],
            "error": str(e),
        }
