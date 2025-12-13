from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
import logging
from pydantic import BaseModel, ValidationError
import asyncio
from quiz_solver import QuizSolver
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

YOUR_EMAIL = os.getenv("EMAIL")
YOUR_SECRET = os.getenv("SECRET")

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.post("/")
async def handle_quiz(request: Request):
    try:
        try:
            body = await request.json()
        except Exception as e:
            logger.error(f"Invalid JSON: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        try:
            quiz_request = QuizRequest(**body)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid request format")
        
        if quiz_request.secret != YOUR_SECRET:
            logger.warning(f"Invalid secret provided")
            raise HTTPException(status_code=403, detail="Invalid secret")
        
        if quiz_request.email != YOUR_EMAIL:
            logger.warning(f"Invalid email provided")
            raise HTTPException(status_code=403, detail="Invalid email")
        
        logger.info(f"Starting quiz chain from URL: {quiz_request.url}")
        solver = QuizSolver(YOUR_EMAIL, YOUR_SECRET)
        asyncio.create_task(solver.solve_quiz_chain(quiz_request.url))
        
        return JSONResponse(
            status_code=200,
            content={"status": "accepted", "message": "Quiz solving started"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    return {"status": "online", "message": "Quiz solver API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "email": YOUR_EMAIL,
        "secret_configured": bool(YOUR_SECRET)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
