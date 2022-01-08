from ..core import *

router = APIRouter(prefix="/search", tags=["Search"], include_in_schema=False)

# @router.get("/profile")
# async def profile_search(request: Request, q: Optional[str] = None):
#    return await render_profile_search(request = request, q = q, api = False)
