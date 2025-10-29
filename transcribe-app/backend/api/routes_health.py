from fastapi import APIRouter

from ..core.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    try:
        import torch  # type: ignore

        gpu_available = bool(torch.cuda.is_available())
    except Exception:
        gpu_available = False
    return {
        "status": "ok",
        "gpu": gpu_available,
        "model_default": settings.default_model_size,
    }
