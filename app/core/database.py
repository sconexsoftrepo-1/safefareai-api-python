
import os
import pyodbc
from dotenv import load_dotenv

# Load environment variables from the project's .env file
load_dotenv()


def get_db_connection():
    """
    Create and return a connection to the SafeFare SQL Server database.
    """

    connection_string = os.getenv("SQL_CONNECTION_STRING")

    if not connection_string:
        raise RuntimeError(
            "SQL_CONNECTION_STRING is missing. "
            "Please check your .env file."
        )

    try:
        connection = pyodbc.connect(
            connection_string,
            timeout=15
        )
        return connection

    except pyodbc.Error as exc:
        raise RuntimeError(
            f"Unable to connect to SQL Server: {exc}"
        ) from exc
