from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
from ml import AIRanker
import uvicorn

# Initialize App and load the AI Ranker singleton
app = FastAPI(title="SmartFeed AI API")
ranker = AIRanker()

# --- Pydantic Schemas for Validation ---
class Video(BaseModel):
    video_id: str
    title: str
    description: Optional[str] = ""
    channel: str

class RankRequest(BaseModel):
    # Expects format like: {"JEE Advanced": 50, "Programming": 30, "Entertainment": 20}
    interests: Dict[str, int] 
    videos: List[Video]

# --- API Endpoints ---
@app.post("/api/v1/rank-feed")
async def rank_feed(request: RankRequest):
    # Convert Pydantic objects to standard dictionaries for the ML engine
    videos_dict = [v.model_dump() for v in request.videos]
    
    # Process through the AI pipeline
    ranked_results = ranker.rank_videos(videos_dict, request.interests)
    
    return {"ranked_videos": ranked_results}

# To run the server directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)