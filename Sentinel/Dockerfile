FROM python:3.15.0-slim-trixie@sha256:f5b92f2a669a4c347044f29367f31983280b648250ca94dea66f98c53bc87e58 AS builder

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

FROM python:3.15.0-slim-trixie@sha256:f5b92f2a669a4c347044f29367f31983280b648250ca94dea66f98c53bc87e58 AS runtime

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
