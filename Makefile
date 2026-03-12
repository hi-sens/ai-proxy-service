.PHONY: help install dev-install format lint type-check test clean docker-up docker-down init-db

help:
	@echo "可用命令："
	@echo "  make install        - 安装生产依赖"
	@echo "  make dev-install    - 安装开发依赖"
	@echo "  make format         - 格式化代码（autoflake + isort + black）"
	@echo "  make lint           - 代码检查（ruff）"
	@echo "  make type-check     - 类型检查（mypy）"
	@echo "  make test           - 运行测试"
	@echo "  make check          - 运行所有检查（format + lint + type-check + test）"
	@echo "  make docker-up      - 启动 Docker 服务"
	@echo "  make docker-down    - 停止 Docker 服务"
	@echo "  make init-db        - 初始化数据库"
	@echo "  make pre-commit     - 安装 pre-commit hooks"
	@echo "  make clean          - 清理缓存文件"

install:
	pip install -r requirements.txt

dev-install:
	pip install -e ".[dev]"
	pre-commit install

format:
	@echo "移除未使用的导入..."
	autoflake --in-place --remove-all-unused-imports --remove-unused-variables --remove-duplicate-keys --ignore-init-module-imports -r src/ tests/
	@echo "排序导入..."
	isort src/ tests/
	@echo "格式化代码..."
	black src/ tests/

lint:
	@echo "运行 ruff 检查..."
	ruff check src/ tests/

type-check:
	@echo "运行 mypy 类型检查..."
	mypy src/

test:
	@echo "运行测试..."
	pytest

test-cov:
	@echo "运行测试并生成覆盖率报告..."
	pytest --cov=src --cov-report=html --cov-report=term

check: format lint type-check test
	@echo "所有检查通过！"

docker-up:
	cd docker && docker-compose up -d

docker-down:
	cd docker && docker-compose down

init-db:
	python scripts/init_db.py

pre-commit:
	pre-commit install
	@echo "pre-commit hooks 已安装"

pre-commit-run:
	pre-commit run --all-files

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage
	@echo "清理完成"
