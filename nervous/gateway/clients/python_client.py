"""Python client for the SuneelWorkSpace Agent API Gateway."""
import os
import json
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


class WorkspaceClient:
    """Simple Python client for the workspace gateway (port 8888)."""

    def __init__(self, base_url: str = "http://localhost:8888", token: str = None):
        self.base_url = base_url.rstrip('/')
        if token is None:
            token_file = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace')) / 'nervous/gateway/.token'
            token = token_file.read_text().strip() if token_file.exists() else ""
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def _get(self, path: str, params: dict = None):
        if requests is None:
            raise RuntimeError("pip3 install requests")
        r = requests.get(f"{self.base_url}{path}", headers=self.headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, params: dict = None, data=None):
        if requests is None:
            raise RuntimeError("pip3 install requests")
        r = requests.post(f"{self.base_url}{path}", headers=self.headers, params=params, json=data, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_health(self):
        return self._get("/health")

    def search_memory(self, query: str, k: int = 5):
        return self._get("/memory/search", params={"q": query, "k": k})

    def get_facts(self):
        return self._get("/memory/facts")

    def get_decisions(self):
        return self._get("/memory/decisions")

    def get_suggestions(self):
        return self._get("/brain/anticipation/suggestions")

    def create_goal(self, description: str, confirm: bool = False):
        return self._post("/goals/create", params={"description": description, "confirm": confirm})

    def list_workflows(self):
        return self._get("/workflows/list")

    def get_active_goals(self):
        return self._get("/goals/active")

    def search_arxiv(self, query: str):
        return self._post("/research/arxiv", params={"query": query})


if __name__ == '__main__':
    client = WorkspaceClient()
    print(json.dumps(client.get_health(), indent=2))
