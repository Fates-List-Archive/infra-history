from modules.core import *
from ..base import API_VERSION
from config import privacy_policy as pp, rules, policies

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/policies",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Policies"]
)

@router.get("/privacy")
def privacy_policy(request: Request):
    """Returns the privacy policy for fates list as a JSON"""
    return pp

@router.get("/rules")
def rules(request: Request):
    """Returns the rules for fates list as a JSON"""
    return rules

@router.get("/all")
def all_policies(request: Request):
    return policies
