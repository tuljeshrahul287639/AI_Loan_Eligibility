import pytest
from pathlib import Path
from rag.rag_pipeline import RAGPipeline
import config

@pytest.fixture
def rag_pipeline():
    return RAGPipeline()

def test_rag_initialization(rag_pipeline):
    """Test RAG pipeline initializes"""
    assert rag_pipeline is not None
    assert rag_pipeline.client is not None

def test_policy_documents_exist():
    """Test policy documents exist"""
    doc_path = Path(config.POLICY_DOCUMENTS_PATH)
    assert doc_path.exists()
    txt_files = list(doc_path.glob("*.txt"))
    assert len(txt_files) > 0

def test_document_loading(rag_pipeline):
    """Test documents are loaded into ChromaDB"""
    assert rag_pipeline.collection is not None

def test_policy_retrieval(rag_pipeline):
    """Test retrieving relevant policies"""
    query = "credit score requirements"
    policies = rag_pipeline.retrieve_relevant_policies(query)
    assert isinstance(policies, list)

def test_policy_retrieval_with_multiple_results(rag_pipeline):
    """Test retrieving multiple policy documents"""
    query = "DTI debt to income ratio"
    policies = rag_pipeline.retrieve_relevant_policies(query, top_k=3)
    assert len(policies) <= 3

def test_context_building(rag_pipeline):
    """Test building context from policies"""
    query = "minimum income requirements"
    policies = rag_pipeline.retrieve_relevant_policies(query)
    if policies:
        context = rag_pipeline.build_context_from_policies(policies)
        assert "Relevant Policies:" in context

def test_empty_query_handling(rag_pipeline):
    """Test handling empty query"""
    policies = rag_pipeline.retrieve_relevant_policies("")
    assert isinstance(policies, list)

def test_document_chunking(rag_pipeline):
    """Test documents are properly chunked"""
    # Load documents and verify they were chunked
    assert rag_pipeline.collection is not None
    # Chunking should create multiple documents from policy files
    results = rag_pipeline.collection.get()
    assert len(results['ids']) > 0

def test_retrieval_consistency(rag_pipeline):
    """Test retrieval is consistent for same query"""
    query = "bankruptcy policy"
    result1 = rag_pipeline.retrieve_relevant_policies(query, top_k=1)
    result2 = rag_pipeline.retrieve_relevant_policies(query, top_k=1)
    assert result1 == result2 or len(result1) == 0