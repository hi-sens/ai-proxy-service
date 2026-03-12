#!/bin/bash

# AI Agent Service 启动脚本

echo "=== AI Agent Service 启动脚本 ==="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3.11 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "创建.env文件..."
    cp .env.example .env
    echo "请编辑.env文件配置必要的环境变量"
fi

# 启动Docker服务
echo "启动基础设施服务..."
cd docker
docker-compose up -d
cd ..

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 初始化数据库
echo "初始化数据库..."
python scripts/init_db.py

# 下载Ollama模型（可选）
echo "是否下载Ollama模型？(y/n)"
read -r download_model
if [ "$download_model" = "y" ]; then
    echo "下载Qwen模型..."
    docker exec -it ai-agent-ollama ollama pull qwen2.5:14b
fi

# 启动应用
echo "启动应用..."
uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000
