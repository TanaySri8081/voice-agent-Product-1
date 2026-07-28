"""
Public endpoint exposing the industry (vertical) templates.

Used by the dashboard onboarding (Register) and Settings pages to populate the
industry picker and to pre-fill the system prompt / greeting when a client
applies or switches templates. No authentication is required: the content is
non-sensitive product metadata (no tenant data).
"""

from fastapi import APIRouter

from backend.services.industry_templates import list_templates
from backend.utils.helpers import api_response

router = APIRouter(tags=["Industry Templates"])


@router.get("/industries")
async def get_industries():
    return api_response(
        success=True,
        message="Industry templates fetched successfully",
        data=list_templates(),
    )
