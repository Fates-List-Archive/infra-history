**Here is a incomplete list of status codes emitted from our API**

200 - Success

404 - Not Found

400 - Error in processing request/misc error/Invalid Input

401/403 - Unauthorized Request/Bad Token

408 - Site down for maintenance/Critical error in request

429 - Ratelimited

**A 500 should not be possible on API v3, instead critical errors will return a 408** 