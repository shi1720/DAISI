"""Start the single-process app locally or in Databricks Apps."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "hawkerbridge.api:create_app",
        factory=True,
        host=os.getenv("HAWKERBRIDGE_BIND", "127.0.0.1")
        if not os.getenv("DATABRICKS_APP_PORT")
        else "0.0.0.0",
        port=int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", "8000"))),
        proxy_headers=bool(os.getenv("DATABRICKS_APP_PORT")),
        forwarded_allow_ips="*" if os.getenv("DATABRICKS_APP_PORT") else "127.0.0.1",
        log_level="info",
    )
