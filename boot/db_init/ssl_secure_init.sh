#!/bin/bash

# mkdir ssh_keys
# cd ssh_keys

openssl genrsa 4096 > "${SQL_CERTIF_PATH}/ca-key.pem"
echo 'Clée générée'

openssl req -new -x509 -nodes -days 365000 -key "${SQL_CERTIF_PATH}/ca-key.pem" -out "${SQL_CERTIF_PATH}/ca-cert.pem" -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MariaDB admin"
echo 'Certificat admin généré'

#-days 365000
openssl req -newkey rsa:2048 -nodes -keyout "${SQL_CERTIF_PATH}/server-key.pem" -out "${SQL_CERTIF_PATH}/server-req.pem" -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MariaDB server"
openssl rsa -in "${SQL_CERTIF_PATH}/server-key.pem" -out "${SQL_CERTIF_PATH}/server-key.pem"
openssl x509 -req -in "${SQL_CERTIF_PATH}/server-req.pem" -days 365000 -CA "${SQL_CERTIF_PATH}/ca-cert.pem" -CAkey "${SQL_CERTIF_PATH}/ca-key.pem" -set_serial 01 -out "${SQL_CERTIF_PATH}/server-cert.pem"
echo "Clée et certificat server généres"

openssl req -newkey rsa:2048 -days 365000 -nodes -keyout "${CLIENT_CERTIF_PATH}/client-key.pem" -out "${CLIENT_CERTIF_PATH}/client-req.pem" -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MariaDB user"
openssl rsa -in "${CLIENT_CERTIF_PATH}/client-key.pem" -out "${CLIENT_CERTIF_PATH}/client-key.pem"
openssl x509 -req -in "${CLIENT_CERTIF_PATH}/client-req.pem" -days 365000 -CA "${SQL_CERTIF_PATH}/ca-cert.pem" -CAkey "${SQL_CERTIF_PATH}/ca-key.pem" -set_serial 01 -out "${CLIENT_CERTIF_PATH}/client-cert.pem"
echo "Clée et certificat client généres"

echo "Vérification des certificats"
openssl verify -CAfile "${SQL_CERTIF_PATH}/ca-cert.pem" "${SQL_CERTIF_PATH}/server-cert.pem" "${CLIENT_CERTIF_PATH}/client-cert.pem"

echo "copie des certificats dans le dossier client"
cp "${SQL_CERTIF_PATH}/ca-key.pem" "${CLIENT_CERTIF_PATH}/ca-key.pem"
cp "${SQL_CERTIF_PATH}/ca-cert.pem" "${CLIENT_CERTIF_PATH}/ca-cert.pem"

echo "Attribution des autorisations"
chown -Rv mysql:root ${SQL_CERTIF_PATH}


echo "Création du fichier de configuration de la BDD"
cat > "${MADIADB_CONF_FILES}/my.cnf" <<- EOM
[mariadb]
### MySQL Server ###
## Securing the Database with ssl option and certificates ##
## There is no control over the protocol level used. ##
##  mariadb will use TLSv1.0 or better.  ##
#ssl
ssl-ca=/etc/mysql/ssl/ca-cert.pem
ssl-cert=/etc/mysql/ssl/server-cert.pem
ssl-key=/etc/mysql/ssl/server-key.pem
## Set up TLS version here. For example TLS version 1.2 and 1.3 ##
tls_version = TLSv1.2,TLSv1.3
require_secure_transport=1
EOM

username=$(cat $MARIADB_LOG_USER_FILE)
log_pwd=$(cat $MARIADB_LOG_PWD_FILE)

cat > "/mariadb_init/log_database.sql" <<- EOM
CREATE DATABASE IF NOT EXISTS ${MARIADB_FOR_LOGS};
CREATE USER IF NOT EXISTS ${username} IDENTIFIED BY '${log_pwd}' REQUIRE SSL;
GRANT ALL ON ${MARIADB_FOR_LOGS}.* TO ${username}@'%' IDENTIFIED BY '${log_pwd}' REQUIRE SSL;
EOM

# echo "Copie du fichier d'initialisation de la abse de logs dans répertoire d'initialisation de la base de données."
# cp /log_database.sh /mariadb_init/log_database.sh
# chmod +x /mariadb_init/log_database.sh


