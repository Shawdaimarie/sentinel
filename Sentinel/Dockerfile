FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS builder

# Apply the fixed Debian zlib package to both build and runtime stages.
RUN apt-get update && \
    apt-get install --no-install-recommends -y zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 && \
    rm -rf /var/lib/apt/lists/*


ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements-build.txt requirements-runtime.txt ./
RUN python -m pip install --require-hashes --only-binary=:all: -r requirements-build.txt && \
    python -m pip download --require-hashes --only-binary=:all: \
      --dest /wheels -r requirements-runtime.txt

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN PIP_NO_INDEX=1 python -m pip wheel --no-deps --no-build-isolation --wheel-dir /wheels .

FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS runtime

RUN apt-get update && \
    apt-get install --no-install-recommends -y zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system sentinel && \
    useradd --system --gid sentinel --create-home sentinel

COPY --from=builder /wheels /wheels
COPY requirements-runtime.txt /tmp/requirements-runtime.txt
RUN python -m pip install --no-index --find-links=/wheels \
      --require-hashes --only-binary=:all: -r /tmp/requirements-runtime.txt && \
    python -m pip install --no-index --no-deps /wheels/sentinel-*.whl && \
    python -m pip check && \
    rm -rf /wheels /tmp/requirements-runtime.txt

USER sentinel
WORKDIR /workspace
ENTRYPOINT ["sentinel-eval"]
CMD ["--help"]
