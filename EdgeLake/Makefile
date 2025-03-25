# Makefile



EDGELAKE_TYPE := generic
ifneq ($(filter-out $@,$(MAKECMDGOALS)), )
	EDGELAKE_TYPE = $(filter-out $@,$(MAKECMDGOALS))
endif

export ARCH := $(shell uname -m)
export TAG := latest
ifeq ($(ARCH),aarch64)
    export TAG := latest-arm64
else ifeq ($(ARCH),arm64)
    export TAG := latest-arm64
endif

export DOCKER_COMPOSE_CMD := $(shell if command -v podman-compose >/dev/null 2>&1; then echo "podman-compose"; \
	elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; \
	else echo "docker compose"; fi)

all: help
build:
	docker pull anylogco/edgelake:$(TAG)

up:
	@echo "Deploy EdgeLake with config file: $(NODE_NAME).env"
	EDGELAKE_TYPE=$(EDGELAKE_TYPE) envsubst < docker_makefile/docker-compose-template.yaml > docker_makefile/docker-compose.yaml
	@${DOCKER_COMPOSE_CMD} -f docker_makefile/docker-compose.yaml up -d
	@rm -rf docker_makefile/docker-compose.yaml
down:
	EDGELAKE_TYPE=$(EDGELAKE_TYPE) envsubst < docker_makefile/docker-compose-template.yaml > docker_makefile/docker-compose.yaml
	@${DOCKER_COMPOSE_CMD} -f docker_makefile/docker-compose.yaml down
	@rm -rf docker_makefile/docker-compose.yaml
clean-vols:
	EDGELAKE_TYPE=$(EDGELAKE_TYPE) envsubst < docker_makefile/docker-compose-template.yaml > docker_makefile/docker-compose.yaml
	@${DOCKER_COMPOSE_CMD} -f docker-makefiles/docker-compose.yaml down --volumes
	@rm -rf docker-makefiles/docker-compose.yaml
clean:
	EDGELAKE_TYPE=$(EDGELAKE_TYPE) envsubst < docker_makefile/docker-compose-template.yaml > docker_makefile/docker-compose.yaml
	@${DOCKER_COMPOSE_CMD} -f docker_makefile/docker-compose.yaml down -v --rmi all
	@rm -rf docker_makefile/docker-compose.yaml
attach:
	docker attach --detach-keys=ctrl-d edgelake-$(EDGELAKE_TYPE)
node-status:
	@if [ "$(EDGELAKE_TYPE)" = "master" ]; then \
		curl -X GET 127.0.0.1:32049 -H "command: get status" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(EDGELAKE_TYPE)" = "operator" ]; then \
		curl -X GET 127.0.0.1:32149 -H "command: get status" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(EDGELAKE_TYPE)" = "query" ]; then \
		curl -X GET 127.0.0.1:32349 -H "command: get status" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(NODE_TYPE)" == "generic" ]; then \
		curl -X GET 127.0.0.1:32549 -H "command: get status" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	fi
test-node:
	@if [ "$(EDGELAKE_TYPE)" = "master" ]; then \
		curl -X GET 127.0.0.1:32049 -H "command: test node" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(EDGELAKE_TYPE)" = "operator" ]; then \
		curl -X GET 127.0.0.1:32149 -H "command: test node" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(EDGELAKE_TYPE)" = "query" ]; then \
		curl -X GET 127.0.0.1:32349 -H "command: test node" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(NODE_TYPE)" == "generic" ]; then \
		curl -X GET 127.0.0.1:32549 -H "command: test node" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	fi
test-network:
	@if [ "$(EDGELAKE_TYPE)" = "master" ]; then \
		curl -X GET 127.0.0.1:32049 -H "command: test network" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(EDGELAKE_TYPE)" = "operator" ]; then \
		curl -X GET 127.0.0.1:32149 -H "command: test network" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(EDGELAKE_TYPE)" = "query" ]; then \
		curl -X GET 127.0.0.1:32349 -H "command: test network" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	elif [ "$(NODE_TYPE)" == "generic" ]; then \
		curl -X GET 127.0.0.1:32549 -H "command: test network" -H "User-Agent: AnyLog/1.23" -w "\n"; \
	fi
exec:
	docker exec -it edgelake-$(EDGELAKE_TYPE) bash
logs:
	docker logs edgelake-$(EDGELAKE_TYPE)
help:
	@echo "Usage: make [target] [edgelake-type]"
	@echo "Targets:"
	@echo "  build       Pull the docker image"
	@echo "  up          Start the containers"
	@echo "  attach      Attach to EdgeLake instance"
	@echo "  test        Using cURL validate node is running"
	@echo "  exec        Attach to shell interface for container"
	@echo "  down        Stop and remove the containers"
	@echo "  logs        View logs of the containers"
	@echo "  clean-vols  Stop and remove the containers and remove image and volumes"
	@echo "  clean       Stop and remove the containers and remove volumes "
	@echo "  help        Show this help message"
	@echo "  supported EdgeLake types: generic, master, operator, and query"
	@echo "Sample calls: make up EDGELAKE_TYPE=master | make attach EDGELAKE_TYPE=master | make clean EDGELAKE_TYPE=master"
