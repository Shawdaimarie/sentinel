FROM golang:1.27.2-trixie@sha256:47667934874913a449b96faa7ef4777fa285d9ec29126ee80ed61c45b7cccf0e AS build

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
