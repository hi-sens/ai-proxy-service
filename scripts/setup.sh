#!/bin/bash
# 快速开始脚本

set -e

echo "🚀 AI Agent Gateway Service - 快速开始"
echo "======================================"

# 检查 Python 版本
echo "📋 检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ 需要 Python 3.11 或更高版本，当前版本: $python_version"
    exit 1
fi
echo "✅ Python 版本: $python_version"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt
pip install -e ".[dev]"

# 安装 pre-commit hooks
echo "🪝 安装 pre-commit hooks..."
pre-commit install

# 检查 Docker
echo "🐳 检查 Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 启动 Docker 服务
echo "🚢 启动 Docker 服务..."
cd docker
docker-compose up -d
cd ..

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 初始化数据库
echo "🗄️  初始化数据库..."
python scripts/init_db.py

# 下载模型（可选）
echo ""
echo "📥 是否下载本地模型？(y/n)"
read -r download_model

if [ "$download_model" = "y" ]; then
    echo "下载 Qwen 模型..."
    docker exec -it ai-proxy-ollama ollama pull qwen2.5:14b
fi

echo ""
echo "✅ 设置完成！"
echo ""
echo "🎯 下一步："
echo "  1. 复制环境变量: cp .env.example .env"
echo "  2. 编辑 .env 文件，配置必要的 API 密钥"
echo "  3. 启动应用: uvicorn src.presentation.main:app --reload"
echo "  4. 访问 API 文档: http://localhost:8000/docs"
echo ""
echo "📚 更多命令："
echo "  make help           - 查看所有可用命令"
echo "  make format         - 格式化代码"
echo "  make check          - 运行所有检查"
echo "  make test           - 运行测试"
