
# Conexión a la base de datos SQL Server usando pyodbc
import pyodbc

class Database:
    def __init__(self):
        self.server = 'localhost'
        self.database = 'SistemaGestionInventarios'
        self.driver = '{ODBC Driver 17 for SQL Server}'
    
    def get_connection(self):
        """Establece conexión con la base de datos"""
        try:
            conn_str = f"""
                DRIVER={self.driver};
                SERVER={self.server};
                DATABASE={self.database};
                Trusted_Connection=yes;
            """
            conn = pyodbc.connect(conn_str)
            print("✅ Conexión a BD exitosa")
            return conn
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return None

# Instancia global de la base de datos
db = Database()

# Función para compatibilidad con los imports existentes
def get_database_connection():
    """Función de compatibilidad para mantener los imports existentes"""
    return db.get_connection()