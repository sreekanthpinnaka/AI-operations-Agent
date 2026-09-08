from app.api.demo import router as demo_router
from app.api.health import router as health_router
from app.api.operations import router as operations_router
from app.api.workflows import router as workflows_router

__all__ = ["health_router", "workflows_router", "operations_router", "demo_router"]

