# main.py - 简化稳定版
import os
import json
import httpx
import asyncio
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# 初始化应用
app = FastAPI(
    title="教务系统代理",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None
)

# 跨域设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
BASE_URL = "http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/"

# 创建HTTP客户端会话
class HttpClient:
    _client: Optional[httpx.AsyncClient] = None
    
    @classmethod
    async def get_client(cls):
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Connection": "keep-alive",
                },
                follow_redirects=True,
                verify=False
            )
        return cls._client
    
    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.aclose()

# 应用生命周期
@app.on_event("startup")
async def startup_event():
    print("🚀 教务代理服务启动")
    print(f"📡 代理目标: {BASE_URL}")
    print(f"🔧 Python版本: 3.8")

@app.on_event("shutdown")
async def shutdown_event():
    await HttpClient.close()
    print("👋 服务关闭")

# 1. 首页
@app.get("/")
async def root():
    """服务首页"""
    return {
        "service": "教务系统代理服务",
        "status": "running",
        "proxy_target": BASE_URL,
        "endpoints": {
            "GET /health": "健康检查",
            "GET /proxy/{path}": "通用代理接口",
            "GET /api/{path}": "API代理接口",
            "GET /fetch": "获取页面内容",
            "GET /analyze": "分析网站结构"
        },
        "docs": "/docs"
    }

# 2. 健康检查（Railway必须）
@app.get("/health")
async def health():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "service": "edu-proxy"
    }

# 3. 核心代理接口
@app.api_route("/proxy/{path:path}", methods=["GET", "POST"])
async def proxy_handler(
    path: str,
    request: Request,
    action: Optional[str] = Query(None),
    oper: Optional[str] = Query(None)
):
    """
    通用代理处理器
    path: 目标路径，如：xkglAction.do
    action/oper: 教务系统常用参数
    """
    try:
        # 构建目标URL
        target_url = urljoin(BASE_URL, path)
        
        # 处理查询参数
        query_params = dict(request.query_params)
        
        # 处理POST数据
        body = None
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.json()
            elif "application/x-www-form-urlencoded" in content_type:
                form_data = await request.form()
                body = dict(form_data)
            else:
                body = await request.body()
        
        # 获取HTTP客户端
        client = await HttpClient.get_client()
        
        # 发送请求
        response = await client.request(
            method=request.method,
            url=target_url,
            params=query_params,
            json=body if isinstance(body, dict) else None,
            data=body if isinstance(body, (dict, str)) else None,
            content=body if isinstance(body, bytes) else None
        )
        
        # 返回响应
        response_headers = dict(response.headers)
        
        # 移除不需要的头部
        for key in ["content-encoding", "transfer-encoding"]:
            response_headers.pop(key, None)
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers
        )
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"请求目标网站失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"代理处理错误: {str(e)}")

# 4. 简化版页面获取
@app.get("/fetch")
async def fetch_page(
    url: str = Query(..., description="要获取的URL路径"),
    format: str = Query("json", description="返回格式: json 或 html")
):
    """获取页面内容"""
    try:
        # 处理URL
        if not url.startswith("http"):
            target_url = urljoin(BASE_URL, url)
        else:
            target_url = url
        
        client = await HttpClient.get_client()
        response = await client.get(target_url)
        
        if format == "html":
            return HTMLResponse(content=response.text)
        
        return {
            "url": target_url,
            "status_code": response.status_code,
            "content_length": len(response.content),
            "headers": dict(response.headers),
            "preview": response.text[:500] + "..." if len(response.text) > 500 else response.text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. 网站结构分析
@app.get("/analyze")
async def analyze():
    """分析目标网站结构"""
    try:
        client = await HttpClient.get_client()
        response = await client.get(BASE_URL)
        
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 基本信息
        result = {
            "base_url": BASE_URL,
            "title": soup.title.string if soup.title else "无标题",
            "has_login_form": False,
            "links_count": 0,
            "forms_count": 0
        }
        
        # 查找登录表单
        forms = soup.find_all('form')
        result["forms_count"] = len(forms)
        
        for form in forms:
            form_html = str(form).lower()
            if any(keyword in form_html for keyword in ['login', 'logon', 'signin', 'password']):
                result["has_login_form"] = True
                result["login_action"] = form.get('action', '')
                break
        
        # 提取链接
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href and not href.startswith(('javascript:', '#')):
                full_url = urljoin(BASE_URL, href)
                links.append({
                    "text": a.get_text(strip=True)[:50],
                    "href": href,
                    "full_url": full_url
                })
        
        result["links_count"] = len(links)
        result["sample_links"] = links[:10]  # 只返回前10个
        
        # 提取可能的API端点
        patterns = [
            r'(\w+Action\.do\??\w*=?\w*)',
            r'(\w+\.action\??\w*=?\w*)',
            r'(\w+\.jsp\??\w*=?\w*)',
            r'(\w+\.aspx\??\w*=?\w*)'
        ]
        
        endpoints = set()
        for pattern in patterns:
            matches = re.findall(pattern, response.text)
            endpoints.update(matches)
        
        result["endpoints"] = list(endpoints)[:20]  # 最多返回20个
        
        return result
        
    except Exception as e:
        return {"error": str(e), "base_url": BASE_URL}

# 6. 测试教务系统常用接口
@app.get("/test/common")
async def test_common_endpoints():
    """测试教务系统常用接口"""
    endpoints = [
        "xkglAction.do?oper=xkgl_ckKb",      # 查看课表
        "xkglAction.do?oper=xkgl_cxXsxk",    # 学生选课
        "xsxkAction.do",                     # 学生选课主页面
        "gradeLnAllAction.do",               # 成绩查询
        "xsdjAction.do",                     # 学生登记
        "xskbcxAction.do",                   # 学生课表查询
    ]
    
    results = []
    client = await HttpClient.get_client()
    
    for endpoint in endpoints[:3]:  # 只测试前3个避免超时
        try:
            url = urljoin(BASE_URL, endpoint)
            response = await client.get(url, timeout=10.0)
            results.append({
                "endpoint": endpoint,
                "status": response.status_code,
                "size": len(response.content),
                "title": BeautifulSoup(response.text, 'html.parser').title.string if BeautifulSoup(response.text, 'html.parser').title else "无标题"
            })
        except Exception as e:
            results.append({
                "endpoint": endpoint,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "tested": len(results),
        "results": results
    }

# 错误处理
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "接口不存在", "path": request.url.path}
    )

# 主程序入口
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        workers=1  # Railway建议使用1个worker
    )