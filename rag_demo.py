from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import math

load_dotenv()

client = OpenAI()

KNOWLEDGE_FILE = Path("knowledge.txt")


def split_text(text):
    lines = []

    for line in text.splitlines():
        line = line.strip()
        if line:
            lines.append(line)

    return lines


def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )

    return response.data[0].embedding


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0

    return dot / (norm_a * norm_b)


def ingest_knowledge():
    text = KNOWLEDGE_FILE.read_text(encoding="utf-8")
    chunks = split_text(text)

    vector_store = []

    for chunk in chunks:
        embedding = get_embedding(chunk)

        vector_store.append({
            "text": chunk,
            "embedding": embedding,
        })

    return vector_store


def retrieve(query, vector_store, top_k=3):
    query_embedding = get_embedding(query)

    scored_chunks = []

    for item in vector_store:
        score = cosine_similarity(query_embedding, item["embedding"])

        scored_chunks.append({
            "text": item["text"],
            "score": score,
        })

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)

    return scored_chunks[:top_k]


def answer_question(query, retrieved_chunks):
    context = "\n".join(
        f"- {item['text']}" for item in retrieved_chunks
    )

    prompt = f"""
Bạn là trợ lý hỗ trợ project finance Telegram bot.

Chỉ trả lời dựa trên tài liệu bên dưới.
Nếu tài liệu không có thông tin, hãy nói: "Tài liệu chưa có thông tin này."

Tài liệu:
{context}

Câu hỏi:
{query}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    return response.output_text


vector_store = ingest_knowledge()

while True:
    query = input("Hỏi: ").strip()

    if query.lower() in ["exit", "quit", "thoát"]:
        break

    retrieved_chunks = retrieve(query, vector_store)
    answer = answer_question(query, retrieved_chunks)

    print("\nĐoạn tìm được:")
    for item in retrieved_chunks:
        print(f"- score={item['score']:.3f}: {item['text']}")

    print("\nTrả lời:")
    print(answer)
    print()