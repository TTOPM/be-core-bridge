from fastapi import APIRouter
from fastapi.responses import FileResponse
import pathlib

router = APIRouter()

@router.get("/webui")
def ui_index():
    base = pathlib.Path(__file__).resolve().parents[2] / "webui" / "index.html"
    return FileResponse(str(base))
