from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz
import docx
from youtube_transcript_api import YouTubeTranscriptApi
from sentence_transformers import SentenceTransformer
import faiss
from groq import Groq
from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid
import re
import os
import time
import threading
from datetime import datetime
import psutil
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
UPLOAD_DIR = "/tmp"
MAX_UPLOADS = 5
MAX_FILE_SIZE = 10 * 1024 * 1024
CLEANUP_INTERVAL = 1800
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
DIM = 384

print(f"[STARTUP] {datetime.now()} Initializing RecallAI...")

try:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
    groq_client = Groq(api_key=GROQ_API_KEY)
    print(f"[STARTUP] {datetime.now()} Groq client initialized")
except Exception as e:
    print(f"[ERROR] {datetime.now()} Groq initialization failed: {e}")
    raise

try:
    EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    print(f"[STARTUP] {datetime.now()} Embedding model loaded")
except Exception as e:
    print(f"[ERROR] {datetime.now()} Embedding model loading failed: {e}")
    raise

UPLOADS = {}
UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/tmp')
MAX_UPLOADS = int(os.getenv('MAX_UPLOADS', '3'))  # Reduced for e2-micro
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', str(5 * 1024 * 1024)))  # 5MB limit
CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', '1800'))  # 30 minutes
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '400'))  # Smaller chunks
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '40'))
MAX_CHUNKS = int(os.getenv('MAX_CHUNKS', '30'))  # Limit total chunks
DIM = 384
UPLOADS = {}
MAX_MEMORY_PCT = float(os.getenv('MAX_MEMORY_PCT', '80.0'))  # Memory threshold

def check_memory():
    process = psutil.Process(os.getpid())
    memory_percent = process.memory_percent()
    if memory_percent > MAX_MEMORY_PCT:
        print(f"[WARN] {datetime.now()} High memory usage: {memory_percent:.1f}%")
        return False
    return True

print(f"[STARTUP] {datetime.now()} Initializing RecallAI...")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("[ERROR] GROQ_API_KEY not set")
groq_client = Groq(api_key=GROQ_API_KEY)
print(f"[STARTUP] {datetime.now()} Groq client initialized")

EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
print(f"[STARTUP] {datetime.now()} Embedding model loaded")

def cleanup_task():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        print(f"[CLEANUP] {datetime.now()} Starting cleanup")
        current_time = time.time()
        if len(UPLOADS) > MAX_UPLOADS:
            oldest = sorted(UPLOADS.items(), key=lambda x: x[1].get('timestamp', 0))
            for upload_no, _ in oldest[:len(UPLOADS) - MAX_UPLOADS]:
                data = UPLOADS.pop(upload_no)
                if data.get("file_path") and os.path.exists(data["file_path"]):
                    os.remove(data["file_path"])
                print(f"[CLEANUP] {datetime.now()} Removed {upload_no}")
        for upload_no, data in list(UPLOADS.items()):
            if current_time - data.get('timestamp', 0) > CLEANUP_INTERVAL:
                if data.get("file_path") and os.path.exists(data["file_path"]):
                    os.remove(data["file_path"])
                UPLOADS.pop(upload_no)
                print(f"[CLEANUP] {datetime.now()} Expired {upload_no}")
        process = psutil.Process(os.getpid())
        print(f"[MEMORY] {datetime.now()} Usage: {process.memory_info().rss / 1024 / 1024:.2f}MB")

threading.Thread(target=cleanup_task, daemon=True).start()

def extract_text_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = "\n".join([page.get_text() for page in doc])
        print(f"[PDF] {datetime.now()} Extracted {len(text)} chars")
        return text
    except Exception as e:
        print(f"[ERROR] {datetime.now()} PDF extraction failed: {e}")
        raise

def extract_text_docx(file_path):
    try:
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        print(f"[DOCX] {datetime.now()} Extracted {len(text)} chars")
        return text
    except Exception as e:
        print(f"[ERROR] {datetime.now()} DOCX extraction failed: {e}")
        raise

