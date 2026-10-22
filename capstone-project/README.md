# AI Loan Eligibility Assessment System

An intelligent loan processing system using multi-agent architecture with financial and risk analysis agents.

## Project Structure

```
capstone-project/
├── agents/                 # Agent implementations
│   ├── financial_agent.py
│   ├── risk_agent.py
│   └── recommendation_agent.py
├── tools/                  # Calculation and analysis tools
│   ├── financial_calculator.py
│   └── risk_calculator.py
├── rag/                    # Retrieval-Augmented Generation pipeline
│   └── rag_pipeline.py
├── utils/                  # Utilities
│   ├── logging_setup.py
│   └── error_handler.py
├── data/                   # Data files
│   ├── sample_applications.json
│   ├── synthetic_data_generator.py
│   └── lending_policies.txt
├── tests/                  # Test suite
│   ├── conftest.py
│   ├── test_financial_agent.py
│   ├── test_risk_agent.py
│   ├── test_orchestrator.py
│   └── test_rag.py
├── main.py                 # Entry point
├── orchestrator.py         # Orchestrates all agents
├── config.py               # Configuration
├── requirements.txt        # Dependencies
└── .env                    # Environment variables (create this)
```

## Installation

### Prerequisites
- Python 3.8+
- Google API key (for Gemini LLM)

### Setup Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create .env File**
   Create a `.env` file in the project root with your Google API key:
   ```
   GOOGLE_API_KEY=your_actual_google_api_key_here
   ```

3. **Verify Data Files**
   - Synthetic applications will be auto-generated in `data/sample_applications.json`
   - Lending policies are in `data/lending_policies.txt`

## Running the Application

### Process Single Loan Application
```bash
python main.py single
```

### Process Batch of Applications
```bash
python main.py batch 10
```
Replace `10` with the number of applications to process.

### Default (Single Application)
```bash
python main.py
```

## Web Application (FastAPI + React)

### Backend (FastAPI)
From `capstone-project/`:
```bash
uvicorn api.main:app --reload --port 8000
```
- Interactive docs: http://127.0.0.1:8000/docs
- `GET /api/documents/types` - income document types
- `POST /api/documents/extract` - upload a document (multipart: `file`, `doc_type`); Gemini extracts income fields
- `POST /api/applications` - submit the reviewed applicant data (+ `document_ids`); runs the three agents and saves the result
- `GET /api/applications?status=APPROVED|REJECTED|PENDING_REVIEW` - list applications
- `GET /api/applications/stats` - counts per status
- `GET /api/applications/{id}` - full detail: input, documents, financial/risk/recommendation agent outputs
- `POST /api/applications/import-samples?limit=10` - assess and save the bundled sample applications
- `POST /api/applications/assess` - run the agents without saving
- `GET /api/applications/samples?limit=10` - bundled sample applications

Data is stored in SQLite at `data/loan_applications.db`. Uploaded files are stored in `uploads/`.
Extraction needs a valid `GOOGLE_API_KEY` in `.env`; without one, documents are marked "Extraction failed" and the form can still be filled in by hand.

### Frontend (React + Vite)
Requires Node.js 18+. From `capstone-project/frontend/`:
```bash
npm install
npm run dev
```
Open http://localhost:5173. Vite proxies `/api` to the backend on port 8000, so start the backend first.

## Running Tests

```bash
pytest tests/
```

## System Workflow

1. **Validation** - Checks application data completeness
2. **Pre-screening** - Quick policy violation checks
3. **Parallel Analysis** - Runs Financial & Risk agents simultaneously
4. **Recommendation** - Synthesizes agent decisions
5. **Final Decision** - APPROVE / REJECT / REVIEW / ESCALATE

## Configuration

Edit `config.py` to customize:
- Credit score thresholds
- DTI ratio limits
- Income requirements
- Risk assessment weights
- Retry and timeout settings
- Parallel execution

## Key Features

- 🤖 Multi-agent LLM orchestration
- 💰 Advanced financial analysis (DTI, affordability)
- ⚠️ Risk scoring and assessment
- 🔍 RAG-based policy retrieval
- 📊 Comprehensive logging
- 🔄 Parallel agent execution
- ✅ Full test coverage

## Output

Each application returns:
- **Decision**: APPROVE / REJECT / REVIEW / ESCALATE
- **Confidence Score**: 0.0 - 1.0
- **Financial Analysis**: DTI, monthly payment, affordability
- **Risk Analysis**: Risk score, risk level, confidence
- **Workflow Duration**: Processing time in seconds
- **Human Approval Required**: Flag for manual review

## Troubleshooting

- **Google API Key Error**: Ensure `.env` file is created and has valid GOOGLE_API_KEY
- **ChromaDB Errors**: Check that `chroma_data/` directory is writable
- **Import Errors**: Run `pip install -r requirements.txt` again
- **Missing Policies**: Ensure `.txt` files exist in `data/` directory

## Development

- Logging output: `logs/loan_assessment.log`
- ChromaDB data: `chroma_data/` directory
- Test fixtures in `tests/conftest.py`

## Notes

- Parallel execution can be disabled in `config.py` for debugging
- RAG pipeline is optional but enhances policy-based decisions
- Human approval threshold is 75% confidence or REVIEW decisions
