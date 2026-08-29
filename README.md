# Civic Infrastructure Triage Agent

A multi-agent system that turns a citizen's photo or text report of broken public infrastructure into a routed, department-ready work order — automatically.

---

## Problem

Citizens who spot broken infrastructure (potholes, damaged streetlights, overflowing drains) have no fast way to report it in a form municipal departments can act on. Reports get lost in generic complaint inboxes, duplicates pile up, and there's no consistent way to judge which issues are actually urgent. The result: slow fixes, wasted staff time, and citizens who give up reporting altogether.

## Solution

The system orchestrates a pipeline of four specialized agents to ingest, filter, classify, and route citizen reports:

```
Citizen Report ──> Intake Agent ──> Duplicate Check Agent ──> Severity Classifier Agent ──> Dispatch Agent ──> Work Order
                                           │ (If duplicate)
                                           └───> [Short-circuit & attach to existing]
```

### 1. Intake Agent
Uses Gemini's multimodal capabilities to analyze uploaded photos, extracting structured issue types and address details. It applies regex-based PII redaction on phone numbers and emails as a defense-in-depth measure before any model calls occur.
* **Multimodal Mismatch Flagging**: If the uploaded image does not depict the civic infrastructure issue described in the accompanying text (or contains no civic issue), the agent sets `has_discrepancy` to `true`. Reports flagged with a discrepancy bypass duplicate checking entirely to avoid being silently merged into unrelated issues.

### 2. Duplicate Check Agent
Uses a hybrid geospatial and semantic matching approach:
* **PostGIS Pre-filtering**: Instead of pulling all reports into Python, the agent queries the database directly using a custom `get_reports_near` database function to identify candidates within 100 meters. Resolved reports (`status = 'resolved'`) are excluded.
* **Semantic Verification**: An LLM call evaluates semantic equivalence only among the nearby geospatial candidates. If a duplicate is found, the pipeline short-circuits, attaching the new report to the existing one.

### 3. Severity Classifier Agent
Scores the urgency of the report on a 1-5 scale (from minor cosmetic issues to immediate safety hazards) and explains its reasoning in plain language.
* **Live Landmark Context**: The agent live-queries schools and hospitals within 200 meters using OpenStreetMap's Overpass API. If a landmark is a factor, the agent is instructed to name the specific school or hospital in its final reasoning rather than using generic text.

### 4. Dispatch Agent
Decides the destination department and drafts the formal work order in a single LLM call. Combining routing and drafting cuts down on latency, state-handoff points, and LLM round-trips.

---

## Architecture

| Agent | Responsibility |
| :--- | :--- |
| **Intake Agent** | Redacts PII, parses photos/text, extracts location, and geotags reports. Flags text/image mismatches (`has_discrepancy`) to bypass duplicate checks. |
| **Duplicate Check Agent** | Filters candidates within 100m using PostGIS (`get_reports_near`), excluding resolved reports, and performs semantic LLM validation to short-circuit duplicates. |
| **Severity Classifier Agent** | Live-queries OpenStreetMap Overpass API for schools/hospitals within 200m, assigning an explainable 1-5 severity score referencing specific landmarks by name. |
| **Dispatch Agent** | Routes the report to the correct department and drafts the formal work order in a single LLM call. |

---

## Tech Stack

