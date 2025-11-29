from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import logging
from pydantic import BaseModel
import asyncio
from quiz_solver import QuizSolver
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

YOUR_EMAIL = os.getenv("EMAIL")
YOUR_SECRET = os.getenv("SECRET")

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.post("/")
async def handle_quiz(request: QuizRequest):
    try:
        if request.secret != YOUR_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret")
        if request.email != YOUR_EMAIL:
            raise HTTPException(status_code=403, detail="Invalid email")
        solver = QuizSolver(YOUR_EMAIL, YOUR_SECRET)
        asyncio.create_task(solver.solve_quiz_chain(request.url))
        return JSONResponse(status_code=200, content={"status": "accepted"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid request")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
