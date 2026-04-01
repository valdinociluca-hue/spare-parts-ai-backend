"""
app/api/routes/requests.py — Internal request management endpoints.

Used by the team's internal tooling or a future admin UI to:
- List and filter incoming requests
- Retrieve a specific request with its classification and draft reply
- Manually trigger reprocessing of a failed request
- Approve or reject a draft reply before it is sent

These endpoints are authenticated (JWT or API key) and are
never exposed to customers.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("")
async def list_requests():
    """List recent requests with optional filters (status, category, channel)."""
    # TODO: inject repository, apply filters, return paginated list
    raise NotImplementedError


@router.get("/{request_id}")
async def get_request(request_id: str):
    """Get a single request with classification result and draft reply."""
    # TODO: fetch from DB, return full detail view
    raise NotImplementedError


@router.post("/{request_id}/reprocess")
async def reprocess_request(request_id: str):
    """Re-run the classification pipeline for a request (e.g. after LLM failure)."""
    # TODO: enqueue reprocessing job
    raise NotImplementedError
