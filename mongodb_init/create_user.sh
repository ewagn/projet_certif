#!/bin/bash
# sudo chown -R mongodb:mongodb /home/mongodb

db_user=$(cat ${MONGO_INITDB_USER_USERNAME_FILE})
db_user_pwd=$(cat ${MONGO_INITDB_USER_PASSWORD_FILE})


mongosh <<EOF
use ${MONGO_DB_NAME}
use admin
db.createUser(
  {
    user: "$db_user",
    pwd: "$db_user_pwd",
    roles: [ { role: 'readWrite', db: ${MONGO_DB_NAME} }, { role: 'read', db: 'local' } ]
  }
)
EOF
