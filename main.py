# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from urllib.parse import urljoin
import os

app = FastAPI(title="教务代理服务")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/"

@app.get("/")
async def root():
    return {
        "service": "教务系统代理",
        "target": BASE_URL,
        "status": "running",
        "endpoints": [
            "/proxy/{path} - 通用代理",
            "/health - 健康检查",
            "/docs - API文档"
        ]
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.api_route("/proxy/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request):
    try:
        # 构建目标URL
        target_url = urljoin(BASE_URL, path)
        
        # 获取查询参数
        query_params = dict(request.query_params)
        
        # 准备请求头
        headers = {k: v for k, v in request.headers.items() 
                  if k.lower() not in ['host', 'content-length']}
        
        # 处理请求体
        body = None
        if request.method == "POST":
            content_type = request.headers.get('content-type', '')
            if 'application/json' in content_type:
                body = await request.json()
            else:
                body = await request.body()
        
        # 使用httpx发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                params=query_params,
                headers=headers,
                json=body if isinstance(body, dict) else None,
                content=body if isinstance(body, bytes) else None
            )
        
        # 返回响应
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)