# echo "Création des clés et certificats d'authentification pour MongoDB"
# # MongoDB CA
# mkdir -p "${MONGODB_CERTIF_PATH}/CA"
# openssl genrsa -out "${MONGODB_CERTIF_PATH}/CA/mongodb_CA.key" 4096
# openssl req -new -x509 -days 1826 -key "${MONGODB_CERTIF_PATH}/CA/mongodb_CA.key" -out "${MONGODB_CERTIF_PATH}/CA/mongodb_CA.crt" -config /openssl_conf_ca.cnf -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MongoDB CA"

# openssl genrsa -out "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.key" 4096
# openssl req -new -key "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.key" -out "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.csr" -config /openssl_conf_ca.cnf -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MongoDB CA"
# openssl x509 -sha256 -req -days 730 -in "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.csr" -CA "${MONGODB_CERTIF_PATH}/CA/mongodb_CA.crt" -CAkey "${MONGODB_CERTIF_PATH}/CA/mongodb_CA.key" -set_serial 01 -out "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.crt" -extfile /openssl_conf_ca.cnf -extensions v3_ca -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MongoDB CA"

# cat "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.crt" "${MONGODB_CERTIF_PATH}/CA/mongodb_CA.crt" > "${MONGODB_CERTIF_PATH}/CA/CA.pem"

# # MongoDB serveur
# mkdir -p "${MONGODB_CERTIF_PATH}/server"
# openssl genrsa -out "${MONGODB_CERTIF_PATH}/server/mongodb_server.key" 4096
# openssl req -new -key "${MONGODB_CERTIF_PATH}/server/mongodb_server.key" -out "${MONGODB_CERTIF_PATH}/server/mongodb_server.csr" -config /openssl_conf_server.cnf -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MongoDB server"
# openssl x509 -sha256 -req -days 365 -in "${MONGODB_CERTIF_PATH}/server/mongodb_server.csr" -CA "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.crt" -CAkey "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.key" -CAcreateserial -out "${MONGODB_CERTIF_PATH}/server/mongodb_server.crt" -extfile /openssl_conf_server.cnf -extensions v3_req -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MongoDB server"

# cat "${MONGODB_CERTIF_PATH}/server/mongodb_server.crt" "${MONGODB_CERTIF_PATH}/server/mongodb_server.key" > "${MONGODB_CERTIF_PATH}/server/server.pem"

# # MongoDB client
# mkdir -p "${MONGODB_CERTIF_PATH}/client"
# openssl genrsa -out "${MONGODB_CERTIF_PATH}/client/mongodb_client.key" 4096
# openssl req -new -key "${MONGODB_CERTIF_PATH}/client/mongodb_client.key" -out "${MONGODB_CERTIF_PATH}/client/mongodb_client.csr" -config /openssl_conf_client.cnf -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MongoDB client"
# openssl x509 -sha256 -req -days 365 -in "${MONGODB_CERTIF_PATH}/client/mongodb_client.csr" -CA "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.crt" -CAkey "${MONGODB_CERTIF_PATH}/CA/mongodb_ia.key" -CAcreateserial -out "${MONGODB_CERTIF_PATH}/client/mongodb_client.crt" -extfile /openssl_conf_client.cnf -extensions v3_req -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MongoDB client"
# cat "${MONGODB_CERTIF_PATH}/client/mongodb_client.crt" "${MONGODB_CERTIF_PATH}/client/mongodb_client.key" > "${MONGODB_CERTIF_PATH}/client/client.pem"

# # Copy CA key file to server and client folders
# cp "${MONGODB_CERTIF_PATH}/CA/CA.pem" "${MONGODB_CERTIF_PATH}/server/CA.pem"
# cp "${MONGODB_CERTIF_PATH}/CA/CA.pem" "${MONGODB_CERTIF_PATH}/client/CA.pem"

# echo "Création du fichier de configuration MongoDB"
# cat > "${MONGODB_CONF_FILE}/mongod.conf" <<- EOM
# net:
#   bindIp: 0.0.0.0
#   port: 27017
#   tls:
#     mode: requireTLS
#     certificateKeyFile: /home/mongodb/ssl/server.pem
#     CAFile: /home/mongodb/ssl/CA.pem
# storage:
#   dbPath: /data/db
# security:
#   authorization: enabled
# EOM

# echo "Copie du fichier dans le volume d'initialisation mongodb"
# cp /mongodb/create_user.sh /mongodb/init/create_user.sh

# echo "Mise à jour des autorisations pour l'éxécution du script"
# chmod +x /mongodb/init/*.sh