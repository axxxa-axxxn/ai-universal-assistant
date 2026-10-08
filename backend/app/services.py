import os
import re
import uuid
import time

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document as DocxDocument
from google import genai
from google.genai import types
from flask import current_app

from .models import Document, DocumentChunk
from . import db


ALLOWED = {".pdf", ".txt", ".md", ".csv", ".docx"}


def extract_text(path, ext):
    if ext == ".pdf":
        reader = PdfReader(path)
        return "\n\n".join(
            (p.extract_text() or "")
            for p in reader.pages
        )

    if ext == ".docx":
        doc = DocxDocument(path)
        return "\n".join(
            p.text
            for p in doc.paragraphs
        )

    with open(
        path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:
        return f.read()


def split_text(text, size=1200, overlap=180):
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(len(text), start + size)
        piece = text[start:end]

        if end < len(text):
            cut = max(
                piece.rfind(". "),
                piece.rfind(" ")
            )

            if cut > size * 0.55:
                end = start + cut + 1
                piece = text[start:end]

        chunks.append(piece.strip())

        if end >= len(text):
            break

        start = max(0, end - overlap)

    return chunks


def save_document(user_id, uploaded_file):
    original = uploaded_file.filename or "file"
    ext = os.path.splitext(original)[1].lower()

    if ext not in ALLOWED:
        raise ValueError(
            "Unsupported file type. Use PDF, TXT, MD, CSV or DOCX."
        )

    stored = f"{uuid.uuid4().hex}{ext}"

    path = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        stored
    )

    uploaded_file.save(path)

    text = extract_text(path, ext)
    chunks = split_text(text)

    if not chunks:
        os.remove(path)
        raise ValueError(
            "No readable text was found in this file."
        )

    doc = Document(
        user_id=user_id,
        original_name=original,
        stored_name=stored,
        file_type=ext
    )

    db.session.add(doc)
    db.session.flush()

    for i, chunk in enumerate(chunks):
        db.session.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                content=chunk
            )
        )

    db.session.commit()

    return doc, len(chunks)


def tokenize(text):
    return set(
        re.findall(
            r"\b[a-zA-Z0-9]{3,}\b",
            text.lower()
        )
    )


def retrieve(user_id, question, limit=5):
    q = tokenize(question)

    if not q:
        return []

    rows = (
        DocumentChunk.query
        .join(Document)
        .filter(Document.user_id == user_id)
        .all()
    )

    scored = []

    for row in rows:
        words = tokenize(row.content)
        overlap = len(q & words)

        if overlap:
            score = overlap / max(1, len(q))
            scored.append((score, row))

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        row
        for _, row in scored[:limit]
    ]


def web_search(query, limit=5):
    try:
        url = "https://html.duckduckgo.com/html/"

        r = requests.post(
            url,
            data={"q": query},
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        r.raise_for_status()

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        results = []

        for item in soup.select(".result")[:limit]:
            a = item.select_one(".result__a")
            snippet = item.select_one(
                ".result__snippet"
            )

            if a:
                results.append({
                    "title": a.get_text(
                        " ",
                        strip=True
                    ),
                    "url": a.get(
                        "href",
                        ""
                    ),
                    "snippet": (
                        snippet.get_text(
                            " ",
                            strip=True
                        )
                        if snippet
                        else ""
                    )
                })

        return results

    except Exception:
        return []


def generate_answer(
    question,
    context,
    history,
    image_path=None,
    web_results=None
):
    api_key = current_app.config.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        if context:
            return (
                "Gemini is not configured yet. "
                "Relevant information from your files:\n\n"
                + "\n\n".join(context)
            )

        return (
            "Gemini is not configured. "
            "Add GEMINI_API_KEY to backend/.env "
            "and restart the backend."
        )

    client = genai.Client(
        api_key=api_key
    )

    # Use the model configured in .env.
    # Current project configuration:
    # AI_MODEL=gemini-3.8-flash
    model = os.getenv(
        "AI_MODEL",
        current_app.config.get(
            "AI_MODEL",
            "gemini-3.8-flash"
        )
    )

    history_text = "\n".join(
        f"{m.role.upper()}: {m.content}"
        for m in history[-8:]
    )

    context_text = (
        "\n\n---\n\n".join(context)
        if context
        else "(No relevant personal files found.)"
    )

    web_text = "\n\n".join(
        f"TITLE: {x['title']}\n"
        f"URL: {x['url']}\n"
        f"SNIPPET: {x['snippet']}"
        for x in (web_results or [])
    ) or "(No web results.)"

    prompt = f"""You are a helpful general-purpose AI assistant.

Answer the user's question clearly and accurately.
Use the user's uploaded files when they are relevant.
Use web results only as supporting current information when supplied.
Do not claim you accessed information that is not in the supplied context.
If the user asks about an uploaded document, prioritize that document.
Be concise but useful.

CONVERSATION HISTORY:
{history_text}

UPLOADED FILE CONTEXT:
{context_text}

WEB SEARCH RESULTS:
{web_text}

USER QUESTION:
{question}
"""

    contents = [prompt]

    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        mime = "image/png"

        ext = os.path.splitext(
            image_path
        )[1].lower()

        if ext in [".jpg", ".jpeg"]:
            mime = "image/jpeg"

        elif ext == ".webp":
            mime = "image/webp"

        elif ext == ".gif":
            mime = "image/gif"

        contents.append(
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime
            )
        )

    # ---------------------------------------------------------
    # Gemini request with automatic retry
    # ---------------------------------------------------------
    #
    # Gemini can temporarily return HTTP 503 when the service
    # is experiencing high demand.
    #
    # Instead of immediately returning a Flask 500 error,
    # retry the request a few times with increasing delays.
    # ---------------------------------------------------------

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents
            )

            return (
                response.text
                or "I could not generate an answer."
            )

        except Exception as e:
            error_text = str(e).lower()

            temporary_error = (
                "503" in error_text
                or "unavailable" in error_text
                or "high demand" in error_text
                or "temporarily" in error_text
            )

            if temporary_error and attempt < max_attempts:
                # 2 seconds after first failure,
                # 4 seconds after second failure.
                wait_time = 2 ** attempt

                print(
                    f"Gemini temporarily unavailable. "
                    f"Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)
                continue

            # Give the frontend a useful message instead
            # of allowing Flask to return a generic 500.
            if temporary_error:
                print(
                    "Gemini remained unavailable after "
                    f"{max_attempts} attempts."
                )

                return (
                    "The AI service is temporarily busy. "
                    "Please try again in a few seconds."
                )

            # Other Gemini errors should still be visible
            # in the backend terminal for debugging.
            print(
                f"Gemini request failed: {e}"
            )

            return (
                "I couldn't generate an answer right now. "
                "Please try again."
            )