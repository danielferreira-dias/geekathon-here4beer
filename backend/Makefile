# -------------------------------
# Food Copilot - Makefile (AWS)
# -------------------------------

# Local image name (for docker run locally)
IMAGE ?= food-copilot-backend
PORT ?= 8000
ENV_FILE ?= .env

# ---------- AWS/ECR ----------
AWS_REGION ?= us-east-1
ECR_REPO ?= here4beer/repo
ACCOUNT_ID := 816308070251
ECR_REGISTRY := $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
ECR_IMAGE := $(ECR_REGISTRY)/$(ECR_REPO):latest

# ---------- Build arch ----------
PLATFORM ?= linux/amd64

# ---------- EC2 (deploy via SSH) ----------
EC2_HOST ?= ec2-3-90-109-68.compute-1.amazonaws.com
EC2_USER ?= ec2-user
EC2_KEY  ?= ~/Downloads/backend.pem
BEDROCK_MODEL_ID ?= arn:aws:bedrock:us-east-1:816308070251:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0

# Detect container engine (docker preferred, fallback to podman)
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

.PHONY: help build rebuild run up stop logs clean shell curl \
        ecr-login ecr-create build-ecr push-ecr print-image \
        release deploy ec2-login ec2-logs

help:
	@echo "Usage: make <target> [VAR=val]"
	@echo ""
	@echo "Local:"
	@echo "  build        Build local image ($(IMAGE))"
	@echo "  run          Build then run locally (maps host $(PORT)->8000)"
	@echo "  up           Run detached locally"
	@echo "  stop         Stop/remove local container"
	@echo "  logs         Tail local container logs"
	@echo "  clean        Remove local image"
	@echo "  shell        Start interactive shell in a new container"
	@echo "  curl         GET / on localhost:$(PORT)"
	@echo ""
	@echo "ECR:"
	@echo "  release      Build for amd64 and push to ECR ($(ECR_IMAGE))"
	@echo "  print-image  Print the full ECR image name"
	@echo ""
	@echo "EC2:"
	@echo "  deploy       Deploy latest image to EC2 ($(EC2_HOST))"
	@echo "  ec2-login    Test SSH connection"
	@echo "  ec2-logs     Tail logs on EC2"

# ---------------- Local build/run ----------------

build:
	$(CONTAINER) build --platform $(PLATFORM) -t $(IMAGE) .

rebuild:
	$(CONTAINER) build --platform $(PLATFORM) --no-cache -t $(IMAGE) .

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
	-@curl -s http://localhost:$(PORT)/health | jq . || curl -s http://localhost:$(PORT)/ || true

# ---------------- ECR ----------------

print-image:
	@echo $(ECR_IMAGE)

ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | \
	$(CONTAINER) login --username AWS --password-stdin $(ECR_REGISTRY)

ecr-create:
	-@aws ecr create-repository --repository-name $(ECR_REPO) --region $(AWS_REGION) >/dev/null 2>&1 || true
	@echo "ECR repo ensured: $(ECR_REPO)"

build-ecr:
	$(CONTAINER) buildx build --platform linux/amd64 -t $(ECR_IMAGE) .

push-ecr: ecr-login
	$(CONTAINER) push $(ECR_IMAGE)

release: ecr-create build-ecr push-ecr
	@echo "✅ Release pushed: $(ECR_IMAGE)"

# ---------------- EC2 ----------------

ec2-login:
	ssh -o StrictHostKeyChecking=no -i $(EC2_KEY) $(EC2_USER)@$(EC2_HOST) "echo Connected to \`hostname\`"

deploy:
	@echo "➡️ Deploying $(ECR_IMAGE) to $(EC2_USER)@$(EC2_HOST)"
	ssh -o StrictHostKeyChecking=no -i $(EC2_KEY) $(EC2_USER)@$(EC2_HOST) '\
	  aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY) && \
	  docker pull $(ECR_IMAGE) && \
	  docker rm -f food-copilot >/dev/null 2>&1 || true && \
	  docker run -d --name food-copilot \
	    -e AWS_REGION=$(AWS_REGION) \
	    -e BEDROCK_MODEL_ID="$(BEDROCK_MODEL_ID)" \
	    --restart=always \
	    -p 80:8000 \
	    $(ECR_IMAGE) && \
	  docker ps \
	'
	@echo "✅ Deployed. Visit: http://$(EC2_HOST)/docs"

ec2-logs:
	ssh -i $(EC2_KEY) $(EC2_USER)@$(EC2_HOST) 'docker logs -f food-copilot'
