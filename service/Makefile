.PHONY: install dev run format lint test test-provider-integration clean help validate-data sandbox-image docker-build docker-run

PYTHON_VERSION := 3.12
WFB_DATA_DIR ?= $(abspath ../dataset)
SANDBOX_IMAGE ?= waterfallbench-sandbox:local

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv_check:
	@if [ ! -f .venv/bin/activate ]; then \
		echo "Virtualenv not found! Run \`make install\` first."; \
		exit 1; \
	fi

install: ## Install dependencies
	uv venv --python $(PYTHON_VERSION)
	uv sync --dev

dev: venv_check  ## Start the development server
	uv run fastapi dev main.py --port 0

lint: ## CHeck style with ruff
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff check --fix .

typecheck: ## Type check code with basedpyright
	uv run basedpyright .

test: ## Run tests
	uv run pytest --ignore=tests/integration

test-provider-integration:
	uv run pytest tests/integration

docker-build: ## Build Docker image
	docker build -t benchmark-service:latest .

docker-run: ## Run the service container with the private data root mounted read-only
	docker run -p 8001:8001 -v $(WFB_DATA_DIR):/data:ro -e WFB_DATA_DIR=/data \
		-e WFB_SANDBOX_IMAGE -e WFB_AGENT_TIMEOUT_SECONDS -e WFB_SETUP_EGRESS -e WFB_RUN_EGRESS \
		-e WFB_EVALUATION_EGRESS -e AUTH_REQUIRED -e WFB_SERVICE_TOKEN benchmark-service:latest

validate-data: venv_check ## Check WFB_DATA_DIR against the data contract
	WFB_DATA_DIR=$(WFB_DATA_DIR) uv run python -m waterfallbench_benchmark_service.validate

sandbox-image: ## Build the agent sandbox image (linux/amd64); push it yourself, then set WFB_SANDBOX_IMAGE
	docker build --platform linux/amd64 -t $(SANDBOX_IMAGE) sandbox-image
