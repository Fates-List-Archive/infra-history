# Ratelimits

Ratelimits are applied on data sent over the websocket. A client can get this information from a control packet under the ``requests_remaining`` key. A response by the client to a ``identity`` control packet sent from the server is equivalent to 2 requests.


!!! note
    Further ratelimits may be added to prevent abuse in the future. These *may* be documented as they are implemented.
