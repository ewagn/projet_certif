#!/bin/bash

mkdir ssh_keys
cd ssh_keys

openssl genrsa 4096 > "${SQL_CERTIF_PATH}/ca-key.pem"
echo 'Clée générée'

openssl req -new -x509 -nodes -days 365000 -key "${SQL_CERTIF_PATH}/ca-key.pem" -out "${SQL_CERTIF_PATH}/ca-cert.pem" -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MariaDB admin"
echo 'Certificat admin génére'

openssl req -newkey rsa:2048 -days 365000 -nodes -keyout "${SQL_CERTIF_PATH}/server-key.pem" -out "${SQL_CERTIF_PATH}/server-req.pem" -subj "/C=FR/ST=Cote d'Or/L=Dijon/O=GRETA21/OU=/CN=MariaDB server"
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