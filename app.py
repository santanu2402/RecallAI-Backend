from flask import Flask, request, jsonify
import fitz  # PyMuPDF for PDF
import docx
from youtube_transcript_api import YouTubeTranscriptApi
from sentence_transformers import SentenceTransformer
import faiss
import ollama
from groq import Groq
from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid
import re
import os
import time
import threading

app = Flask(__name__)

# -------------------- CONFIG -------------------- #
UPLOAD_DIR = "/tmp"
UPLOADS = {}  # {upload_no: {"text": str, "index": faiss_index, "chunks": [str], "file_path": str}}
EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
DIM = 384
groq_client = Groq(api_key="")

# -------------------- CLEANUP THREAD -------------------- #
def cleanup_task():
    while True:
        time.sleep(1800)  # every 30 min
        print("[CLEANUP] Clearing uploads and temp files...")
        for upload_no, data in list(UPLOADS.items()):
            file_path = data.get("file_path")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        UPLOADS.clear()
        print("[CLEANUP] Done.")

threading.Thread(target=cleanup_task, daemon=True).start()

# -------------------- HELPERS -------------------- #
def extract_text_pdf(file_path):
    doc = fitz.open(file_path)
    return "\n".join([page.get_text() for page in doc])

def extract_text_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_youtube(url):
    video_id = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")
    transcript = YouTubeTranscriptApi.get_transcript(video_id.group(1))
    return " ".join([t['text'] for t in transcript])

def embed_chunks(chunks):
    vectors = EMBED_MODEL.encode(chunks)
    index = faiss.IndexFlatL2(DIM)
    index.add(vectors)
    return index, vectors

def local_llm(prompt):
    try:
        response = ollama.chat(model="llama3:8b", messages=[{"role": "user", "content": prompt}])
        return response['message']['content']
    except Exception as e:
        # Fallback to Groq if Ollama is not available
        completion = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content

def groq_refine(question, context, draft):
    prompt = f"""
    You are a helpful assistant. The user asked: {question}
    Context: {context}
    Draft answer: {draft}
    Improve clarity, accuracy, and detail. Add any extra relevant facts.
    """
    completion = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# -------------------- ENDPOINTS -------------------- #
@app.route("/upload/file", methods=["POST"])
def upload_file():
    file = request.files['file']
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    file.save(path)

    if file.filename.endswith(".pdf"):
        text = extract_text_pdf(path)
    elif file.filename.endswith(".docx"):
        text = extract_text_docx(path)
    else:
        return jsonify({"error": "Unsupported file type"}), 400

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(text)
    index, _ = embed_chunks(chunks)
    upload_no = str(uuid.uuid4())

    UPLOADS[upload_no] = {"text": text, "chunks": chunks, "index": index, "file_path": path}
    return jsonify({"upload_no": upload_no})

@app.route("/upload/youtube", methods=["POST"])
def upload_youtube():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing YouTube URL"}), 400

    try:
        text = extract_text_youtube(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(text)
    index, _ = embed_chunks(chunks)
    upload_no = str(uuid.uuid4())

    UPLOADS[upload_no] = {"text": text, "chunks": chunks, "index": index, "file_path": None}
    return jsonify({"upload_no": upload_no})

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")
    upload_no = data.get("upload_no")

    if not question or not upload_no:
        return jsonify({"error": "Missing question or upload_no"}), 400
    if upload_no not in UPLOADS:
        return jsonify({"error": "Invalid upload_no"}), 404

    chunks = UPLOADS[upload_no]["chunks"]
    index = UPLOADS[upload_no]["index"]

    # Step 1: Clarify intent
    clarify_prompt = f"""
    The user asked: "{question}"
    Rewrite this question to be explicit and unambiguous for searching a document or transcript.
    """
    clarified_question = local_llm(clarify_prompt).strip()

    # Step 2: Retrieve top chunks
    q_vec = EMBED_MODEL.encode([clarified_question])
    D, I = index.search(q_vec, k=3)
    retrieved_chunks = [chunks[i] for i in I[0]]
    context = "\n\n".join(retrieved_chunks)

    # Step 3: Draft answer
    draft_prompt = f"Answer the question using only this context:\n{context}\n\nQuestion: {clarified_question}"
    draft = local_llm(draft_prompt)

    # Step 4: Refine
    final_answer = groq_refine(clarified_question, context, draft)

    return jsonify({
        "clarified_question": clarified_question,
        "answer": final_answer
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
