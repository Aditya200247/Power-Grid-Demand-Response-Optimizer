# 🚀 Hugging Face Space Setup Guide

## 1. Create a New HF Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Fill in:
   - **Space name**: `power-grid-optimizer` (or your choice)
   - **License**: MIT (or your choice)
   - **Space SDK**: Docker
   - **Visibility**: Public
4. Click **Create Space**

---

## 2. Add Your HF Token as a Secret

1. In your Space, go to **Settings** → **Repository secrets**
2. Add a new secret:
   - **Name**: `HF_TOKEN`
   - **Value**: `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`
3. Save

---

## 3. Push Your Code to the Space

The Space repo will be available at: `https://huggingface.co/spaces/YOUR_USERNAME/power-grid-optimizer`

Clone it:
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/power-grid-optimizer
cd power-grid-optimizer
```

Copy all files from this repo (or add as remote):
```bash
git remote add main https://github.com/YOUR_USERNAME/Power-Grid-Demand-Response-Optimizer
git pull main phase-6-final-build
```

Push to HF Space:
```bash
git push origin main
```

---

## 4. Environment Variables Setup

Your HF Space automatically sets `HF_TOKEN` from secrets. The inference.py will use:

```python
API_BASE_URL = "https://router.huggingface.co/v1"  # HF's default
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"  # Change to your model
HF_TOKEN = os.getenv("HF_TOKEN")  # From secrets
ENV_URL = "http://127.0.0.1:8000"  # Local Docker container
```

To use **OpenAI GPT-4o-mini** instead:
```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="sk-..." # Your OpenAI key (if using OpenAI)
```

---

## 5. File Checklist

Your Space needs these files in the root:

- ✅ `Dockerfile` — Docker image definition
- ✅ `requirements.txt` — Python dependencies
- ✅ `inference.py` — Hackathon inference script
- ✅ `openenv.yaml` — OpenEnv specification
- ✅ `server/app.py` — FastAPI server
- ✅ `server/environment.py` — Physics engine
- ✅ `server/models.py` — Data models
- ✅ `models.py` — Legacy models (for imports)
- ✅ `test_*.py` — Tests (optional for Space)
- ✅ `README.md` — Documentation

---

## 6. Validate Your Submission

Run the validation script locally:

```bash
chmod +x validate-submission.sh
./validate-submission.sh https://YOUR_USERNAME-power-grid-optimizer.hf.space
```

This checks:
1. HF Space is live ✓
2. Docker builds ✓
3. OpenEnv spec is valid ✓

---

## 7. Test Locally (Optional)

Before pushing to HF:

```bash
# Start the server
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000

# In another terminal, run inference
export ENV_URL="http://127.0.0.1:8000"
export MODEL_NAME="gpt-4o-mini"
export API_BASE_URL="https://api.openai.com/v1"
export HF_TOKEN="your_api_key"
python inference.py
```

Expected output:
```
[START] task=easy env=power-grid-optimizer model=gpt-4o-mini
[STEP] step=1 action={"battery_flow":0.0,...} reward=0.95 done=false error=null
[STEP] step=2 action={"battery_flow":0.5,...} reward=0.98 done=false error=null
...
[END] success=true steps=24 score=0.850 rewards=0.95,0.98,...
```

---

## 8. Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker build fails | Check `Dockerfile` syntax, all files present |
| Space won't start | Check `requirements.txt` for missing deps |
| Inference fails | Verify `ENV_URL` points to running server |
| Invalid JSON action | Ensure LLM returns valid JSON format |
| Grid collapse early | Adjust difficulty or agent prompt |

---

## 9. Final Submission

Once validated:
1. Make sure all commits are pushed to HF Space
2. Document any custom setup in README.md
3. Test the `/reset` and `/step` endpoints via curl
4. Submit Space URL to hackathon organizers

**Space URL**: `https://huggingface.co/spaces/YOUR_USERNAME/power-grid-optimizer`

---

Good luck! 🎉
