import os
import requests
import json
from openai import OpenAI

# Environment setup
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")

# The URL of the local or deployed environment
ENV_URL = os.getenv("ENV_URL", "http://127.0.0.1:8000")
BENCHMARK = "power-grid-optimizer"
SUCCESS_SCORE_THRESHOLD = 0.5  # Passing score

def run_task(client, task_id):
    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)
    
    # 1. Reset Environment
    reset_response = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id})
    reset_response.raise_for_status()
    obs = reset_response.json()
    
    done = False
    step_count = 0
    rewards = []
    
    system_prompt = (
        "You are a Power Grid AI Manager. Maintain the grid frequency close to 50.0Hz. "
        "You have access to a battery, diesel generators, grid trading, and load shedding. "
        "Outputs must be raw valid JSON ONLY, matching exactly this schema: "
        '{"battery_flow": float(-1.0 to 1.0), "diesel_activation": float(0.0 to 1.0), '
        '"grid_trade": float(-1.0 to 1.0), "shed_load_zone": int(0, 1, or 2)}'
    )
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    while not done:
        step_count += 1
        error_val = None
        
        # Format observation
        obs_str = json.dumps(obs)
        messages.append({"role": "user", "content": f"Current Observation: {obs_str}"})
        
        fallback_action = {"battery_flow": 0.0, "diesel_activation": 1.0, "grid_trade": 1.0, "shed_load_zone": 0}
        
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.0
            )
            
            action_text = completion.choices[0].message.content.strip()
            
            if action_text.startswith("```json"):
                action_text = action_text[7:-3]
            elif action_text.startswith("```"):
                action_text = action_text[3:-3]
                
            action_dict = json.loads(action_text)
            action_str = json.dumps(action_dict).replace(" ", "")
            
        except Exception as e:
            error_val = str(e)
            action_dict = fallback_action
            action_str = json.dumps(action_dict).replace(" ", "")
            
        messages.append({"role": "assistant", "content": json.dumps(action_dict)})

        # 2. Step Environment
        try:
            step_response = requests.post(f"{ENV_URL}/step", json=action_dict)
            step_response.raise_for_status()
            data = step_response.json()
            
            obs = data["observation"]
            reward = float(data["reward"])
            done = data["done"]
        except Exception as e:
            error_val = str(e)
            reward = 0.0
            done = True
        
        rewards.append(reward)
        done_str = str(done).lower()
        err_str = f"\"{error_val}\"" if error_val else "null"
        
        print(f"[STEP] step={step_count} action={action_str} reward={reward:.2f} done={done_str} error={err_str}", flush=True)
        
    # Check final state for score
    try:
        state_response = requests.get(f"{ENV_URL}/state")
        final_score = state_response.json().get("score", 0.0)
    except:
        final_score = 0.0
        
    success = final_score >= SUCCESS_SCORE_THRESHOLD
    success_str = str(success).lower()
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    
    print(f"[END] success={success_str} steps={step_count} score={final_score:.3f} rewards={rewards_str}", flush=True)

if __name__ == "__main__":
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN or "dummy-key"
    )
    
    tasks = ["easy", "medium", "hard"]
    for task in tasks:
        run_task(client, task)
