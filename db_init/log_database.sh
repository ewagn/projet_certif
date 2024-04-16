#!/bin/bash

username=$(cat $MARIADB_LOG_USER_FILE)
log_pwd=$(cat $MARIADB_LOG_PWD_FILE)
root_pwd=$(cat $MARIADB_ROOT_PASSWORD_FILE)

echo "le mot de passe administrateur est ${root_pwd}"

echo "creation de la base de données ${MARIADB_FOR_LOGS}"
mariadb -u root -p$root_pwd -e "CREATE DATABASE IF NOT EXISTS ${MARIADB_FOR_LOGS};"

echo "création de l'utilisateur ${username} avec le mot de passe ${log_pwd}"
mariadb -u root -p$root_pwd  -e "CREATE USER IF NOT EXISTS ${username} IDENTIFIED BY '${log_pwd}' REQUIRE SSL;"

echo "Attribution des permissions"
mariadb -u root -p$root_pwd -e "GRANT ALL ON ${MARIADB_FOR_LOGS}.* TO ${username}@'%' IDENTIFIED BY '${log_pwd}' REQUIRE SSL;"
# mariadb -u root -p$(cat $MARIADB_ROOT_PASSWORD_FILE) -e "FLUSH PRIVILEGES;"


# GRANT ALL ON ${MARIADB_FOR_LOGS}.* TO ${username}@localhost IDENTIFIED BY '${pwd}' REQUIRE SSL;
# GRANT ALL ON ${MARIADB_FOR_LOGS}.* TO ${username}@isearch_app-mariadb-1 IDENTIFIED BY '${pwd}' REQUIRE SSL;
# GRANT ALL ON ${MARIADB_FOR_LOGS}.* TO ${username}@mariadb-1 IDENTIFIED BY '${pwd}' REQUIRE SSL;
# GRANT ALL ON ${MARIADB_FOR_LOGS}.* TO ${username}@10.3.0.3 IDENTIFIED BY '${pwd}' REQUIRE SSL;