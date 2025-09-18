import streamlit as st
import sqlite3
import pandas as pd

# Fonction pour se connecter à la base de données
def get_db_connection():
    """
    Établit une connexion à la base de données SQLite.
    """
    try:
        conn = sqlite3.connect('mesures_sante.db')
        return conn
    except sqlite3.Error as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        return None

# Fonction pour obtenir la liste de toutes les tables
def get_table_list():
    """
    Récupère une liste de toutes les tables non-système dans la base de données.
    """
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    return []

# Fonction pour vider une table
def clear_table(table_name):
    """
    Vide une table de la base de données.
    """
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name}")
            conn.commit()
            st.success(f"La table '{table_name}' a été vidée avec succès.")
        except sqlite3.Error as e:
            st.error(f"Une erreur est survenue lors du vidage de la table '{table_name}' : {e}")
        finally:
            conn.close()

# Nouvelle fonction pour supprimer une table
def delete_table(table_name):
    """
    Supprime une table de la base de données de manière sécurisée.
    """
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
            st.success(f"La table '{table_name}' a été supprimée avec succès.")
        except sqlite3.Error as e:
            st.error(f"Une erreur est survenue lors de la suppression de la table '{table_name}' : {e}")
        finally:
            conn.close()

# Fonction pour charger les données d'une table
def load_table_data(table_name):
    """
    Charge les données d'une table dans un DataFrame Pandas.
    """
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            return df
        except pd.io.sql.DatabaseError as e:
            st.warning(f"Impossible de charger les données de la table '{table_name}'. Elle est peut-être vide ou inaccessible. Erreur: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

# --- Configuration de la page Streamlit ---
st.set_page_config(page_title="Gestion des Données Santé", layout="wide")
st.title("Gérer vos Données Santé")
st.markdown("Utilisez cette page pour visualiser et gérer vos tables de données.")

# --- Récupération dynamique des tables ---
tables = get_table_list()

if not tables:
    st.info("Aucune table trouvée dans la base de données 'mesures_sante.db'.")
else:
    # Création dynamique des onglets
    tabs = st.tabs(tables)

    for i, table_name in enumerate(tables):
        with tabs[i]:
            st.header(f"Table : `{table_name}`")
            st.write(f"Contenu de la table `{table_name}`.")
            
            # Affichage des données
            df_table = load_table_data(table_name)
            if not df_table.empty:
                st.dataframe(df_table, use_container_width=True)
            else:
                st.info("La table est vide.")

            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                # Bouton pour vider la table
                if st.button(f"Vider la table '{table_name}'", key=f"clear_btn_{table_name}"):
                    clear_table(table_name)
                    st.experimental_rerun()
            
            with col2:
                # Bouton de confirmation de suppression
                if f"confirm_delete_{table_name}" not in st.session_state:
                    st.session_state[f"confirm_delete_{table_name}"] = False

                if not st.session_state[f"confirm_delete_{table_name}"]:
                    if st.button(f"Supprimer la table '{table_name}'", key=f"delete_btn_{table_name}"):
                        st.session_state[f"confirm_delete_{table_name}"] = True
                        st.warning("⚠️ Attention : La suppression est définitive. Êtes-vous sûr ?")
                else:
                    st.error("Êtes-vous sûr de vouloir supprimer cette table ?")
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        if st.button("Confirmer la suppression", key=f"confirm_del_btn_{table_name}"):
                            delete_table(table_name)
                            # Réinitialiser la session state et relancer
                            st.session_state[f"confirm_delete_{table_name}"] = False
                            st.experimental_rerun()
                    with col2_2:
                        if st.button("Annuler", key=f"cancel_del_btn_{table_name}"):
                            st.session_state[f"confirm_delete_{table_name}"] = False
                            st.experimental_rerun()