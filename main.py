"""
最简单的教务系统代理服务器
作者：新手友好版
功能：获取公开的教务通知（无需登录测试）
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

# 创建应用
app = FastAPI(title="教务助手代理", version="1.0")

# 允许所有来源访问（方便测试）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def home():
    """首页"""
    return {
        "service": "教务助手代理服务",
        "status": "运行正常",
        "endpoints": {
            "/test": "测试连接",
            "/news": "获取教务新闻",
            "/schedule?username=学号&password=密码": "获取课表（需登录）"
        }
    }

@app.get("/test")
async def test_connection():
    """测试是否能访问教务网站"""
    try:
        url = "http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": "可以访问教务网站",
                "status_code": response.status_code
            }
        else:
            return {
                "success": False,
                "message": f"网站返回状态码：{response.status_code}",
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败：{str(e)}"
        }

@app.get("/news")
async def get_news():
    """获取教务网站首页的新闻通知（公开内容）"""
    try:
        url = "http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试查找新闻列表（需要根据实际网页调整）
            news_items = []
            
            # 方法1：查找所有链接
            for link in soup.find_all('a', href=True)[:10]:  # 取前10个
                text = link.get_text(strip=True)
                if text and len(text) > 5:  # 过滤太短的文本
                    news_items.append({
                        "title": text,
                        "url": link['href'] if link['href'].startswith('http') 
                               else f"http://qzjw.bwgl.cn{link['href']}"
                    })
            
            # 如果没找到，尝试其他选择器
            if not news_items:
                # 查找可能有新闻的div
                for div in soup.find_all('div', class_=True):
                    if 'news' in div.get('class', []) or 'notice' in div.get('class', []):
                        news_items.append({
                            "title": div.get_text(strip=True)[:100],
                            "source": "div元素"
                        })
            
            return {
                "success": True,
                "data": news_items[:5],  # 只返回前5条
                "total_found": len(news_items),
                "hint": "这是公开内容测试，如需课表需要登录功能"
            }
        else:
            return {
                "success": False,
                "error": f"获取网页失败，状态码：{response.status_code}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"解析失败：{str(e)}",
            "tip": "可能需要调整解析规则"
        }

@app.get("/check-structure")
async def check_page_structure():
    """查看网页结构，帮助调整解析规则"""
    try:
        url = "http://qzjw.bwgl.cn/gllgdxbwglxy_jsxsd/"
        response = requests.get(url, timeout=10)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 收集页面结构信息
        structure = {
            "title": soup.title.string if soup.title else "无标题",
            "forms": [],
            "tables": [],
            "common_classes": [],
            "common_ids": []
        }
        
        # 查找表单
        for form in soup.find_all('form'):
            structure["forms"].append({
                "action": form.get('action', '无'),
                "id": form.get('id', '无'),
                "class": form.get('class', [])
            })
        
        # 查找表格
        for table in soup.find_all('table'):
            structure["tables"].append({
                "id": table.get('id', '无'),
                "class": table.get('class', []),
                "rows": len(table.find_all('tr'))
            })
        
        # 统计常见的class
        class_counter = {}
        for tag in soup.find_all(class_=True):
            for cls in tag['class']:
                class_counter[cls] = class_counter.get(cls, 0) + 1
        
        # 取出现次数最多的10个class
        structure["common_classes"] = sorted(
            class_counter.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return {
            "success": True,
            "structure": structure,
            "tip": "根据这些信息调整news接口的解析规则"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("教务代理服务器启动")
    print("访问地址：http://localhost:8000")
    print("测试接口：http://localhost:8000/test")
    print("获取新闻：http://localhost:8000/news")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)