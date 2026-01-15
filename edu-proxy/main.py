"""
教务系统代理服务器 - Python 3.8兼容版
确保在Python 3.8和Railway上都能正常运行
"""
import sys
print(f"Python版本: {sys.version}")

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import requests
    from bs4 import BeautifulSoup
    import uvicorn
    print("✓ 所有依赖包导入成功")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("请运行: pip install -r requirements.txt")
    sys.exit(1)

# 创建应用
app = FastAPI(title="教务代理", version="1.0")

# 允许跨域（鸿蒙App需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    """首页"""
    return {
        "service": "教务系统代理API",
        "python_version": sys.version.split()[0],
        "status": "运行正常",
        "endpoints": {
            "/test": "测试教务网站连接",
            "/simple": "简单数据接口"
        }
    }

@app.get("/test")
def test_connection():
    """测试是否能访问教务网站"""
    try:
        url = "http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/"
        # 使用较短的超时时间
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": "可以访问教务网站",
                "status_code": response.status_code,
                "content_length": len(response.text)
            }
        else:
            return {
                "success": False,
                "message": f"网站返回 {response.status_code}",
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)[:100]}",  # 只显示前100字符
            "error_type": type(e).__name__
        }

@app.get("/simple")
def simple_data():
    """返回简单数据（用于测试API是否工作）"""
    return {
        "success": True,
        "data": {
            "courses": [
                {"name": "测试课程1", "time": "周一 1-2节", "location": "A101"},
                {"name": "测试课程2", "time": "周二 3-4节", "location": "B202"}
            ],
            "notices": [
                {"title": "测试通知1", "date": "2024-01-15"},
                {"title": "测试通知2", "date": "2024-01-16"}
            ]
        },
        "note": "这是测试数据，实际数据需要连接教务系统获取"
    }

@app.get("/check-website")
def check_website_structure():
    """查看网站结构（用于调试）"""
    try:
        url = "http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            # 使用BeautifulSoup解析
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 收集基本信息
            info = {
                "title": str(soup.title)[:100] if soup.title else "无标题",
                "forms_count": len(soup.find_all('form')),
                "tables_count": len(soup.find_all('table')),
                "has_login_form": any('login' in str(form).lower() or 
                                     '密码' in str(form) or 
                                     'user' in str(form).lower() 
                                     for form in soup.find_all('form')),
                "sample_html": response.text[:500]  # 前500字符
            }
            
            return {
                "success": True,
                "website_info": info,
                "tip": "根据这些信息可以设计登录逻辑"
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:200]
        }

if __name__ == "__main__":
    print("=" * 50)
    print("教务代理服务器启动")
    print(f"Python版本: {sys.version}")
    print("访问地址: http://localhost:8000")
    print("测试接口: http://localhost:8000/test")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)