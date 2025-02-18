from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from chatbot import app as chatbot_app

app = FastAPI()

# Mount the chatbot routes
app.mount("/api", chatbot_app)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Serve static files if you have any
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
