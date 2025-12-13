from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

ROUTES = {
    "auth": "http://localhost:8001",
    "api": "http://localhost:8002",
    "events": "http://localhost:8003",
    "attendance": "http://localhost:8004",
    "statistics": "http://localhost:8005",
    "storage": "http://localhost:8006",
}


@app.api_route("/{service}/{path:path}", methods=["GET", "PUT", "POST", "DELETE"])
async def gateway(service: str, path: str, request: Request):
    if service not in ROUTES:
        raise HTTPException(status_code=404, detail="Unknown service")

    target = f"{ROUTES[service]}/{path}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target,
                headers=request.headers,
                content=await request.body
            )
        return response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
