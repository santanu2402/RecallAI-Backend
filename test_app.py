import unittest
import json
from app import app, EMBED_MODEL, groq_refine
import os

class TestRecallAI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Test the embedding model directly
        self.test_text = "This is a test sentence for embedding."
        try:
            vectors = EMBED_MODEL.encode([self.test_text])
            self.embedding_works = True
        except Exception as e:
            print(f"Embedding model error: {e}")
            self.embedding_works = False
            
        # Create a PDF file with actual text content
        self.test_pdf = b'''%PDF-1.4
1 0 obj
<</Type /Catalog /Pages 2 0 R>>
endobj
2 0 obj
<</Type /Pages /Kids [3 0 R] /Count 1>>
endobj
3 0 obj
<</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>>
endobj
4 0 obj
<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>
endobj
5 0 obj
<</Length 44>>
stream
BT /F1 12 Tf 72 712 Td (This is a test document.) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000060 00000 n
0000000115 00000 n
0000000230 00000 n
0000000300 00000 n
trailer
<</Size 6 /Root 1 0 R>>
startxref
390
%%EOF'''
        
        # Create a test DOCX file
        self.test_docx = b'Mock DOCX content for testing'
        
    def tearDown(self):
        # Clean up test files
        if os.path.exists('test.txt'):
            os.remove('test.txt')
            
    def test_file_upload_endpoint(self):
        # Test PDF file upload
        from io import BytesIO
        pdf_file = BytesIO(self.test_pdf)
        response = self.client.post(
            '/upload/file',
            data={'file': (pdf_file, 'test.pdf')},
            content_type='multipart/form-data'
        )
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('upload_no', data)
        
    def test_youtube_upload_endpoint(self):
        # Test YouTube upload with a valid-looking URL
        response = self.client.post(
            '/upload/youtube',
            json={'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'}
        )
        data = json.loads(response.data)
        # Either success or proper error handling
        self.assertIn(response.status_code, [200, 400])
        
    def test_embedding_model(self):
        """Test if the sentence transformer model works"""
        test_texts = ["This is a test sentence.", "This is another test sentence."]
        try:
            vectors = EMBED_MODEL.encode(test_texts)
            self.assertEqual(len(vectors), 2)
            self.assertEqual(len(vectors[0]), 384)  # Check dimension
        except Exception as e:
            self.fail(f"Embedding model failed: {e}")
            

            
    def test_groq_llm(self):
        """Test if the Groq LLM works"""
        try:
            response = groq_refine(
                question="What is the capital of France?",
                context="France is a country in Europe. Its capital city is Paris.",
                draft="The capital of France is Paris."
            )
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
        except Exception as e:
            self.fail(f"Groq LLM failed: {e}")
        
    def test_ask_endpoint(self):
        # Test ask endpoint without proper upload
        response = self.client.post(
            '/ask',
            json={'question': 'test question', 'upload_no': 'invalid_id'}
        )
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', data)

if __name__ == '__main__':
    unittest.main()
