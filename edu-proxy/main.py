import os
import json
import time
import hashlib
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import httpx
from fastapi import FastAPI, HTTPException, Request, Query, Form, Body
from fastapi.responses import (
    HTMLResponse, 
    JSONResponse, 
    Response, 
    StreamingResponse,
    RedirectResponse,
    PlainTextResponse
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from bs4 import BeautifulSoup
import aiofiles
import asyncio

# 初始化 FastAPI
app = FastAPI(
    title="教务系统代理服务",
    description="代理访问 http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
BASE_URL = "http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/"
TARGET_DOMAIN = "qzjw.bwgl.cn"
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# 创建静态文件和模板目录
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# HTTP客户端实例
_client = None

async def get_http_client():
    """获取HTTP客户端"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            follow_redirects=True
        )
    return _client

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    global _client
    if _client:
        await _client.aclose()

# 缓存管理
def get_cache_key(url: str) -> str:
    """生成缓存键"""
    return hashlib.md5(url.encode()).hexdigest()

async def get_cached_response(url: str, expire_seconds: int = 300) -> Optional[Dict]:
    """获取缓存响应"""
    cache_key = get_cache_key(url)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    try:
        if os.path.exists(cache_file):
            file_stat = os.stat(cache_file)
            if time.time() - file_stat.st_mtime < expire_seconds:
                async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
    except Exception as e:
        print(f"读取缓存失败: {e}")
    return None

async def save_cached_response(url: str, data: Dict, expire_seconds: int = 300):
    """保存缓存响应"""
    cache_key = get_cache_key(url)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    try:
        async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False))
    except Exception as e:
        print(f"保存缓存失败: {e}")

# 1. 健康检查接口（Railway 需要）
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": time.time()}

# 2. 主页
@app.get("/")
async def home():
    """代理服务主页"""
    return {
        "service": "教务系统代理服务",
        "target": BASE_URL,
        "endpoints": {
            "proxy": "/proxy/{path} - 通用代理",
            "fetch": "/fetch?url={path} - 获取页面",
            "api": "/api/{path} - API接口代理",
            "static": "/resource?url={path} - 静态资源",
            "analyze": "/analyze - 网站分析",
            "health": "/health - 健康检查"
        }
    }

# 3. 通用代理接口
@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_all(path: str, request: Request):
    """通用代理接口，支持所有HTTP方法"""
    try:
        # 构建目标URL
        target_url = urljoin(BASE_URL, path)
        
        # 获取查询参数
        query_params = dict(request.query_params)
        
        # 准备请求头
        headers = {}
        exclude_headers = ['host', 'content-length', 'connection', 'accept-encoding']
        for key, value in request.headers.items():
            key_lower = key.lower()
            if key_lower not in exclude_headers:
                headers[key] = value
        
        # 处理请求体
        body = None
        content_type = request.headers.get('content-type', '')
        if request.method in ["POST", "PUT", "PATCH"]:
            if content_type:
                if 'application/json' in content_type:
                    body = await request.json()
                elif 'application/x-www-form-urlencoded' in content_type:
                    form_data = await request.form()
                    body = dict(form_data)
                elif 'multipart/form-data' in content_type:
                    form_data = await request.form()
                    body = dict(form_data)
                else:
                    body = await request.body()
        
        client = await get_http_client()
        
        # 发送请求
        response = await client.request(
            method=request.method,
            url=target_url,
            params=query_params,
            headers=headers,
            json=body if isinstance(body, dict) and 'application/json' in content_type else None,
            data=body if isinstance(body, (dict, str)) and 'application/json' not in content_type else None,
            content=body if isinstance(body, bytes) else None
        )
        
        # 处理响应
        response_headers = dict(response.headers)
        
        # 移除一些不需要的头部
        response_headers.pop('content-encoding', None)
        response_headers.pop('transfer-encoding', None)
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")

# 4. 简单的页面获取接口
@app.get("/fetch")
async def fetch_page(
    url: str = Query(..., description="要获取的页面URL（相对或绝对路径）"),
    use_cache: bool = Query(False, description="是否使用缓存"),
    refresh: bool = Query(False, description="强制刷新缓存")
):
    """获取网页内容"""
    try:
        # 处理URL
        if not url.startswith(('http://', 'https://')):
            target_url = urljoin(BASE_URL, url)
        else:
            target_url = url
        
        # 检查缓存
        if use_cache and not refresh:
            cached = await get_cached_response(target_url)
            if cached:
                return JSONResponse(content=cached)
        
        client = await get_http_client()
        response = await client.get(target_url)
        
        # 构建响应数据
        result = {
            "url": target_url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text,
            "timestamp": time.time()
        }
        
        # 保存缓存
        if use_cache:
            await save_cached_response(target_url, result)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取页面失败: {str(e)}")

# 5. API接口代理（专门处理JSON数据）
@app.api_route("/api/{path:path}", methods=["GET", "POST"])
async def api_proxy(path: str, request: Request):
    """API接口代理"""
    try:
        target_url = urljoin(BASE_URL, path)
        
        client = await get_http_client()
        
        # 根据请求方法发送请求
        if request.method == "GET":
            query_params = dict(request.query_params)
            response = await client.get(target_url, params=query_params)
        else:
            body = await request.json()
            response = await client.post(target_url, json=body)
        
        # 尝试解析为JSON
        try:
            data = response.json()
            return JSONResponse(content=data)
        except:
            return PlainTextResponse(content=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API代理失败: {str(e)}")

# 6. 静态资源代理
@app.get("/resource")
async def proxy_resource(url: str = Query(...)):
    """代理静态资源（CSS、JS、图片等）"""
    try:
        if not url.startswith(('http://', 'https://')):
            target_url = urljoin(BASE_URL, url)
        else:
            target_url = url
        
        client = await get_http_client()
        response = await client.get(target_url)
        
        # 确定Content-Type
        content_type = response.headers.get('content-type', 'application/octet-stream')
        
        return Response(
            content=response.content,
            media_type=content_type,
            headers={
                'Cache-Control': 'public, max-age=86400'
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资源失败: {str(e)}")

# 7. 网站分析接口
@app.get("/analyze")
async def analyze_site():
    """分析目标网站结构"""
    try:
        client = await get_http_client()
        response = await client.get(BASE_URL)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取信息
        result = {
            "base_url": BASE_URL,
            "title": soup.title.string if soup.title else "无标题",
            "meta_tags": [],
            "links": [],
            "forms": [],
            "scripts": [],
            "stylesheets": []
        }
        
        # 提取meta标签
        for meta in soup.find_all('meta'):
            meta_info = {attr: meta.get(attr) for attr in meta.attrs}
            result["meta_tags"].append(meta_info)
        
        # 提取链接
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href:
                full_url = urljoin(BASE_URL, href)
                result["links"].append({
                    "text": link.get_text(strip=True),
                    "href": href,
                    "full_url": full_url
                })
        
        # 提取表单
        for form in soup.find_all('form'):
            form_info = {
                "action": form.get('action', ''),
                "method": form.get('method', 'get').upper(),
                "inputs": []
            }
            
            for input_tag in form.find_all(['input', 'textarea', 'select']):
                input_info = {
                    "type": input_tag.get('type', input_tag.name),
                    "name": input_tag.get('name', ''),
                    "value": input_tag.get('value', ''),
                    "placeholder": input_tag.get('placeholder', '')
                }
                form_info["inputs"].append(input_info)
            
            result["forms"].append(form_info)
        
        # 提取脚本
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src:
                result["scripts"].append(urljoin(BASE_URL, src))
        
        # 提取样式表
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                result["stylesheets"].append(urljoin(BASE_URL, href))
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析网站失败: {str(e)}")

# 8. 直接HTML渲染（用于浏览器访问）
@app.get("/view/{path:path}")
async def view_page(path: str, request: Request):
    """直接在浏览器中查看页面（处理相对链接）"""
    try:
        target_url = urljoin(BASE_URL, path)
        
        client = await get_http_client()
        response = await client.get(target_url)
        
        html_content = response.text
        
        # 修复相对链接（简单处理）
        html_content = html_content.replace('href="/', f'href="/view/')
        html_content = html_content.replace('src="/', f'src="/resource?url=/')
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        return HTMLResponse(f"""
            <html>
                <body>
                    <h1>页面加载失败</h1>
                    <p>错误: {str(e)}</p>
                    <p>URL: {path}</p>
                    <a href="/">返回首页</a>
                </body>
            </html>
        """)

# 错误处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "未找到", "path": request.url.path}
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误", "detail": str(exc)}
    )

# 启动应用
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )