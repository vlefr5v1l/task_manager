from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.api.v1.router import api_router
import asyncio
from src.messaging.consumers import start_consumers
from src.messaging.producers import close_kafka_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumers_task = asyncio.create_task(start_consumers())
    yield
    await close_kafka_producer()


app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json", lifespan=lifespan)

# Set CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"message": "Welcome to Task Management System"}
