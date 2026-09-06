FROM golang:1.23 AS build

WORKDIR /src
COPY go.mod ./
COPY cmd ./cmd
COPY internal ./internal

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -trimpath \
    -ldflags="-s -w -buildid=" \
    -o /out/aegis ./cmd/aegis

FROM scratch

COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /out/aegis /aegis

USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/aegis"]
