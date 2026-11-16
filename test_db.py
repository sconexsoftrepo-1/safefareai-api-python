from app.database.connection import test_database_connection

try:
    result = test_database_connection()
    print("Database connected successfully!")
    print("Database:", result.database_name)
    print("Server:", result.server_name)

except Exception as error:
    print("Database connection failed!")
    print(error)