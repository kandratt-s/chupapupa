import httpx
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI()

ROUTES = {
    "auth-service": "http://localhost:8001",
    "admin-service": "http://localhost:8002",
    "attendance-service": "http://localhost:8003",
    "event-service": "http://localhost:8006",
    "user_statistic-service": "http://localhost:8007",
}


@app.api_route("/{service}/{path:path}", methods=["GET", "PUT", "POST", "DELETE"])
async def gateway(service: str, path: str, request: Request) -> Response:
    if service not in ROUTES:
        raise HTTPException(status_code=404, detail="Unknown service")

    target = f"{ROUTES[service]}/{path}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target,
                headers=request.headers,
                content=await request.body(),
            )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )
    except httpx.ConnectError as err:
        raise HTTPException(status_code=503, detail="Service unavailable") from err
    except httpx.TimeoutException as err:
        raise HTTPException(status_code=504, detail="Service timeout") from err
