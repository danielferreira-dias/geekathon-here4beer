# Makefile for Clotho Frontend
# Simplifies common development and build tasks for the React application.

# --- Configuration ---
NODE_MODULES := node_modules
DIST_DIR := dist
BUILD_TOOL := npm

# --- Help ---
# The default target. Running 'make' will display this help message.
.PHONY: help
help:
	@echo "🎨 Clotho Frontend Makefile"
	@echo "-------------------------------------------------"
	@echo "Usage: make [target]"
	@echo ""
	@echo "📦 Development:"
	@echo "  install               Install npm dependencies"
	@echo "  dev                   Start development server (http://localhost:5173)"
	@echo "  run                   Build and run Docker container (http://localhost:3000)"
	@echo "  build                 Build for production"
	@echo "  preview               Preview production build locally"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean                 Remove node_modules and dist directories"
	@echo "  fresh                 Clean and reinstall dependencies"
	@echo ""
	@echo "🔍 Quality:"
	@echo "  lint                  Run ESLint to check code quality"
	@echo "  type-check            Run TypeScript type checking"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  docker-build          Build Docker image for production"
	@echo "  docker-run            Run Docker container locally"

# --- Development Targets ---

# Install npm dependencies
.PHONY: install
install:
	@echo "📦 Installing npm dependencies..."
	$(BUILD_TOOL) install

# Start development server
.PHONY: dev
dev: install
	@echo "🚀 Starting development server..."
	@echo "Frontend will be available at: http://localhost:5173"
	$(BUILD_TOOL) run dev

# Build and run Docker container (main run command)
.PHONY: run
run: docker-build
	@echo "🚀 Running Clotho frontend in Docker..."
	@echo "Frontend will be available at: http://localhost:3000"
	docker run -p 3000:3000 --rm clotho-frontend

# Build for production
.PHONY: build
build: install
	@echo "🏗️ Building for production..."
	$(BUILD_TOOL) run build

# Preview production build
.PHONY: preview
preview: build
	@echo "🔍 Starting preview server..."
	$(BUILD_TOOL) run preview

# --- Quality Targets ---

# Run ESLint
.PHONY: lint
lint: install
	@echo "🔍 Running ESLint..."
	$(BUILD_TOOL) run lint

# Run TypeScript type checking
.PHONY: type-check
type-check: install
	@echo "📝 Running TypeScript type check..."
	npx tsc --noEmit

# --- Maintenance Targets ---

# Remove generated directories
.PHONY: clean
clean:
	@echo "🧹 Cleaning up generated files..."
	rm -rf $(NODE_MODULES)
	rm -rf $(DIST_DIR)
	rm -f package-lock.json
	@echo "✅ Cleanup complete."

# Clean and reinstall dependencies
.PHONY: fresh
fresh: clean install
	@echo "✨ Fresh installation complete!"

# --- Docker Targets ---

# Build Docker image
.PHONY: docker-build
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t clotho-frontend .

# Run Docker container
.PHONY: docker-run
docker-run: docker-build
	@echo "🚀 Running Docker container..."
	@echo "Frontend will be available at: http://localhost:3000"
	docker run -p 3000:3000 --rm clotho-frontend

# --- Utility Targets ---

# Show project info
.PHONY: info
info:
	@echo "📊 Project Information:"
	@echo "  Project: Clotho Frontend"
	@echo "  Framework: React + Vite + TypeScript"
	@echo "  Styling: TailwindCSS + shadcn/ui"
	@echo "  Node version: $$(node --version)"
	@echo "  NPM version: $$(npm --version)"

# Set the default target to 'help'
.DEFAULT_GOAL := help
