import os
import chromadb
from pathlib import Path
import config

class RAGPipeline:
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path=config.CHROMADB_PATH)
        self.collection = None
        self.load_documents()
    
    def load_documents(self):
        """Load policy documents into ChromaDB"""
        try:
            doc_path = Path(config.POLICY_DOCUMENTS_PATH)
            documents = []
            
            for file in doc_path.glob("*.txt"):
                with open(file, 'r') as f:
                    content = f.read()
                    docs = self._chunk_document(content, file.name)
                    documents.extend(docs)
            
            if documents:
                self.collection = self.client.get_or_create_collection(
                    name="lending_policies",
                    metadata={"hnsw:space": "cosine"}
                )
                
                ids = [f"doc_{i}" for i in range(len(documents))]
                self.collection.add(ids=ids, documents=documents)
                print(f"✅ Loaded {len(documents)} policy chunks")
        
        except Exception as e:
            print(f"⚠️ RAG initialization: {e}")
    
    def _chunk_document(self, content, filename, chunk_size=500, overlap=100):
        """Split document into chunks"""
        chunks = []
        for i in range(0, len(content), chunk_size - overlap):
            chunk = content[i:i + chunk_size]
            if chunk.strip():
                chunks.append(f"[{filename}]\n{chunk}")
        return chunks
    
    def retrieve_relevant_policies(self, query, top_k=5):
        """Retrieve top-k relevant policies"""
        try:
            if not self.collection:
                return []
            
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            return results.get('documents', [[]])[0]
        except Exception as e:
            return []
    
    def build_context_from_policies(self, policies, max_tokens=1500):
        """Format policies for LLM context"""
        context = "\n---\n".join(policies)
        if len(context) > max_tokens * 4:
            context = context[:max_tokens * 4]
        return f"Relevant Policies:\n{context}"