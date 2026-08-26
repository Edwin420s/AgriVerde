from fastapi import APIRouter
router = APIRouter()
@router.get("/users/me")
def get_me():
    return {"user": "current user"}