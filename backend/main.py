from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.items import router as items_router
from routers.evaluaciones import router as evaluaciones_router
from routers.auth import router as auth_router

app = FastAPI(root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items_router)
app.include_router(evaluaciones_router)
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "Backend funcionando correctamente!"}