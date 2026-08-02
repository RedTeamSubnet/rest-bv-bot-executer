# Device Fingerprinter Proxy API

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/RedTeamSubnet/rest.vm-runner/3.create-release.yml?logo=GitHub)](https://github.com/RedTeamSubnet/rest.vm-runner/actions/workflows/3.create-release.yml)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/RedTeamSubnet/rest.vm-runner?logo=GitHub)](https://github.com/RedTeamSubnet/rest.vm-runner/releases)

This is a short description of the project.

## ✨ Features

- Device Fingerprinter Challenge
- Proxy API server
- RedTeam Subnet

---

## 🐤 Getting Started

### 1. 🚧 Prerequisites

[RECOMMENDED] For **docker** runtime:

- Install [**docker** and **docker compose**](https://docs.docker.com/engine/install)
    - Docker image: [**redteamsubnet61/rest.vm-runner**](https://hub.docker.com/r/redteamsubnet61/rest.vm-runner)

For **standalone** runtime:

- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED] [Miniconda (v3)](https://www.anaconda.com/docs/getting-started/miniconda/install)**
    - _[arm64/aarch64] [Miniforge (v3)](https://github.com/conda-forge/miniforge)_
    - _[Python virutal environment] [venv](https://docs.python.org/3/library/venv.html)_

[OPTIONAL] For **DEVELOPMENT** environment:

- Install [**git**](https://git-scm.com/downloads)
- Setup an [**SSH key**](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh) ([video tutorial](https://www.youtube.com/watch?v=snCP3c7wXw0))

### 2. 📥 Download or clone the repository

**2.1.** Prepare projects directory (if not exists):

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects

# Enter into projects directory:
cd ~/workspaces/projects
```

**2.2.** Follow one of the below options **[A]**, **[B]** or **[C]**:

**OPTION A.** Clone the repository:

```sh
git clone https://github.com/RedTeamSubnet/rest.vm-runner.git && \
    cd rest.vm-runner
```

**OPTION B.** Clone the repository (for **DEVELOPMENT**: git + ssh key):

```sh
git clone git@github.com:RedTeam/rest.vm-runner.git && \
    cd rest.vm-runner
```

**OPTION C.** Download source code:

1. Download archived **zip** or **tar.gz** file from [**releases**](https://github.com/RedTeamSubnet/rest.vm-runner/releases).
2. Extract it into the projects directory.
3. Enter into the project directory.

### 3. 📦 Install dependencies

[TIP] Skip this step, if you're going to use **docker** runtime

```sh
pip install -r ./requirements.txt

# For DEVELOPMENT:
pip install -r ./requirements/requirements.dev.txt
```

### 4. 🌎 Configure environment variables

[NOTE] Please, check **[environment variables](#-environment-variables)** section for more details.

#### **OPTION A.** **[RECOMMENDED]** For **docker** runtime **[5.A]**

```sh
# Copy '.env.example' file to '.env' file:
cp -v ./.env.example ./.env

# Edit environment variables to fit in your environment:
nano ./.env
```

#### **OPTION B.** For **standalone** runtime **[5.B ~ 5.F]**

```sh
# Copy '.env.example' file to '.env' file:
cp -v ./.env.example ./src/.env

# Edit environment variables to fit in your environment:
nano ./src/.env
```

### 5. 🏁 Start the server

[NOTE] Follow the one of below instructions based on your environment **[A, B, C, D, E, F]**:

#### Docker runtime

**OPTION A.** **[RECOMMENDED]** Run with **docker compose**:

```sh
## 1. Configure 'compose.override.yml' file.

# Copy 'compose.override.[ENV].yml' file to 'compose.override.yml' file:
cp -v ./templates/compose/compose.override.[ENV].yml ./compose.override.yml
# For example, DEVELOPMENT environment:
cp -v ./templates/compose/compose.override.dev.yml ./compose.override.yml
# For example, STATGING or PRODUCTION environment:
cp -v ./templates/compose/compose.override.prod.yml ./compose.override.yml

# Edit 'compose.override.yml' file to fit in your environment:
nano ./compose.override.yml


## 2. Check docker compose configuration is valid:
./compose.sh validate
# Or:
docker compose config


## 3. Start docker compose:
./compose.sh start -l
# Or:
docker compose up -d --remove-orphans --force-recreate && \
    docker compose logs -f --tail 100
```

#### Standalone runtime (PM2)

**OPTION B.** Run with **PM2**:

[**IMPORTANT**] Before running, need to install [**PM2**](https://pm2.keymetrics.io/docs/usage/quick-start):

```sh
## 1. Configure PM2 configuration file.

# Copy example PM2 configuration file:
cp -v ./pm2-process.json.example ./pm2-process.json

# Edit PM2 configuration file to fit in your environment:
nano ./pm2-process.json


## 2. Start PM2 process:
pm2 start ./pm2-process.json && \
    pm2 logs --lines 50 dfg
```

#### Standalone runtime (Python)

**OPTION C.** Run server as **python script**:

```sh
cd src
python -u ./main.py
```

**OPTION D.** Run server as **python module**:

```sh
python -u -m src.api

# Or:
cd src
python -u -m api
```

**OPTION E.** Run with **uvicorn** cli:

```sh
uvicorn src.main:app --host=[BIND_HOST] --port=[PORT] --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"
# For example:
uvicorn src.main:app --host="0.0.0.0" --port=8000 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"


# Or:
cd src
uvicorn main:app --host="0.0.0.0" --port=8000 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"

# For DEVELOPMENT:
uvicorn main:app --host="0.0.0.0" --port=8000 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*" --reload --reload-include="*.yml" --reload-include=".env"
```

**OPTION F.** Run with **fastapi** cli:

```sh
fastpi run src/main.py --host=[BIND_HOST] --port=[PORT]
# For example:
fastapi run src/main.py --port=8000

# For DEVELOPMENT:
fastapi dev src/main.py --host="0.0.0.0" --port=8000


# Or:
cd src
fastapi run --port=8000

# For DEVELOPMENT:
fastapi dev --host="0.0.0.0" --port=8000
```

### 6. ✅ Check server is running

Check with CLI (curl):

```sh
# Send a ping request with 'curl' to REST API server and parse JSON response with 'jq':
curl -s http://localhost:8000/api/v1/ping | jq
```

Check with web browser:

- Health check: <http://localhost:8000/api/v1/health>
- Swagger: <http://localhost:8000/docs>
- Redoc: <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

### 7. 🛑 Stop the server

Docker runtime:

```sh
# Stop docker compose:
./compose.sh stop
# Or:
docker compose down --remove-orphans
```

Standalone runtime (Only for **PM2**):

```sh
pm2 stop ./pm2-process.json && \
    pm2 flush dfg && \
    pm2 delete ./pm2-process.json
```

👍

---

## ⚙️ Configuration

### 🌎 Environment Variables

[**`.env.example`**](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/.env.example):

```sh
## --- Environment variable --- ##
ENV=LOCAL
DEBUG=false
# TZ=UTC
# PYTHONDONTWRITEBYTECODE=1


## -- DFP Proxy API configs -- ##
MDM_PROXY_API_PORT=8000
# MDM_PROXY_API_LOGS_DIR="/var/log/rest.vm-runner"
# MDM_PROXY_API_DATA_DIR="/var/lib/rest.vm-runner"

# MDM_PROXY_API_VERSION="1"
# MDM_PROXY_API_PREFIX="/api/v{api_version}"
# MDM_PROXY_API_DOCS_ENABLED=true
# MDM_PROXY_API_DOCS_OPENAPI_URL="{api_prefix}/openapi.json"
# MDM_PROXY_API_DOCS_DOCS_URL="{api_prefix}/docs"
# MDM_PROXY_API_DOCS_REDOC_URL="{api_prefix}/redoc"


## -- DFP Challenge configs -- ##
MDM_CHALLENGE_API_KEY="your_api_key_here"  # !!! CHANGE THIS TO REAL API KEY !!!
MDM_CHALLENGE_BASE_URL="http://localhost:10001"
```

### 🔧 Command arguments

You can customize the command arguments to debug or run the service with different commands.

[**`compose.override.yml`**](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/templates/compose/compose.override.dev.yml):

```yml
    command: ["/bin/bash"]
    command: ["-b", "pwd && ls -al && /bin/bash"]
    command: ["-b", "python -u -m api"]
    command: ["-b", "uvicorn main:app --host=0.0.0.0 --port=${MDM_PROXY_API_PORT:-8000} --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips='*'"]
```

---

## 🧪 Running Tests

To run tests, run the following command:

```sh
# Install python test dependencies:
pip install -r ./requirements/requirements.test.txt

# Run tests:
./scripts/test.sh -l -v -c
# Or:
python -m pytest -sv -o log_cli=true
```

## 🏗️ Build Docker Image

Before building the docker image, make sure you have installed **docker** and **docker compose**.

To build the docker image, run the following command:

```sh
# Build docker image:
./scripts/build.sh
# Or:
docker compose build
```

## 📝 Generate Docs

To build the documentation, run the following command:

```sh
# Install python documentation dependencies:
pip install -r ./requirements/requirements.docs.txt

# Serve documentation locally (for development):
./scripts/docs.sh
# Or:
mkdocs serve

# Or build documentation:
./scripts/docs.sh -b
# Or:
mkdocs build
```

## 📚 Documentation

- [Docs](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs)
- [Home](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/README.md)

### Getting Started

- [Prerequisites](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/getting-started/prerequisites.md)
- [Installation](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/getting-started/installation.md)
- [Quick start](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/getting-started/quick-start.md)
- [Configuration](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/getting-started/configuration.md)
- [Examples](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/getting-started/examples.md)

### API Documentation

<!-- - [API Reference](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/api-docs/api-reference.md) -->

- [openapi.json](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/api-docs/openapi.json)
- [Error Codes](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/api-docs/error-codes.md)

### Development

- [Test](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/test.md)
- [Build](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/build.md)
- [Docs](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/docs.md)
- [Scripts](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/scripts/README.md)
- [CI/CD](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/cicd/README.md)
- [File Structure](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/file-structure.md)
- [Sitemap](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/sitemap.md)
- [Related projects](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/related-projects.md)
- [Roadmap](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/roadmap.md)
- [Contributing](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/dev/contributing.md)

### Research

- [Reports](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/research/reports.md)
- [Benchmarks](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/research/benchmarks.md)
- [References](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/research/references.md)

### [Release Notes](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/release-notes.md)

### [Blog](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/blog/index.md)

### About

- [FAQ](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/about/faq.md)
- [Authors](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/about/authors.md)
- [Contact](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/about/contact.md)
- [License](https://github.com/RedTeamSubnet/rest.vm-runner/blob/main/docs/pages/about/license.md)

---

## 📑 References

- FastAPI - <https://fastapi.tiangolo.com>
- Docker - <https://docs.docker.com>
- Docker Compose - <https://docs.docker.com/compose>
