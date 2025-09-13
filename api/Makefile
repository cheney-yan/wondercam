# Makefile for Vertex AI to Gemini API Proxy

# Configuration
DOCKER_IMAGE = nightlybible/vertex-to-gemini
DOCKER_TAG ?= latest
DOCKER_PLATFORM = linux/amd64,linux/arm64

# Default target
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  setup       - Install dependencies and setup environment"
	@echo "  run         - Run the service locally"
	@echo "  dev         - Run the service in development mode"
	@echo "  test        - Test the service"
	@echo "  build       - Build Docker image"
	@echo "  push        - Push Docker image to registry"
	@echo "  release     - Build and push Docker image"
	@echo "  clean       - Clean up Docker images"

# Setup
.PHONY: setup
setup:
	@echo "Setting up development environment..."
	@pip install -r requirements.txt
	@cp .env.example .env
	@echo "✅ Setup complete! Please edit .env with your configuration."

# Run locally
.PHONY: run
run:
	@echo "🚀 Starting Vertex-to-Gemini API service..."
	@python run.py

# Development mode
.PHONY: dev
dev:
	@echo "🔧 Starting service in development mode..."
	@DEBUG=True uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Test
.PHONY: test
test:
	@echo "🧪 Testing service..."
	@curl -s http://localhost:8000/health || echo "❌ Service not running. Start with 'make run' first."
	@echo "✅ Basic health check complete"

# Docker build
.PHONY: build
build:
	@echo "🐳 Building Docker image: $(DOCKER_IMAGE):$(DOCKER_TAG)"
	@docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "✅ Docker image built successfully"

# Docker push
.PHONY: push
push:
	@echo "📤 Pushing Docker image: $(DOCKER_IMAGE):$(DOCKER_TAG)"
	@docker push $(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "✅ Docker image pushed successfully"

# Build multi-platform and push
.PHONY: release
release:
	@echo "🚀 Building and pushing multi-platform image: $(DOCKER_IMAGE):$(DOCKER_TAG)"
	@docker buildx build \
		--platform $(DOCKER_PLATFORM) \
		--tag $(DOCKER_IMAGE):$(DOCKER_TAG) \
		--push .
	@echo "✅ Multi-platform release complete"

# Clean up
.PHONY: clean
clean:
	@echo "🧹 Cleaning up Docker images..."
	@docker rmi $(DOCKER_IMAGE):$(DOCKER_TAG) 2>/dev/null || true
	@docker system prune -f
	@echo "✅ Cleanup complete"

# Docker compose
.PHONY: up
up:
	@echo "🐳 Starting services with Docker Compose..."
	@docker-compose up -d
	@echo "✅ Services started"

.PHONY: down
down:
	@echo "🛑 Stopping services..."
	@docker-compose down
	@echo "✅ Services stopped"

.PHONY: logs
logs:
	@docker-compose logs -f vertex-gemini-translator