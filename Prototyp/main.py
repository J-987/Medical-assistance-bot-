"""
Entry point — run with:
    uvicorn main:app --reload --port 8000
"""

from app.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
