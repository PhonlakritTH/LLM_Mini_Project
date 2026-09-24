from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .graph import run_agent
from .state import AgentRequest, AgentResult

app = FastAPI(title="PC Build AI Agent", version="1.0")

@app.post("/v1/agent/run", response_model=AgentResult)
async def run(req: AgentRequest, x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:      # only the backend may call the agent
        raise HTTPException(401, "UNAUTHORIZED")
    return await run_agent(req)

@app.get("/health")
def health(): return {"status": "ok", "prompt_version": settings.prompt_version, "policy_version": settings.policy_version}
