FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

FROM mcr.microsoft.com/devcontainers/python:3.14@sha256:28835c112fd097cb6d2fe1e195b660d66ae051859070a9b871fa2308f35897d3

COPY --from=uv /uv /uvx /usr/local/bin/

# Pre-create the cache mount point so the named volume is owned by vscode.
RUN install -d -o vscode -g vscode /home/vscode/.cache /home/vscode/.cache/uv
