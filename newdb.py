import sqlite3

def create_database():
    """
    Crée une base de données SQLite nommée 'mesures_sante.db'
    avec trois tables pour la pression sanguine, la glycémie et le poids.
    """
    try:
        conn = sqlite3.connect('mesures_sante.db')
        cursor = conn.cursor()

        # Crée la table pour la Pression sanguine
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS PressionSanguine (
                DateHeure TEXT PRIMARY KEY,
                Systolique INTEGER,
                Diastolique INTEGER,
                Pouls INTEGER,
                Note TEXT
            )
        ''')

        # Crée la table pour la Glycémie
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Glycemie (
                DateHeure TEXT PRIMARY KEY,
                Valeur REAL,
                Note1 TEXT,
                Note2 TEXT
            )
        ''')

        # Crée la table pour le Poids
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Poids (
                DateHeure TEXT PRIMARY KEY,
                PoidsLbs REAL,
                PoidsKg REAL,
                Note1 TEXT,
                Note2 TEXT
            )
        ''')

        conn.commit()
        print("La base de données 'mesures_sante.db' et ses tables ont été créées avec succès.")
    except sqlite3.Error as e:
        print(f"Une erreur s'est produite : {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    create_database()