# syntax=docker/dockerfile:1
FROM alpine:3.19.1
RUN 'apk update && apk add bash && apk add openssl'
COPY 'ssl_secure_init.sh' '/ssl_secure_init.sh'
RUN chmod +x /ssl_secure_init.sh
ENTRYPOINT '/ssl_secure_init.sh'