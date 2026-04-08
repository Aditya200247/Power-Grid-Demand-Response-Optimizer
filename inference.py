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

def run_task(client, task_id):
    print(f"[START] Initializing task: {task_id}")
    
    # 1. Reset Environment
    reset_response = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id})
    reset_response.raise_for_status()
    obs = reset_response.json()
    
    done = False
    step_count = 0
    
    system_prompt = (
        "You are a Power Grid AI Manager. Maintain the grid frequency close to 50.0Hz. "
        "You have access to a battery, diesel generators, grid trading, and load shedding. "
        "Keep costs and emissions low, but avoid grid collapse at all costs. "
        "Outputs must be raw valid JSON ONLY, matching exactly this schema: "
        '{"battery_flow": float(-1.0 to 1.0), "diesel_activation": float(0.0 to 1.0), '
        '"grid_trade": float(-1.0 to 1.0), "shed_load_zone": int(0, 1, or 2)}'
    )
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    while not done:
        step_count += 1
        
        # Format observation
        obs_str = json.dumps(obs)
        messages.append({"role": "user", "content": f"Current Observation: {obs_str}"})
        
        try:
            # Action via LLM
            # Basic fallback for parsing error
            fallback_action = {"battery_flow": 0.0, "diesel_activation": 1.0, "grid_trade": 1.0, "shed_load_zone": 0}
            
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.0
            )
            
            action_text = completion.choices[0].message.content.strip()
            
            # Clean possible markdown block
            if action_text.startswith("```json"):
                action_text = action_text[7:-3]
            elif action_text.startswith("```"):
                action_text = action_text[3:-3]
                
            action_dict = json.loads(action_text)
            
        except Exception as e:
            print(f"⚠️ LLM Call Failed: {e}. Using fallback action.")
            # Fallback for LLM failure to keep environment moving
            action_dict = fallback_action
            
        # Ensure we always append assistant response so we don't break LLM state
        messages.append({"role": "assistant", "content": json.dumps(action_dict)})

        # 2. Step Environment
        step_response = requests.post(f"{ENV_URL}/step", json=action_dict)
        step_response.raise_for_status()
        data = step_response.json()
        
        obs = data["observation"]
        reward = data["reward"]
        done = data["done"]
        
        print(f"[STEP] {step_count} | Action: {json.dumps(action_dict)} | Reward: {reward:.4f} | Done: {done}")
        
    # Check final state for score
    state_response = requests.get(f"{ENV_URL}/state")
    final_score = state_response.json().get("score", 0.0)
    
    print(f"[END] Task {task_id} completed. Score: {final_score:.4f}")

if __name__ == "__main__":
    if not HF_TOKEN:
        print("Warning: HF_TOKEN is not set. Inference might fail unless API doesn't require it.")
        
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN or "dummy-key"
    )
    
    tasks = ["easy", "medium", "hard"]
    for task in tasks:
        run_task(client, task)
