#########################################################################
# 1st stage: build kerbrute                                             #
#########################################################################
FROM golang:1.21-alpine AS builder

RUN apk add --no-cache git ca-certificates && update-ca-certificates
WORKDIR /src
RUN git clone --depth 1 https://github.com/ropnop/kerbrute.git .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags='-s -w' -o kerbrute .

#########################################################################
# 2nd stage: minimal runtime image                                      #
#########################################################################
FROM alpine:3.18

RUN addgroup -S kerb && adduser -S -G kerb kerb
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /src/kerbrute /usr/local/bin/kerbrute

# ─── bundle word-lists from the build-context ──────────────────────────
RUN mkdir -p /wordlists
COPY wordlists/users.txt      /wordlists/users.txt
COPY wordlists/passwords.txt  /wordlists/passwords.txt
# ----------------------------------------------------------------------

RUN chown -R kerb:kerb /usr/local/bin/kerbrute /wordlists
USER kerb

ENTRYPOINT ["/usr/local/bin/kerbrute"]
CMD ["--help"] 