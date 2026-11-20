FROM golang:1.27.4-trixie@sha256:f18c3d73a184fb0582828510722e723b63a93f7188d11dd223d9be6f6880e65d AS build

WORKDIR /src
COPY go.mod ./
COPY cmd ./cmd
COPY internal ./internal

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -trimpath \
    -ldflags="-s -w -buildid=" \
    -o /out/aegis ./cmd/aegis && \
    mkdir -p /out/data && chmod 750 /out/data

FROM scratch

COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /out/aegis /aegis
# A fresh named volume inherits this directory's non-root ownership.
COPY --from=build --chown=65532:65532 /out/data /data

USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/aegis"]
