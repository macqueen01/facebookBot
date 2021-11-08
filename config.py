from sqlalchemy import create_engine, text

db = {
    'user' : 'root',
    'password' : 'aidan1004',
    'host' : 'localhost',
    'port' : 3306,
    'database' : 'fbBot'
}

DB_URL= "mysql://b1ef036df40a61:f2c8e6b6@us-cdbr-east-04.cleardb.com/heroku_e0cfc0510170cee"
#DB_URL= f"mysql+mysqlconnector://{db['user']}:{db['password']}@{db['host']}:3306/{db['database']}?charset=utf8"
