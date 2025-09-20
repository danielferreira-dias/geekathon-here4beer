# Simple Makefile to build and run the Dockerized API

# Configurable variables (can be overridden: `make run PORT=9000`)
IMAGE ?= food-copilot-backend
PORT ?= 8000
ENV_FILE ?= .env
# Set to linux/amd64 if you need to force platform on Apple Silicon, e.g., `make build PLATFORM=linux/amd64`
PLATFORM ?=

# Detect container engine (docker preferred, fallback to podman)
# Emit a clear error if neither is installed.
CONTAINER :=
ifeq (,$(shell command -v docker 2>/dev/null))
  ifeq (,$(shell command -v podman 2>/dev/null))
    $(error No container engine found. Please install Docker or Podman. On macOS: `brew install --cask docker` (then start Docker Desktop) or `brew install podman podman-desktop`)
  else
    CONTAINER := podman
  endif
else
  CONTAINER := docker
endif

.PHONY: help build run up stop logs rebuild clean shell curl

help:
	@echo "Usage: make <target> [VAR=val]"
	@echo "Targets:"
	@echo "  build     Build the image ($(IMAGE)) using $(CONTAINER)"
	@echo "  run       Build then run the container in the foreground (maps host $(PORT)->8000)"
	@echo "  up        Run the container detached"
	@echo "  stop      Stop (and remove) the running container"
	@echo "  logs      Tail container logs"
	@echo "  rebuild   Rebuild without cache"
	@echo "  clean     Remove the image"
	@echo "  shell     Start an interactive shell in a new container"
	@echo "  curl      Example curl call to / (health)"

build:
	$(CONTAINER) build $(if $(PLATFORM),--platform $(PLATFORM),) -t $(IMAGE) .

rebuild:
	$(CONTAINER) build $(if $(PLATFORM),--platform $(PLATFORM),) --no-cache -t $(IMAGE) .

run: build
	-@$(CONTAINER) rm -f $(IMAGE) >/dev/null 2>&1 || true
	$(CONTAINER) run --name $(IMAGE) --rm -p $(PORT):8000 --env-file $(ENV_FILE) $(IMAGE)

up:
	-@$(CONTAINER) rm -f $(IMAGE) >/dev/null 2>&1 || true
	$(CONTAINER) run -d --name $(IMAGE) -p $(PORT):8000 --env-file $(ENV_FILE) $(IMAGE)

stop:
	-@$(CONTAINER) stop $(IMAGE) >/dev/null 2>&1 || true
	-@$(CONTAINER) rm -f $(IMAGE) >/dev/null 2>&1 || true

logs:
	$(CONTAINER) logs -f $(IMAGE)

clean:
	-@$(CONTAINER) rmi -f $(IMAGE) >/dev/null 2>&1 || true

shell:
	$(CONTAINER) run -it --rm --env-file $(ENV_FILE) $(IMAGE) sh

curl:
	curl -s http://localhost:$(PORT)/ | jq . || curl -s http://localhost:$(PORT)/