FROM python:3.12.15-slim-trixie@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS builder

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

FROM python:3.12.15-slim-trixie@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS runtime

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