* **Google ADK**: Orchestrates the multi-agent execution pipeline via a shared runner and session service.
* **MCP Server**: A custom geocoding/landmarks server ([`geocoding_server.py`](file:///c:/Users/Admin/Desktop/civic-triage-agent/mcp_server/geocoding_server.py)) that wraps geopy (Nominatim) for geocoding and executes live OpenStreetMap Overpass API queries.
* **LLM**: Gemini (`gemini-3.6-flash`) utilized via the Google ADK interface across all agents.
* **Database**: Supabase (PostgreSQL + PostGIS) for persistent storage and distance-based RPC queries.
* **Deployment**:
  * **Backend**: Render (Docker web service). Render is selected over Cloud Run to avoid mandatory credit card billing requirements; Render, Supabase, and Google AI Studio API keys allow this project to run on a zero-credit-card-required stack.
  * **Frontend**: A static HTML/CSS/JS frontend hosted on Vercel, which communicates directly with the Render API.
* **Security & Auth**:
  * **PII Redaction**: Pre-model regex filtering to redact phone numbers and emails.
  * **Dual-Key API Authentication**: Protects the API using a full Admin Key (`TRIAGE_API_KEY`) and a lower-trust Demo Key (`TRIAGE_DEMO_API_KEY`). The Demo Key can call `/triage`, but only the Admin Key is authorized to call the `/reports/{report_id}/resolve` endpoint.
  * **Rate Limiting**: Sliding window in-memory rate limiting applied to the `/triage` endpoint (capped at 5 requests per 60 seconds per IP).

---

## Live Demo

* **Live Frontend**: [https://civic-triage-frontend-m7lo262hy-hasithavittas-projects.vercel.app](https://civic-triage-frontend-m7lo262hy-hasithavittas-projects.vercel.app)
* **Backend API**: [https://civic-infrastructure-triage-agent.onrender.com](https://civic-infrastructure-triage-agent.onrender.com)
* *Note: The frontend uses a shared, rate-limited demo key. Heavy testing may temporarily exceed the model rate limits.*

---

## Setup

### 1. Clone & Install Dependencies
```bash
git clone <your-repo-url>
cd civic-triage-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_GENAI_USE_VERTEXAI=False
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
TRIAGE_API_KEY=your_secret_admin_key
TRIAGE_DEMO_API_KEY=your_public_demo_key
```
> [!IMPORTANT]
> `GOOGLE_GENAI_USE_VERTEXAI=False` must be explicitly configured, or the ADK framework may fail to authenticate Gemini API keys by defaulting to Vertex AI.

### 3. Database Initialization
Ensure your Supabase project has the **PostGIS** extension enabled. Run the SQL schema script in [`schema.sql`](file:///c:/Users/Admin/Desktop/civic-triage-agent/schema.sql) in your Supabase SQL editor to create the `reports` table and define the `get_reports_near` function.

### 4. Run Locally
Start the local FastAPI server:
```bash
python main.py
```
By default, the server will start on port `8080`.

### Example `curl` Commands

* **Submit Report (Text Only):**
  ```bash
  curl -X POST http://localhost:8080/triage \
    -H "X-API-Key: your_public_demo_key" \
    -F "raw_text=Large pothole near Raj Bhavan Road, Somajiguda, Hyderabad."
  ```

* **Submit Report (With Image):**
  ```bash
  curl -X POST http://localhost:8080/triage \
    -H "X-API-Key: your_public_demo_key" \
    -F "raw_text=Clogged drain causing water accumulation." \
    -F "image=@/path/to/pothole.jpg"
  ```

* **Resolve Report (Admin Key Required):**
  ```bash
  curl -X PATCH http://localhost:8080/reports/<report_id>/resolve \
    -H "X-API-Key: your_secret_admin_key"
  ```

---

## Testing

The project has a comprehensive, automated test suite to ensure robustness and catch regressions. The suite contains **37 tests** in total.

### 1. Run the Offline Mocked Test Suite
To run all tests offline (excluding live geocoding/landmarks API calls):
```bash
python -m pytest tests/ -v --ignore=tests/test_mcp_geocoding.py
```
This runs **34 tests** offline. All agent behaviors, rate-limiting rules, error boundaries, and dual-key permissions are fully mocked to prevent hitting Gemini API quotas or sending real network requests.
* **Mutation Testing Case**: The PII redaction logic contains a strict mutation test (`test_pii_redaction_before_model_call` in [`test_intake_agent.py`](file:///c:/Users/Admin/Desktop/civic-triage-agent/tests/test_intake_agent.py)) that inspects the actual mock arguments to verify that sensitive details are stripped *before* the prompt reaches the LLM.

### 2. Run Live Network Smoke Tests
To run the live Nominatim/Overpass API integration checks (run sparingly as it makes real network calls and is subject to rate limits):
```bash
python -m pytest tests/test_mcp_geocoding.py -v
```
This runs the remaining **3 tests** in the suite.

---

## Deployment

### Backend (Render)
1. Create a new **Web Service** on Render and connect your GitHub repository.
2. Render automatically detects the root [`Dockerfile`](file:///c:/Users/Admin/Desktop/civic-triage-agent/Dockerfile) to build the container.
3. Configure the **Health Check Path** to `/`.
4. In the Render Dashboard under **Environment**, add the environment variables defined in the `.env` section.

### Frontend (Vercel)
1. Deploy the project repository to Vercel.
2. In the project settings, configure the **Root Directory** to `civic-triage-frontend`.
3. The frontend does not require any Vercel-side environment variables; instead, [`index.html`](file:///c:/Users/Admin/Desktop/civic-triage-agent/civic-triage-frontend/index.html) features a client-side JavaScript check on `window.location.hostname` (and `window.location.protocol`) to dynamically switch between the local API endpoint (`http://127.0.0.1:8080/triage`) and the production Render API endpoint.

---

## Build Process & Engineering Discipline

This project was built iteratively using **Antigravity** as an AI coding agent, applying disciplined, test-driven engineering practices. Working in pair-programming cycles, we successfully identified and resolved critical bugs:
* **Duplicate-Check Exact Match Regression**: Detected via adversarial tests ([`run_harder_duplicate.py`](file:///c:/Users/Admin/Desktop/civic-triage-agent/tests/run_harder_duplicate.py)), where the duplicate check agent initially required exact issue type matches. We corrected this to allow semantic equivalence (e.g. marking "massive sinkhole" and "road surface damage" at the same coordinates as duplicates).
* **Database Client Retry Regression**: During the PostGIS migration commit, the retry-logic configuration on the database client was silently reverted from a robust, fail-fast policy (2 retries, 2s/4s delays) back to its legacy configuration (5 retries with exponential backoff up to 60 seconds). This regression went unnoticed until a live test hung for several minutes. It was caught and debugged via git log inspection and live log analysis, and restored back to the fail-fast behavior.
* **Infrastructure Migration**: Navigated a full, unplanned migration of the service and database (moving from GCP Cloud Run billing constraints to a zero-billing stack using Render and Supabase) without losing feature parity or breaking unit tests.

---

## Known Limitations

* **In-Memory Rate Limiting**: The sliding-window rate limiter is stored in-memory per-instance. It resets when the service restarts and would fragment if the backend were scaled to multiple instances.
* **Gemini Free-Tier Limits**: Deployed with Gemini API keys subject to free-tier rate limits, meaning high concurrent traffic will result in temporary model degradation or fallback work orders.
* **Prompt/Reasoning Verification**: While structural behaviors, error fallbacks, and schema parsing are automated, the actual quality and correctness of the agents' prompts are verified manually.

---

## Roadmap

* **Reports Dashboard & Map View**: Build an administrative interface to visually display routed work orders and duplicates on a map.
* **Persistent Rate Limiting**: Migrate the IP-based rate limiting to a Redis store to support multi-instance horizontal scaling.
* **Expanded Landmark Categories**: Incorporate a broader set of sensitive locations (e.g., nursing homes, emergency routes) to dynamically weigh severity scores.