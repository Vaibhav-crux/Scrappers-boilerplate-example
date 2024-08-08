from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    """Root API to indicate the application is running."""
    return {"message": "API is running!"}
