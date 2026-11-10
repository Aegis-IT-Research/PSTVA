#########################################################################
# 1st stage: build FFuF                                                 #
#########################################################################
FROM golang:alpine AS builder

RUN apk add --no-cache git ca-certificates && update-ca-certificates
WORKDIR /src
RUN git clone https://github.com/ffuf/ffuf.git .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags='-s -w' -o ffuf .

#########################################################################
# 2nd stage: minimal runtime image                                      #
#########################################################################
FROM alpine:latest
RUN addgroup -S fuf && adduser -S -G fuf fuf
RUN apk add --no-cache ca-certificates && update-ca-certificates
COPY --from=builder /src/ffuf /usr/local/bin/ffuf

#~~~~~~~~~~~~~~~~WORDLISTS~~~~~~~~~~~~~~~~#
RUN mkdir -p /wordlists
COPY wordlists/  /wordlists/


RUN chown -R fuf:fuf /usr/local/bin/ffuf /wordlists
USER fuf

ENTRYPOINT [ "/usr/local/bin/ffuf"]
CMD [ "--help" ]
