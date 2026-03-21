from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.db.database import init_db
from backend.routes.workout import router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.include_router(router)


@app.on_event("startup")
def startup():
    init_db()
