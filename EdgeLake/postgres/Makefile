# ---- Config (override any of these via `make KEY=value`) ----
IMAGE            ?= postgres:14.0-alpine
NAME             ?= postgres
HOST_PORT        ?= 5432
CONTAINER_PORT   ?= 5432
VOLUME           ?= pgdata
NETWORK          ?= pgnet

# DB env
POSTGRES_USER    ?= demo
POSTGRES_PASSWORD?= passwd
POSTGRES_DB      ?= mnist_fl

# ---- Helpers ----
DOCKER_RUN = docker run -d \
	--name $(NAME) \
	--restart always \
	--tty --interactive \
	-e POSTGRES_USER=$(POSTGRES_USER) \
	-e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
	-e POSTGRES_DB=$(POSTGRES_DB) \
	-p $(HOST_PORT):$(CONTAINER_PORT) \
	-v $(VOLUME):/var/lib/postgresql/data \
	--network $(NETWORK) \
	$(IMAGE)

.PHONY: up down restart logs shell psql status rm clean nuke inspect env

# Create volume/network (idempotent) and start the container
up:
	@docker volume inspect $(VOLUME) >/dev/null 2>&1 || docker volume create $(VOLUME)
	@docker network inspect $(NETWORK) >/dev/null 2>&1 || docker network create $(NETWORK)
	@docker ps -a --filter name=^/$(NAME) --format '{{.Names}}' | grep -qx '$(NAME)' && { echo "Container '$(NAME)' already exists. Use 'make restart' or 'make down' first."; exit 1; } || true
	@$(DOCKER_RUN)
	@echo "Started $(NAME) on host port $(HOST_PORT) with volume $(VOLUME)."

# Stop and remove the container (keeps volume/network)
down:
	@docker stop $(NAME) 2>/dev/null || true
	@docker rm $(NAME) 2>/dev/null || true
	@echo "Stopped and removed container $(NAME)."

# Stop, then bring back up
restart: down up

# Tail logs
logs:
	@docker logs -f $(NAME)

# Shell into the container
shell:
	@docker exec -it $(NAME) sh

# psql inside the container (requires the image’s psql client)
psql:
	@docker exec -it $(NAME) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

# Quick status
status:
	@docker ps -a --filter name=^/$(NAME)

# Remove just the container (alias to down)
rm: down

# Remove container + volume (keeps network)
clean: down
	@docker volume rm $(VOLUME) 2>/dev/null || true
	@echo "Removed volume $(VOLUME)."

# Remove container + volume + network (full cleanup)
nuke: clean
	@docker network rm $(NETWORK) 2>/dev/null || true
	@echo "Removed network $(NETWORK)."

# Inspect everything quickly
inspect:
	@echo "IMAGE=$(IMAGE)"
	@echo "NAME=$(NAME)"
	@echo "HOST_PORT=$(HOST_PORT) -> CONTAINER_PORT=$(CONTAINER_PORT)"
	@echo "VOLUME=$(VOLUME)"
	@echo "NETWORK=$(NETWORK)"
	@echo "POSTGRES_USER=$(POSTGRES_USER)"
	@echo "POSTGRES_DB=$(POSTGRES_DB)"

# Show effective env block as docker would receive it
env:
	@echo "POSTGRES_USER=$(POSTGRES_USER)"
	@echo "POSTGRES_PASSWORD=$(POSTGRES_PASSWORD)"
	@echo "POSTGRES_DB=$(POSTGRES_DB)"
