#!/bin/bash
# start.sh

# 等待端口就绪
sleep 2

# 启动 FastAPI 应用
uvicorn main:app --host=0.0.0.0 --port=${PORT:-8000} --workers=${WORKERS:-4}