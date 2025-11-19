from fastapi import FastAPI
from database import engine, Base

app = FastAPI()

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Backend funcionando correctamente!"}
