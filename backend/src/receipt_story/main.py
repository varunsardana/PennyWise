from dotenv import load_dotenv
load_dotenv()  # Load env vars BEFORE other imports

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from receipt_story.core.logging import configure_logging
from receipt_story.api.health import router as health_router
from receipt_story.api.routes_receipts import router as receipts_router
from receipt_story.api.routes_insights import router as insights_router
from receipt_story.api.routes_advisor import router as advisor_router

from receipt_story.api.routes_trends import router as trends_router
from receipt_story.api.routes_chatbot import router as chatbot_router
from receipt_story.api.routes_planning import router as planning_router
from receipt_story.api.routes_dispatcher import router as dispatcher_router

logger = configure_logging()

def create_app() -> FastAPI:
    app = FastAPI(title="Receipt Story Backend", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)
    app.include_router(receipts_router)
    app.include_router(insights_router)
    app.include_router(advisor_router)
    app.include_router(trends_router)
    app.include_router(chatbot_router)
    app.include_router(planning_router)
    app.include_router(dispatcher_router)

    @app.on_event("startup")
    def _startup():
        logger.info("Backend starting up...")

    return app

app = create_app()
