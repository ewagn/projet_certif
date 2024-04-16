# syntax=docker/dockerfile:1
FROM alpine:3.19.1
RUN apk update && apk add bash && apk add openssl
COPY 'ssl_secure_init.sh' '/ssl_secure_init.sh'
# COPY 'log_database.sh' '/log_database.sh'
# COPY 'openssl_conf_ca.cnf' '/openssl_conf_ca.cnf'
# COPY 'openssl_conf_server.cnf' '/openssl_conf_server.cnf'
# COPY 'openssl_conf_client.cnf' '/openssl_conf_client.cnf'
RUN chmod +x /ssl_secure_init.sh
ENTRYPOINT /ssl_secure_init.sh