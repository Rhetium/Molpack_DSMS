from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def read_health():
    return {"status": "ok", "service": "dsms-backend"}
