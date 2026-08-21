"""
Suppression API Endpoints

Manages the global suppression list for opt-outs and bounces.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_suppression_list():
    """Get suppression list."""
    return {"message": "Suppression list - to be implemented"}


@router.post("")
async def add_to_suppression():
    """Add email/domain to suppression list."""
    return {"message": "Add to suppression - to be implemented"}


@router.delete("/{item_id}")
async def remove_from_suppression(item_id: int):
    """Remove item from suppression list."""
    return {"message": f"Remove {item_id} from suppression - to be implemented"}


@router.post("/import")
async def import_suppression():
    """Import suppression list from CSV."""
    return {"message": "Import suppression - to be implemented"}


@router.get("/export")
async def export_suppression():
    """Export suppression list to CSV."""
    return {"message": "Export suppression - to be implemented"}
