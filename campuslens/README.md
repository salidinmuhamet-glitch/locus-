# CampusLens AI

CampusLens AI is a browser MVP for LOCUS HACKATHON 2026 CASE 01. It helps a student inspect a university through source-backed visual evidence instead of treating image search results as verified facts.

## Problem

A university photo search can mix official campus media, unrelated images, stock photography, duplicates, and stale material. CampusLens separates university resolution, evidence collection, deduplication, confidence scoring, and honest uncertainty.

## Current MVP

- University search with explicit disambiguation.
- Demo catalog for Nazarbayev University, Astana IT University, Harvard, Oxford, and other catalog entries.
- Verification pipeline with resolve, collect, dedupe, verify, categorize, and profile steps.
- Transparent confidence model: source 30%, page context 25%, university match 20%, category/visual match 15%, metadata 10%.
- HIGH, MEDIUM, and LOW confidence tiers.
- Evidence modal with source type, page title, metadata, category, confidence parts, and AI availability.
- Honest missing-source behavior: no fabricated URL is shown. Wikimedia links are explicitly search links, not proof of a source page.
- Duplicate detection for collected records using normalized title/facility similarity.
- Category filters, confidence filters, official-source filter, and recent-data filter.
- Verification summary: discovered, duplicate, irrelevant, HIGH, uncertain, source types, URL coverage, recent records, and unknown dates.
- University comparison and grounded assistant when the local AI capability is available.
- Top-university tab backed by `pars/top_world_universities.csv` and `pars/us_admission_requirements.csv`, with preference filters.
- Local light/dark theme and local browser auth/favorites for the demo.
- The main search flow is available without registration; authentication is optional and only protects local profile/favorites actions.

## Run Locally

Open `campuslens.html` in a browser. For reliable local CSV loading, serve the folder with any static server, for example:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000/campuslens.html`.

## Data And Source Handling

- `campuslens-data.json` contains the current demo evidence records.
- `pars/top_world_universities.csv` supplies ranking data.
- `pars/us_admission_requirements.csv` supplies US tuition, admission rate, and SAT fields where names match.
- Demo records use generated visual placeholders and are labelled as such; they are not photographs.
- A record is not presented as having an official source URL unless `sourceUrl` exists in the record.
- The current static MVP does not crawl websites, download images, or claim live visual verification.

## Architecture

The current deliverable is a dependency-free static browser app. The HTML file contains the UI, state, demo pipeline, deterministic scoring, evidence renderer, and CSV integration. `campuslens-data.json` is loaded at runtime. CSV files are loaded lazily for the top-university view.

## Planned Production Services

A production deployment should move collection and verification to a backend with endpoints such as:

- `POST /api/university/search`
- `POST /api/profile/generate`
- `GET /api/profile/{id}`
- `GET /api/images/{id}/evidence`
- `POST /api/compare`
- `POST /api/ask`
- `GET /api/search/status/{job_id}`

Suggested services are Next.js/TypeScript for the frontend, FastAPI for collection, PostgreSQL for records, Redis for jobs/cache, an image embedding or vision model for visual checks, and OpenStreetMap for maps. The backend should store source URL, domain, page title, date, license, dimensions, perceptual hash, verification status, and confidence components.

## Limitations

- The static demo cannot perform unrestricted web crawling from a local file.
- The deterministic provider verifies metadata-like evidence only; it does not inspect pixels with a vision model.
- Generated placeholders must not be presented as real university photos.
- Coordinates, travel distances, exact campus history, and image licenses are not invented when unavailable.
- Real image collection, perceptual hashing over downloaded media, embeddings, rate-limit handling, and persistent server-side caching require the planned backend.

## Test Scenarios

1. Search `Nazarbayev University` and inspect the profile.
2. Search `MIT` and select the resolved university.
3. Search `Harvard University` and open evidence for a card.
4. Search `University of Oxford`.
5. Search an unknown name and confirm the honest no-match response.
6. Search an ambiguous short name and confirm candidate selection appears.
7. Use the gallery filters and the Recent filter.
8. Open Top Universities and filter by country, tuition, admission rate, and SAT.

No account is required for these jury scenarios.

## License And Copyright

CampusLens keeps source links and does not redistribute downloaded images in this static MVP. Any production collector must respect robots.txt, provider terms, copyright, licensing metadata, rate limits, and attribution requirements.

## Pre-existing Components

The MVP builds on the existing `campuslens.html`, `campuslens-data.json`, local type declarations, and parser outputs in `pars/`. No external images are bundled.
