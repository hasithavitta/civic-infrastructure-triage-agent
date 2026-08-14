# Civic Infrastructure Triage Agent

A multi-agent system that turns a citizen's photo or text report of broken
public infrastructure into a routed, department-ready work order —
automatically. A personal project exploring what multi-agent systems are
actually good for, built with Google's Agent Development Kit (ADK), a
custom MCP server, and Gemini's multimodal capability.

---

## Problem

Citizens who spot broken infrastructure (potholes, damaged streetlights,
overflowing drains) have no fast way to report it in a form municipal
departments can act on. Reports get lost in generic complaint inboxes,
duplicates pile up, and there's no consistent way to judge which issues are
actually urgent. The result: slow fixes, wasted staff time, and citizens who
give up reporting altogether.

## Solution

An agent pipeline that takes a raw report — a photo, a text description, or
both together — reasons about it the way a triage officer would, and
produces a structured, routed work order. The Intake Agent uses Gemini's
multimodal capability to actually see and describe an uploaded photo (not
just accept a filename), checking for duplicates and explaining its own
severity judgment along the way.

```
Citizen report → Intake Agent → Duplicate Check Agent → Severity Classifier
Agent → Dispatch Agent → Dispatched work order
```

Four agents, not five: routing and work order drafting are combined into
a single Dispatch Agent. They share the same inputs and produce related
outputs, so a separate LLM round-trip between them added latency and one
more state handoff without adding real capability.

An MCP server exposing geocoding and mapping tools supports the Intake and
Duplicate Check agents, isolating GIS logic into a clean, swappable service
rather than tangling it into agent prompts.

## Why agents (not a fixed script)

Each stage requires judgment, not a lookup table:
- **Severity** depends on context (a pothole near a school ranks differently
  than the same pothole on a low-traffic road) — this needs reasoning, not a
  hardcoded rubric.
- **Duplicate detection** requires semantic + geospatial matching against
  open-ended prior reports, not exact-match lookups.
- **Routing** depends on interpreting the issue type against a department's
  actual jurisdiction, which varies by municipality and issue description.
- **Multimodal consistency checking** — deciding whether an uploaded photo
  actually matches its accompanying text isn't a fixed classification
  problem; it requires genuinely comparing open-ended image content against
  open-ended text.

## Architecture

| Agent | Responsibility |
|---|---|
| **Intake Agent** | Parses the photo/text report, extracts issue type and location, and geotags it via the MCP geocoding tool. Uses Gemini's multimodal input to genuinely analyze an uploaded photo (not just record that one was attached) — if the image and text description conflict, the agent is instructed to flag the mismatch explicitly rather than silently trusting one input over the other. |
| **Duplicate Check Agent** | Searches existing reports for geospatial + semantic matches. If found, attaches to the existing report instead of creating a new one (this is the one conditional branch in the pipeline). |
| **Severity Classifier Agent** | Scores urgency and — importantly — explains *why* (structural risk, proximity to schools/hospitals, foot traffic), rather than returning a black-box label. |
| **Dispatch Agent** | Maps the issue category to the correct municipal department AND drafts the formal work order, in one call. |

## Tech stack

- **Google ADK** — multi-agent orchestration (via a shared `Runner` +
  `InMemorySessionService` helper in `agents/runner_utils.py`)
- **MCP Server** — custom geocoding/maps tool server (`mcp_server/geocoding_server.py`)
- **LLM** — Gemini (via ADK)
- **API** — FastAPI wrapper (`main.py`) exposing `/triage` and a `/` health check
- **Deployment** — Render (Docker web service)
- **Database** — Supabase table storage
- **Security** — PII redaction on intake (phone numbers/emails stripped from
  free-text descriptions via regex before the report reaches the model or
  is stored)

> **Note on auth:** the deployed `/triage` endpoint is currently public
> (`--allow-unauthenticated`). This was fine for early testing, but since
> this is an ongoing project rather than a one-off demo, adding real
> authentication is now a near-term priority — see Known limitations below.

## No frontend (for now)

This project is currently API-first: a working `/triage` endpoint
(accepting text, an uploaded photo, or both) rather than a UI. That was a
reasonable place to focus effort early on — proving the agent pipeline,
the MCP server, and real multimodal reasoning all work — but a simple
frontend is a natural next step now that the backend is stable (see
Roadmap).

## Setup

```bash
git clone <your-repo-url>
cd civic-triage-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # fill in your own API key — never commit real keys
```

