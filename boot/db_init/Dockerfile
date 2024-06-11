# syntax=docker/dockerfile:1
ARG VM_IMG
FROM $VM_IMG

ARG VM_ENTRYPNT

RUN apk update && apk add bash && apk add openssl

COPY $VM_ENTRYPNT '/ssl_secure_init.sh'

# COPY 'log_database.sh' '/log_database.sh'
# COPY 'openssl_conf_ca.cnf' '/openssl_conf_ca.cnf'
# COPY 'openssl_conf_server.cnf' '/openssl_conf_server.cnf'
# COPY 'openssl_conf_client.cnf' '/openssl_conf_client.cnf'

RUN chmod +x /ssl_secure_init.sh
ENTRYPOINT /ssl_secure_init.sh