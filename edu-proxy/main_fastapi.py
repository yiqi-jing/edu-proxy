"""
专门为PythonAnywhere优化的FastAPI服务器
"""
import sys
import os

# 添加当前路径到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"当前目录: {current_dir}")
print(f"Python路径: {sys.path}")

try:
    # 先导入核心库
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    
    # 这里使用 starlette 的 WSGI 适配器
    from starlette.middleware.wsgi import WSGIMiddleware
    from fastapi.responses import JSONResponse
    
    print("✓ 依赖库导入成功")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()

# 创建应用
app = FastAPI(title="教务代理-PythonAnywhere", version="1.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 路由定义 ============
@app.get("/")
async def root():
    """首页"""
    return JSONResponse({
        "service": "教务代理API (PythonAnywhere版)",
        "status": "运行正常",
        "python_version": sys.version,
        "endpoints": [
            "/test - 测试连接",
            "/health - 健康检查"
        ]
    })

@app.get("/test")
async def test():
    """测试端点"""
    return JSONResponse({
        "success": True,
        "message": "PythonAnywhere服务器正常工作",
        "timestamp": "2024-01-15T10:00:00"
    })

@app.get("/health")
async def health():
    """健康检查"""
    return JSONResponse({
        "status": "healthy",
        "service": "edu-proxy"
    })

# PythonAnywhere需要这个
application = app