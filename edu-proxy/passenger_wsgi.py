"""
PythonAnywhere专用的WSGI入口文件
这是PythonAnywhere实际加载的文件
"""
import sys
import os

# 设置项目路径
project_home = '/home/你的用户名/edu-proxy'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# 设置环境变量（如果需要）
os.environ['PYTHONPATH'] = project_home

print(f"项目目录: {project_home}")
print(f"系统路径: {sys.path}")

try:
    # 导入FastAPI应用
    from main_fastapi import app
    
    # PythonAnywhere需要这个application变量
    application = app
    
    print("✓ FastAPI应用导入成功")
    
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    
    # 提供一个简单的fallback应用
    def application(environ, start_response):
        """简单的WSGI应用作为备选"""
        start_response('200 OK', [('Content-Type', 'application/json')])
        return [b'{"error": "主应用加载失败，但WSGI工作正常"}']