def extract_text_youtube(url):
    try:
        video_id = re.search(r"v=([a-zA-Z0-9_-]+)", url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        transcript = YouTubeTranscriptApi.get_transcript(video_id.group(1))
        text = " ".join([t['text'] for t in transcript])
        print(f"[YT] {datetime.now()} Extracted {len(text)} chars")
        return text
    except Exception as e:
        print(f"[ERROR] {datetime.now()} YouTube extraction failed: {e}")
        raise

def embed_chunks(chunks):
    try:
        print(f"[EMBED] {datetime.now()} Processing {len(chunks)} chunks")
        vectors = EMBED_MODEL.encode(chunks)
        index = faiss.IndexFlatL2(DIM)
        index.add(vectors)
        print(f"[EMBED] {datetime.now()} Index size: {index.ntotal}")
        return index, vectors
    except Exception as e:
        print(f"[ERROR] {datetime.now()} Embedding failed: {e}")
        raise

def groq_llm(prompt):
    try:
        print(f"[LLM] {datetime.now()} Query length: {len(prompt)}")
        completion = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        response = completion.choices[0].message.content.strip()
        print(f"[LLM] {datetime.now()} Response length: {len(response)}")
        return response
    except Exception as e:
        print(f"[ERROR] {datetime.now()} LLM failed: {e}")
        raise

def groq_refine(question, context, draft):
    try:
        prompt = f"You are a helpful assistant. The user asked: {question}\nContext: {context}\nDraft answer: {draft}\nImprove clarity, accuracy, and detail."
        print(f"[REFINE] {datetime.now()} Refining answer")
        completion = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        response = completion.choices[0].message.content.strip()
        print(f"[REFINE] {datetime.now()} Final length: {len(response)}")
        return response
    except Exception as e:
        print(f"[ERROR] {datetime.now()} Refinement failed: {e}")
        raise

# -------------------- ENDPOINTS -------------------- #
@app.route("/health", methods=["GET"])
def health_check():
    try:
        process = psutil.Process(os.getpid())
        memory_percent = process.memory_percent()
        return jsonify({
            "status": "healthy",
            "memory_usage_percent": round(memory_percent, 2),
            "active_uploads": len(UPLOADS)
        })
    except Exception as e:
        print(f"[ERROR] {datetime.now()} Health check failed: {e}")
        return jsonify({"status": "unhealthy"}), 500

@app.route("/upload/file", methods=["POST"])
def upload_file():
    try:
        if not check_memory():
            return jsonify({"error": "Server is under high load"}), 503
        print(f"[UPLOAD] {datetime.now()} File upload request")
        if len(UPLOADS) >= MAX_UPLOADS:
            print(f"[LIMIT] {datetime.now()} Max uploads reached")
            return jsonify({"error": "Maximum uploads reached"}), 429

        file = request.files['file']
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        print(f"[UPLOAD] {datetime.now()} File size: {size/1024/1024:.2f}MB")

        if size > MAX_FILE_SIZE:
            print(f"[LIMIT] {datetime.now()} File too large")
            return jsonify({"error": "File too large"}), 413

        path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
        file.save(path)

        if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
            return jsonify({"error": "Unsupported file type"}), 400

        text = extract_text_pdf(path) if file.filename.endswith(".pdf") else extract_text_docx(path)

        splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        chunks = splitter.split_text(text)
        if len(chunks) > 50:
            print(f"[LIMIT] {datetime.now()} Truncating chunks from {len(chunks)} to 50")
            chunks = chunks[:50]

        index, _ = embed_chunks(chunks)
        upload_no = str(uuid.uuid4())
        
        UPLOADS[upload_no] = {
            "text": text,
            "chunks": chunks,
            "index": index,
            "file_path": path,
            "timestamp": time.time()
        }
        print(f"[UPLOAD] {datetime.now()} Success: {upload_no}")
        return jsonify({"upload_no": upload_no})
    except Exception as e:
        print(f"[ERROR] {datetime.now()} Upload failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/upload/youtube", methods=["POST"])
def upload_youtube():
    try:
        print(f"[YT] {datetime.now()} YouTube upload request")
        if len(UPLOADS) >= MAX_UPLOADS:
            print(f"[LIMIT] {datetime.now()} Max uploads reached")
            return jsonify({"error": "Maximum uploads reached"}), 429

        data = request.json
        url = data.get("url")
        if not url:
            return jsonify({"error": "Missing YouTube URL"}), 400

        text = extract_text_youtube(url)
        splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        chunks = splitter.split_text(text)
        
        if len(chunks) > 50:
            print(f"[LIMIT] {datetime.now()} Truncating chunks from {len(chunks)} to 50")
            chunks = chunks[:50]

        index, _ = embed_chunks(chunks)
        upload_no = str(uuid.uuid4())
        
        UPLOADS[upload_no] = {
            "text": text,
            "chunks": chunks,
            "index": index,
            "file_path": None,
            "timestamp": time.time()
        }
        print(f"[YT] {datetime.now()} Success: {upload_no}")
        return jsonify({"upload_no": upload_no})
    except Exception as e:
        print(f"[ERROR] {datetime.now()} YouTube upload failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/ask", methods=["POST"])
def ask():
    try:
        print(f"[ASK] {datetime.now()} Question request")
        data = request.json
        question = data.get("question")
        upload_no = data.get("upload_no")

        if not question or not upload_no:
            return jsonify({"error": "Missing question or upload_no"}), 400
        if upload_no not in UPLOADS:
            return jsonify({"error": "Invalid upload_no"}), 404

        print(f"[ASK] {datetime.now()} Processing: {question[:100]}...")
        chunks = UPLOADS[upload_no]["chunks"]
        index = UPLOADS[upload_no]["index"]

        clarify_prompt = f'The user asked: "{question}"\nRewrite this question to be explicit and unambiguous.'
        clarified_question = groq_llm(clarify_prompt)
        print(f"[ASK] {datetime.now()} Clarified: {clarified_question[:100]}...")

        q_vec = EMBED_MODEL.encode([clarified_question])
        D, I = index.search(q_vec, k=3)
        retrieved_chunks = [chunks[i] for i in I[0]]
        context = "\n\n".join(retrieved_chunks)
        print(f"[ASK] {datetime.now()} Retrieved {len(retrieved_chunks)} chunks")

        draft_prompt = f"Answer using only this context:\n{context}\n\nQuestion: {clarified_question}"
        draft = groq_llm(draft_prompt)
        print(f"[ASK] {datetime.now()} Draft length: {len(draft)}")

        final_answer = groq_refine(clarified_question, context, draft)
        print(f"[ASK] {datetime.now()} Final length: {len(final_answer)}")

        process = psutil.Process(os.getpid())
        print(f"[MEMORY] {datetime.now()} Usage: {process.memory_info().rss / 1024 / 1024:.2f}MB")

        return jsonify({
            "clarified_question": clarified_question,
            "answer": final_answer
        })
    except Exception as e:
        print(f"[ERROR] {datetime.now()} Question processing failed: {e}")
        return jsonify({"error": str(e)}), 500

def create_app():
    print(f"[STARTUP] {datetime.now()} Initializing app")
    threading.Thread(target=cleanup_task, daemon=True).start()
    return app

if __name__ == "__main__":
    port = int(os.getenv('PORT', '5000'))
    print(f"[STARTUP] {datetime.now()} Starting server on port {port}")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
