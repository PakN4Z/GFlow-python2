import mysql.connector
from mysql.connector import Error

class DBManager:
    def __init__(self):
        self.host = "localhost"
        self.user = "gflow_admin"
        self.password = "HY.per.1548"
        self.database = "gflow"

    def connect(self):
        """Establish a connection to the database."""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False

    def disconnect(self):
        """Close the database connection."""
        if self.connection.is_connected():
            self.connection.close()

    def execute_query(self, query, params=None):
        """Execute a given SQL query."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            if query.lower().startswith("select"):
                return cursor.fetchall()  # For SELECT queries
            else:
                self.connection.commit()  # For INSERT, UPDATE, DELETE
                return cursor.rowcount  # Number of rows affected
        except Error as e:
            print(f"Error executing query: {e}")
            return None
        finally:
            cursor.close()

    def insert_data(self, pallet_number, program_name, creation_time, total_runtime):
        """Insert data into the table."""
        query = """INSERT INTO table1 (pallet_number, program_name, creation_time, total_runtime) 
                   VALUES (%s, %s, %s, %s)"""
        params = (pallet_number, program_name, creation_time, total_runtime)
        return self.execute_query(query, params)

    def update_data(self, program_id, pallet_number, program_name, creation_time, total_runtime):
        """Update data in the table."""
        query = """UPDATE table1 SET pallet_number = %s, program_name = %s, 
                   creation_time = %s, total_runtime = %s WHERE program_id = %s"""
        params = (pallet_number, program_name, creation_time, total_runtime, program_id)
        return self.execute_query(query, params)

    def delete_data(self, program_id):
        """Delete data from the table."""
        query = "DELETE FROM table1 WHERE program_id = %s"
        params = (program_id,)
        return self.execute_query(query, params)

    def fetch_data(self):
        """Fetch all data from the table."""
        query = "SELECT * FROM table1"
        return self.execute_query(query)


