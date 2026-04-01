"""Server entrypoint that reads PORT from environment."""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Starting uvicorn on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
