FROM golang:1.26.9-trixie@sha256:f89535b7caea67fa9ff0ba009894bff8f3be915e49cb635477c8ce04e045db5d AS build

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
