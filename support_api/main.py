# support_api/main.py

from datetime import datetime
import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel
from pymongo import MongoClient

# -------------------------------------------------------
# ENV + MONGO CLIENT
# -------------------------------------------------------

load_dotenv()

MONGO_URI = os.getenv("SHOPFLOW_MONGO_URI")
DB_NAME = os.getenv("SHOPFLOW_DB_NAME", "shopflow")
COLLECTION_NAME = os.getenv("SHOPFLOW_TICKETS_COLLECTION", "support_tickets")
API_KEY = os.getenv("SHOPFLOW_API_KEY")  # simple header-based auth

if not MONGO_URI:
    raise RuntimeError("SHOPFLOW_MONGO_URI is not set. Check your .env file.")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
tickets_col = db[COLLECTION_NAME]

app = FastAPI(
    title="ShopFlow Support Tickets API",
    description=(
        "API giving access to support_tickets stored in MongoDB. "
        "Designed so Data Engineers can pull tickets via HTTP and join with RDS data."
    ),
    version="1.0.0",
)


# -------------------------------------------------------
# SECURITY (simple API key in header)
# -------------------------------------------------------

def require_api_key(x_api_key: str = Header(default=None)):
    if API_KEY is None:
        # if no key configured, treat as open (dev mode)
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# -------------------------------------------------------
# RESPONSE MODELS
# -------------------------------------------------------

class Ticket(BaseModel):
    ticket_id: str
    customer_id: str
    customer_segment: Optional[str] = None
    created_date: datetime
    resolved_date: Optional[datetime] = None
    issue_type: str
    issue_category: str
    priority: str
    status: str
    resolution_hours: Optional[int] = None
    satisfaction_score: Optional[float] = None
    agent_id: str
    description: str
    order_id: Optional[str] = None
    product_id: Optional[str] = None


class TicketsPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[Ticket]


# -------------------------------------------------------
# HELPERS
# -------------------------------------------------------

def _build_ticket_filter(
    customer_id: Optional[str],
    segment: Optional[str],
    status: Optional[str],
    priority: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
):
    query = {}

    if customer_id:
        query["customer_id"] = customer_id
    if segment:
        query["customer_segment"] = segment
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority

    # created_date range filter
    if from_date or to_date:
        created_filter = {}
        if from_date:
            created_filter["$gte"] = datetime.fromisoformat(from_date)
        if to_date:
            created_filter["$lte"] = datetime.fromisoformat(to_date)
        query["created_date"] = created_filter

    return query


def _serialize_ticket(doc) -> Ticket:
    doc["_id"] = str(doc["_id"])  # not exposed in model but we can keep it
    return Ticket(**doc)


# -------------------------------------------------------
# ENDPOINTS
# -------------------------------------------------------

@app.get("/health", dependencies=[Depends(require_api_key)])
def health():
    """Basic health check."""
    count = tickets_col.estimated_document_count()
    return {"status": "ok", "tickets_estimate": count}


@app.get(
    "/tickets",
    response_model=TicketsPage,
    dependencies=[Depends(require_api_key)],
)
def list_tickets(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    customer_id: Optional[str] = Query(default=None),
    segment: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(
        default=None,
        description="Start ISO date, e.g. 2023-01-01",
    ),
    to_date: Optional[str] = Query(
        default=None,
        description="End ISO date, e.g. 2023-12-31",
    ),
):
    """
    List support tickets with filters and pagination.

    DE usage examples:
    - GET /tickets?limit=100
    - GET /tickets?customer_id=CUST000123
    - GET /tickets?segment=Churned&status=Resolved&from_date=2023-01-01
    """

    query = _build_ticket_filter(
        customer_id=customer_id,
        segment=segment,
        status=status,
        priority=priority,
        from_date=from_date,
        to_date=to_date,
    )

    total = tickets_col.count_documents(query)
    cursor = (
        tickets_col.find(query)
        .sort("created_date", 1)
        .skip(offset)
        .limit(limit)
    )

    items = [_serialize_ticket(doc) for doc in cursor]

    return TicketsPage(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@app.get(
    "/customers/{customer_id}/tickets",
    response_model=TicketsPage,
    dependencies=[Depends(require_api_key)],
)
def tickets_for_customer(
    customer_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get all tickets for a particular customer.

    Usage: GET /customers/CUST000123/tickets
    """
    query = {"customer_id": customer_id}
    total = tickets_col.count_documents(query)
    cursor = (
        tickets_col.find(query)
        .sort("created_date", -1)
        .skip(offset)
        .limit(limit)
    )
    items = [_serialize_ticket(doc) for doc in cursor]
    return TicketsPage(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )
