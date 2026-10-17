from backend.routes.video.routes import router as video_router
from backend.routes.chat.routes import router as chat_router
from backend.routes.summary.routes import router as summary_router
from backend.routes.redis.routes import router as redis_router
from backend.routes.health.routes import router as health_router

__all__ = [
    "video_router",
    "chat_router",
    "summary_router",
    "redis_router",
    "health_router",
]
