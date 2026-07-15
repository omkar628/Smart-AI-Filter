# SmartFeed AI

SmartFeed AI is a Chrome extension and FastAPI backend that semantically re-ranks YouTube home feed videos based on a user's selected interests.

Instead of relying on exact keyword matches, the system expands user interests into related concepts, embeds both the video metadata and concepts, measures semantic similarity, and uses a second-stage cross-encoder to validate the match.

## Features

- Semantic YouTube feed filtering based on weighted interests
- FastAPI backend for ranking and classification
- Chrome extension UI for managing topic weights
- Two-stage AI ranking pipeline:
  - `BAAI/bge-base-en-v1.5` for semantic retrieval
  - `cross-encoder/ms-marco-MiniLM-L6-v2` for relevance verification
- Groq-powered interest expansion for richer concept coverage
- Docker support for cloud deployment

## Project Structure

```text
Smart-AI-Filter/
|-- backend/
|   |-- main.py
|   |-- ml.py
|   |-- preference_expander.py
|   |-- requirements.txt
|   |-- requirements.docker.txt
|   `-- Dockerfile
|-- chrome_extension/
|   |-- manifest.json
|   |-- popup/
|   `-- scripts/
`-- README.md
```

## How It Works

1. The Chrome extension extracts video titles and channels from the YouTube home feed.
2. It sends the extracted videos and user interest weights to the backend.
3. The backend expands each interest into related concepts using Groq.
4. Each video is converted into text in this form:
   `Title: <title>. Channel: <channel>.`
5. The backend computes semantic similarity between the video text and each expanded concept using BGE embeddings.
6. The strongest concept matches are re-scored by a cross-encoder.
7. A video is accepted only if it passes both thresholds.

## Similarity Pipeline

The backend does not compare raw keywords to titles directly.

- User interest:
  Example: `Programming`
- Expanded concepts:
  Example: `Programming`, `Software Development`, `Coding Tutorial`, `Python Project`, and similar terms
- Video text:
  `Title: Learn Python by Building 5 Projects. Channel: CodeWithExample.`

The model then:

- generates embeddings for the video text and concepts,
- computes cosine similarity,
- keeps the top concept matches,
- applies a weighted top-k score,
- verifies the best candidate matches with a cross-encoder.

## Backend Setup

### Local Python setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create a `backend/.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Run the backend:

```powershell
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- `GET /`
- `GET /health`
- `POST /api/v1/rank-feed`

## Chrome Extension Setup

1. Open Chrome and go to `chrome://extensions`.
2. Enable Developer Mode.
3. Click `Load unpacked`.
4. Select the `chrome_extension` folder.
5. Open YouTube and use the extension popup to save your interest mix.

## API Request Format

`POST /api/v1/rank-feed`

```json
{
  "interests": {
    "JEE Advanced": 50,
    "Programming": 30,
    "Artificial Intelligence": 20
  },
  "videos": [
    {
      "video_id": "abc123",
      "title": "Top 10 Dynamic Programming Problems",
      "description": "",
      "channel": "CodeBasics"
    }
  ]
}
```

## Railway Deployment

This repository is set up so Railway can build using `backend/Dockerfile` from the repository root context.

### Recommended Railway settings

- Root directory: repository root
- Dockerfile path: `backend/Dockerfile`

### Required environment variables

- `GROQ_API_KEY`

### Notes

- The Dockerfile now honors Railway's injected `PORT`.
- A root-level `.dockerignore` is included to keep the build context small.
- The backend exposes `/health` so you can quickly verify startup status.

## Troubleshooting

### Docker build error: `requirements.docker.txt not found`

This happens when the Docker build context is the repository root but the Dockerfile tries to copy files as if the build context were `backend/`.

This repository already includes the fix by copying:

```dockerfile
COPY backend/requirements.docker.txt ./requirements.docker.txt
COPY backend/ .
```

### Backend returns 503

Check:

- `GROQ_API_KEY` is set correctly
- model downloads are allowed in the deployment environment
- the service has enough memory to load the embedding and cross-encoder models

### Extension cannot reach the backend

The extension currently targets:

- `http://localhost:8000/api/v1/rank-feed`

If you want the extension to use Railway instead of your local backend, update `chrome_extension/scripts/background.js` and `chrome_extension/manifest.json` to point to your deployed API domain.

## Development Notes

- `backend/ml.py` contains the ranking pipeline
- `backend/preference_expander.py` contains Groq-based concept expansion
- `chrome_extension/scripts/content.js` extracts YouTube feed data
- `chrome_extension/scripts/background.js` sends data to the API

## Next Steps Before Pushing

1. Add your Railway environment variables.
2. Redeploy once to confirm `/health` returns ready status.
3. If you want, update the extension backend URL to your Railway domain.
4. Commit and push the repository to GitHub.
