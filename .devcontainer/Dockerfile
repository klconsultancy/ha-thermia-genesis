FROM ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff AS uv

FROM mcr.microsoft.com/devcontainers/python:3.15@sha256:eb39f07323784af4c7558396808ceb01dacbe6dd7c63614f34d0235d0344a0ff

COPY --from=uv /uv /uvx /usr/local/bin/

# Pre-create the cache mount point so the named volume is owned by vscode.
RUN install -d -o vscode -g vscode /home/vscode/.cache /home/vscode/.cache/uv
