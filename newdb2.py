import sqlite3

def create_database(db_name="mesures_sante.db"):
    """
    Crée une base de données SQLite.

    Args:
        db_name (str): Le nom du fichier de la base de données.
    """
    try:
        conn = sqlite3.connect(db_name)
        print(f"Base de données '{db_name}' créée avec succès.")
    except sqlite3.Error as e:
        print(f"Une erreur est survenue lors de la création de la base de données : {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    create_database()