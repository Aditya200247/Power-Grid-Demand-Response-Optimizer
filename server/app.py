from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from server.models import TaskDifficulty, PowerGridAction, PowerGridObservation, StepResponse
from server.environment import PowerGridEnv
import uvicorn

app = FastAPI(title="Power Grid Demand-Response Optimizer")

# Global environment instance for single-agent simulation
# In a robust multi-tenant setup, we'd use session IDs.
# For this hackathon, we assume 1 worker = 1 agent.
env = PowerGridEnv()

from typing import Optional

class ResetRequest(BaseModel):
    task_id: Optional[TaskDifficulty] = TaskDifficulty.EASY

@app.get("/")
def read_root():
    """Health check endpoint for Hugging Face Spaces."""
    return {"status": "ok", "environment": "Power Grid Demand-Response Optimizer"}

@app.post("/reset", response_model=PowerGridObservation)
def reset(request: Optional[ResetRequest] = None):
    """Initializes the episode and returns the initial observation."""
    try:
        task_id = request.task_id if request else TaskDifficulty.EASY
        obs = env.reset(task_id)
        return obs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step", response_model=StepResponse)
def step(action: PowerGridAction):
    """Applies an action to the environment."""
    if env.task_id is None:
        raise HTTPException(status_code=400, detail="Environment not resetting. Call /reset first.")
    
    response = env.step(action)
    return response

@app.get("/state")
def state():
    """Returns the current metadata and state of the environment."""
    return env.state()

def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
