print("Started Adding the Users.");
const fs = require("fs")
var username = fs.readFile(process.env.MONGO_INITDB_USER_USERNAME_FILE, 't');
var dbname = fs.readFile(process.env.MONGO_DB_NAME, 't');
var userpwd = fs.readFile(process.env.MONGO_INITDB_USER_PASSWORD_FILE, 't');

db = db.getSiblingDB(dbname);
db.createUser({
    user: username,
    pwd: userpwd,
    roles: [{ role: "readWrite", db: dbname }],
});

print("End Adding the User Roles.");