# 🌐 NexusGraph O2C (SAP Context Graph)

NexusGraph O2C is a full-stack, AI-powered visualizer for traversing and analyzing the complex lifecycle of SAP Order-to-Cash (O2C) datasets. It ingests raw, fragmented JSONL data across Sales Orders, Deliveries, and Invoices, strictly mapping them into a unified embedded graph architecture.

---

## 🏗️ Architecture Decisions
- **Monolithic Data, Decoupled Serving:** The backend handles both API generation (FastAPI) and raw SQL execution entirely in Python, while the UI is fully decoupled in React (Vite). This ensures UI rendering blockages don't interfere with the asynchronous API calls made to the LLM. For deployment, the system supports both split hosting (Vercel Frontend + Railway Backend) AND a unified single-server `StaticFiles` mount for extreme portability.
- **Frontend Graphing Engine:** Utilizes `react-force-graph-2d` layered under a premium absolute-positioned "glassmorphism" HUD, allowing hardware-accelerated rendering of thousands of nodes while preserving a sleek, responsive chat and inspector interface.
- **Dynamic Node Inspector:** When a node is clicked, the UI dynamically extracts and maps every underlying database property assigned to that entity, bypassing the need for redundant API calls for metadata.

## 🗄️ Database Choice: Relational SQLite
While Graph Databases (like Neo4j) are often standard for node visualizations, **SQLite** was explicitly chosen for this system due to the highly structured nature of SAP O2C data.
1. **Relational Integrity:** JSONL fragments dynamically feed into rigid SQL tables (e.g., Sales Orders inherently link to Deliveries). Using Foreign Keys drastically optimized node tracking compared to loose NoSQL models.
2. **Speed & Portability:** An embedded SQLite database allowed instantaneous ingestion scaling and requires zero environment overhead to spin up in deployment (unlike spinning up a Postgres instance).
3. **LLM Synergy:** Generative AI models are historically massively tuned on standard SQL syntax compared to specific graph query languages (like Cypher). Feeding an LLM a relational schema yields significantly lower hallucination rates.

## 🤖 LLM Prompting Strategy (Groq/LLaMA)
Because speed is a priority for UX, the system utilizes the blazing-fast **Groq API** running `llama-3.3-70b-versatile` in a **Two-Pass Reasoning Chain**:
1. **Pass 1 - Query Translation:** The LLM is fed the raw database schema and the natural language question. Its sole instruction is to output an executable SQL query. Temperature is strictly clamped to `0.0`.
2. **Pass 2 - Insight Generation:** The python backend executes the SQL on the local SQLite DB and extracts up to 100 rows of matched data. This hard factual data is fed back into the LLM context window alongside the original question. The LLM is then prompted to format this data into responsive **Markdown Tables** and explain the business lifecycle behind it, preventing *any* hallucinations because it is simply repeating known data.

## 🛡️ Security Guardrails & Edge Cases
- **Regex Query Isolation:** LLMs occasionally append conversational fluff (e.g., *"Here is your query: ```sql..."*). A rigid Python regex handler (`r'```(?:sql)?\s*(.*?)\s*```'`) was built to forcefully isolate and extract the raw SQL, preventing the entire pipeline from crashing on syntax errors.
- **SQL Leak Prevention:** If an execution error occurs, the pipeline catches it and maps it to a safe, generic frontend warning (*"I'm sorry, I couldn't process this request"*), entirely preventing the backend schema tables and raw SQL error logs from bleeding to the end-user.
- **System Constraints:** The system prompt aggressively restricts the AI: *"SECURITY CONSTRAINTS: NEVER mention SQL, databases, tables, schemas, backend logic, or internal queries. Act as a seamless business intelligence assistant."* This ensures the UX remains completely native and professional without breaking the "magic" of the application.

---

## 🚀 Quickstart (Local Development)

**1. Infrastructure Setup**
```bash
pip install -r requirements.txt
python ingest.py  # Builds the SQLite DB from /sap-o2c-data
```
*Note: Create an `api.txt` in the root folder with your Groq `gsk_` API Key.*

**2. Run the Backend & Frontend**
```bash
# Terminal 1 (API Server)
python -m uvicorn app:app --reload

# Terminal 2 (React UI)
cd frontend
npm install
npm run dev
```
