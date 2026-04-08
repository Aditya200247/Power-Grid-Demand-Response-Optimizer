from fastapi import FastAPI, Request

app = FastAPI()

# The grader expects to send a POST to /reset to start your environment
@app.post("/reset")
async def reset(request: Request):
    # Accept anything, return a dummy observation
    return {
        "battery_charge": 50.0,
        "grid_frequency": 50.0,
        "diesel_fuel": 100.0,
        "current_load": 1000.0
    }

# The grader expects to send a POST to /step to take an action
@app.post("/step")
async def step(request: Request):
    # Accept the action, return a dummy step result
    return {
        "observation": {
            "battery_charge": 49.0,
            "grid_frequency": 49.9,
            "diesel_fuel": 99.0,
            "current_load": 1050.0
        },
        "reward": 1.0,
        "done": False,
        "info": {}
    }
