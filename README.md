# RecallAI 🧠

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![Groq](https://img.shields.io/badge/Groq-LLM-orange.svg)](https://groq.com)
[![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-red.svg)](https://github.com/facebookresearch/faiss)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.0-purple.svg)](https://python.langchain.com)

An intelligent document and YouTube video Q&A system powered by Groq LLM and semantic search. Upload documents or YouTube videos and ask questions to get accurate, contextual answers.

## 🏗 Architecture

```plaintext
┌──────────────┐        ┌──────────────┐
│   Client     │───────▶│   Flask API  │
└──────────────┘        └───────┬──────┘
                               │
                   ┌───────────┴───────────┐
                   ▼           ▼           ▼
            ┌──────────┐ ┌─────────┐ ┌────────┐
            │Document  │ │ YouTube │ │  Text  │
            │Processor │ │  API    │ │Splitter│
            └────┬─────┘ └────┬────┘ └───┬────┘
                 │           │          │
                 └───────────┴──────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Text Chunks    │
                  └────────┬────────┘
                          │
              ┌──────────┴───────────┐
              ▼                      ▼
      ┌──────────────┐      ┌───────────────┐
      │   Sentence   │      │    Vector     │
      │ Transformer  │      │    Store      │
      └──────┬───────┘      └───────┬───────┘
             └────────┬─────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │    Groq LLM     │
            └─────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │    Response     │
            └─────────────────┘

```

## 🛠 Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| 🌐 API Framework | Flask | RESTful API endpoints |
| 🧠 LLM Engine | Groq | AI reasoning & responses |
| 📊 Vector Store | FAISS | Semantic search |
| 🔤 Embeddings | Sentence Transformers | Text vectorization |
| 📝 Text Processing | LangChain | Document chunking |
| 📺 Video Processing | YouTube Transcript API | Caption extraction |
| 🗄️ Document Processing | PyMuPDF & python-docx | File parsing |
| 🔄 Process Management | Gunicorn | Production server |
| 🔍 Memory Management | psutil | Resource monitoring |

## 🌟 Features

- **Document Processing** 📄
  - PDF and DOCX support
  - Automatic text extraction
  - Smart chunking and embedding
  - Memory-efficient processing

- **YouTube Integration** 🎥
  - Transcript extraction
  - Automatic caption processing
  - Full video context understanding

- **Intelligent Q&A** 💡
  - Context-aware responses
  - Multi-step reasoning:
    1. Question clarification
    2. Relevant context retrieval
    3. Draft answer generation
    4. Answer refinement

- **Performance Optimized** ⚡
  - Memory-efficient processing
  - Automatic resource management
  - Configurable chunk sizes
  - Regular cleanup cycles

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Groq API key
- Virtual environment

### Installation

1. Clone the repository
```bash
git clone https://github.com/santanu2402/RecallAI-Backend.git
cd RecallAI
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

5. Run the application
```bash
python app.py
```

## 🔧 Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| GROQ_API_KEY | Your Groq API key | Required |
| UPLOAD_DIR | Directory for file uploads | /tmp |
| MAX_UPLOADS | Maximum concurrent uploads | 3 |
| MAX_FILE_SIZE | Maximum file size in bytes | 5MB |
| CHUNK_SIZE | Text chunk size | 400 |
| CHUNK_OVERLAP | Chunk overlap size | 40 |
| CLEANUP_INTERVAL | Cleanup interval in seconds | 900 |

## 📡 API Endpoints

### File Upload
```http
POST /upload/file
Content-Type: multipart/form-data

file: <file>
```

### YouTube Upload
```http
POST /upload/youtube
Content-Type: application/json

{
    "url": "https://www.youtube.com/watch?v=..."
}
```

### Ask Question
```http
POST /ask
Content-Type: application/json

{
    "question": "Your question here",
    "upload_no": "upload_id"
}
```

### Health Check
```http
GET /health
```

## 🔍 Example Usage

```python
import requests

# Upload a PDF
files = {'file': open('document.pdf', 'rb')}
upload_response = requests.post('http://localhost:5000/upload/file', files=files)
upload_id = upload_response.json()['upload_no']

# Ask a question
question = {
    'question': 'What are the main points discussed?',
    'upload_no': upload_id
}
answer = requests.post('http://localhost:5000/ask', json=question)
print(answer.json()['answer'])
```

## 🚢 Deployment

### Local Development
```bash
python app.py
```

### Production (Gunicorn)
```bash
gunicorn -c gunicorn.conf.py "app:create_app()"
```

### GCP e2-micro
Follow the detailed guide in [GCP_E2_DEPLOY.md](GCP_E2_DEPLOY.md)

## 🔐 Security Notes

- Set appropriate file size limits
- Configure CORS settings
- Use HTTPS in production
- Secure API key management
- Regular cleanup of uploaded files

## 📊 Monitoring

- Memory usage tracking
- Resource utilization alerts
- Operation logging
- Error tracking
- Performance metrics

## 🛠 Development

### Running Tests
```bash
python -m unittest test_app.py -v
```

### Code Style
```bash
pip install flake8
flake8 app.py
```

## 📝 Technical Details

- **Embedding Model**: all-MiniLM-L6-v2 (384 dimensions)
- **LLM**: Groq llama3-70b-8192
- **Vector Store**: FAISS
- **Text Processing**: LangChain
- **Memory Management**: Automatic cleanup and monitoring

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. Commit your changes
   ```bash
   git commit -m 'Add some AmazingFeature'
   ```
4. Push to the branch
   ```bash
   git push origin feature/AmazingFeature
   ```
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Groq](https://groq.com) for the LLM API
- [Sentence Transformers](https://www.sbert.net) for embeddings
- [FAISS](https://github.com/facebookresearch/faiss) for vector search
- [LangChain](https://python.langchain.com) for text processing
- [Flask](https://flask.palletsprojects.com) for the web framework
