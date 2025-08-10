from fastapi import FastAPI, Query, HTTPException
from db.mongo import db
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone



app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"] for more security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI is working!"}

@app.get("/cinema")
async def get_movies(type: str | None = Query(default = None)):
    movies = []
    if type is None:
        docs = await db["cinema"].find({}).to_list()
    else:
        docs = await db["cinema"].find({"foundIn": type}).to_list(None)
    for doc in docs:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        movies.append(doc)
        
    return movies

@app.delete("/cinema/{movie_id}")
async def delete_movie(movie_id: str):
    try:
        result = await db["cinema"].delete_one({"_id": ObjectId(movie_id)})
        if result.deleted_count == 1:
            return {"message": "Movie deleted successfully."}
        raise HTTPException(status_code=404, detail="Movie not found.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class MovieUpdate(BaseModel):
    original_title: Optional[str] = None
    overview: Optional[str] = None
    original_language: Optional[str] = None
    imdb: Optional[float] = None
    release_date: Optional[str] = None
    run_time: Optional[str] = None 
    genres: Optional[List[str]] = None
    episodes: Optional[int] = None
    seasons: Optional[int] = None
    cast: Optional[List[Dict]] = None 

@app.put("/cinema/{movie_id}")
async def update_movie(movie_id: str, update: MovieUpdate):
    result = await db["cinema"].update_one(
        {"_id": ObjectId(movie_id)},
        {"$set": {k: v for k, v in update.model_dump().items() if v is not None}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    return {"message": "Movie updated successfully"}

class MovieCreate(BaseModel):
    original_title: str
    overview: str
    original_language: str
    imdb: float
    release_date: Optional[str] = None
    poster_path: Optional[str] = None 
    backdrop_path: Optional[str] = None  
    genres: Optional[List[str]] = Field(default_factory=list)
    foundIn: List[str] = Field(..., min_items=1)
    run_time: Optional[str] = None
    episodes: Optional[int] = None
    seasons: Optional[int] = None
    cast: Optional[List[Dict]] = Field(default_factory=list)


class MovieResponse(BaseModel):
    id: str = Field(alias="_id") # Map _id from MongoDB to 'id' in the response
    backdrop_path: Optional[str] = None
    original_language: Optional[str] = None
    original_title: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    release_date: Optional[str] = None
    title: Optional[str] = None
    imdb: Optional[float] = None
    genres: Optional[List[str]] = None
    run_time: Optional[str] = None
    foundIn: List[str]
    episodes: Optional[int] = None
    seasons: Optional[int] = None
    cast: Optional[List[Dict]] = None
    
    class Config:
        populate_by_name = True # Allows mapping of aliases
        json_encoders = {
            ObjectId: str
        }


@app.post("/cinema", response_model=MovieResponse) # <--- ADD response_model here
async def create_movie(movie: MovieCreate):
    movie_dict = {k: v for k, v in movie.model_dump(by_alias=True).items() if v is not None}
    result = await db["cinema"].insert_one(movie_dict)
    if result.inserted_id:
        # Retrieve the newly inserted document to return the full object
        inserted_movie = await db["cinema"].find_one({"_id": result.inserted_id})
        if inserted_movie:
            inserted_movie["_id"] = str(inserted_movie["_id"]) # Convert ObjectId to string
            return inserted_movie
    raise HTTPException(status_code=500, detail="Failed to create movie")

@app.get("/search/movie")
async def search_movie(query: str = Query(...)):
    docs = await db["cinema"].find({
        "original_title": {"$regex": query, "$options": "i"}
    }).to_list(None)

    results = []
    for doc in docs:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        results.append(doc)
    return {"results": results}

IST = timezone(timedelta(hours=5, minutes=30))

class FeedbackCreate(BaseModel):
    userName: str = Field(..., min_length=1)
    feedback: str = Field(..., min_length=1)

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate):
    feedback_data = {
        "userName": feedback.userName,
        "feedback": feedback.feedback,
        "timeStamp": datetime.now(IST).strftime("%Y-%m-%d %H.%M")

    }

    result = await db["feedback"].insert_one(feedback_data)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Feedback not saved")

    return {"message": "Feedback submitted successfully", "id": str(result.inserted_id)}