Your `.env` needs at minimum:
```
GOOGLE_API_KEY=your_real_gemini_key_here
GOOGLE_GENAI_USE_VERTEXAI=False
```
> `GOOGLE_GENAI_USE_VERTEXAI=False` matters: some ADK/genai versions default
> to Vertex AI credential mode and will reject a valid `GOOGLE_API_KEY`
> with an "API key not valid" error unless this is set explicitly.

Run the pipeline directly:
```bash
python orchestrator.py
```

Or run the API locally:
```bash
python main.py
# then, in another terminal — text only:
curl -X POST http://localhost:8080/triage \
  -F "raw_text=A large pothole on Main Street outside the elementary school."

# or with a photo attached:
curl -X POST http://localhost:8080/triage \
  -F "raw_text=A large pothole on Main Street outside the elementary school." \
  -F "image=@/path/to/photo.jpg"
```

## Testing

`tests/test_mcp_geocoding.py` is a standalone smoke test for the MCP
geocoding server's core functions (geocoding and distance calculation),
runnable independently of the full agent pipeline:
```bash
python tests/test_mcp_geocoding.py
```

The multimodal `/triage` endpoint has been manually verified against
text-only, image-only, and text+image cases — including a deliberate
mismatch test (an unrelated photo paired with infrastructure text) to
confirm the Intake Agent actually inspects the image content rather than
trusting the text description blindly. Automated tests for the full agent
pipeline (beyond the MCP server smoke test) are a known gap — see Roadmap.

## Deploying to Render

This application is deployed as a containerized Docker Web Service on Render.

### Deployment Steps:

1. **Database Setup**:
   Create a new project on [Supabase](https://supabase.com). In the Supabase SQL Editor, run the DDL script in [schema.sql](file:///c:/Users/Admin/Desktop/civic-triage-agent/schema.sql) to set up the `reports` table.

2. **Create Render Service**:
   - Log in to [Render](https://render.com) and create a new **Web Service**.
   - Connect your GitHub repository containing this project.

3. **Configure Service Settings**:
   - **Language/Environment**: Choose **Docker**.
   - **Instance Type**: Select **Free** (or any tier of your choice).
   - **Health Check Path**: Set to `/` (this verifies that the service starts and responds with `{"status":"ok"}`).

4. **Add Environment Variables**:
   In the **Environment** tab on Render's dashboard, add the following variables:
   - `GOOGLE_API_KEY`: Your Gemini API key.
   - `GOOGLE_GENAI_USE_VERTEXAI`: `False`.
   - `SUPABASE_URL`: Your Supabase project URL.
   - `SUPABASE_KEY`: Your Supabase API key (anon key is fine).
   - `TRIAGE_API_KEY`: Your secret API key to secure the `/triage` endpoint (sent via the `X-API-Key` header).

## Known limitations

Being upfront about these, since they're the real difference between "a
working demo" and "something you'd trust in production":

- **No authentication** on the deployed endpoint — anyone with the URL can
  call it. Fine for now, not fine long-term.
- **Database Persistence** — Reports are stored persistently in Supabase, preventing duplicate check loss after service restarts or across scaled instances.
- **Geocoding isn't actually wired into the Intake Agent yet** — the MCP
  server's `geocode_address` tool exists and is tested standalone, but
  `run_intake()` doesn't call it yet, so `latitude`/`longitude` stay `null`
  on every report. The Duplicate Check Agent currently relies on semantic
  similarity alone, not real geospatial distance.
- **No automated tests for the four agents themselves** — only the MCP
  geocoding functions have a dedicated test file. Agent behavior has been
  verified through manual testing, not a repeatable test suite.
- **Free-tier Gemini rate limits** will interrupt real usage quickly (20
  requests/day on the free tier, and each `/triage` call uses 3-4 model
  calls). A paid tier is basically required for anything beyond casual use.

## Roadmap

Rough priority order for continuing this as a real project, not just a demo:

1. Wire `geocode_address` into `run_intake()` so `latitude`/`longitude`
   actually populate, and have the Duplicate Check Agent use real distance
   calculations (via `distance_meters`) alongside semantic matching.
2. Replace in-memory report storage with a real database (Done — using Supabase).
3. Add authentication to the deployed endpoint.
4. Add a proper automated test suite for the four agents (mocking the
   Gemini calls, testing the orchestrator's branching logic in isolation).
5. A minimal frontend — even a simple form with an image upload — so this
   is usable by someone who isn't comfortable with curl.
6. Regional language support for report intake.
7. Voice input.
8. Offline queuing for low-connectivity areas.