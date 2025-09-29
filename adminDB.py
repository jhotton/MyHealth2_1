import streamlit as st
import sqlite3
import pandas as pd
import datetime
import io

# --- Fonctions de la base de données ---

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

# --- Fonctions d'Exportation ---

@st.cache_data
def convert_df_to_csv(df):
    """
    Convertit un DataFrame en fichier CSV encodé en UTF-8.
    """
    return df.to_csv(index=False).encode('utf-8')

def convert_df_to_excel(df):
    """
    Convertit un DataFrame en fichier Excel.
    Nécessite 'openpyxl'.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Données')
    processed_data = output.getvalue()
    return processed_data

# --- Configuration de la page Streamlit ---
st.set_page_config(page_title="Gestion des Données Santé", layout="wide")
st.title("Gérer vos Données Santé")
st.markdown("Utilisez cette page pour visualiser, gérer et exporter vos tables de données.")

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

                # --- NOUVELLE SECTION : EXPORTATION DES DONNÉES ---
                st.markdown("---")
                st.subheader("Exporter les données")

                # S'assure que le DataFrame a des colonnes pour éviter les erreurs
                if not df_table.columns.empty:
                    col_export1, col_export2 = st.columns(2)

                    with col_export1:
                        # Sélection de la colonne de date
                        date_column = st.selectbox(
                            "Sélectionnez la colonne de date",
                            df_table.columns,
                            key=f"date_col_{table_name}"
                        )

                    with col_export2:
                        # Sélection de la date de début
                        start_date = st.date_input(
                            "Exporter les données à partir du",
                            datetime.date.today() - datetime.timedelta(days=30),
                            key=f"date_input_{table_name}"
                        )
                    
                    try:
                        # Conversion de la colonne de date et de la date de début pour la comparaison
                        df_table[date_column] = pd.to_datetime(df_table[date_column], errors='coerce')
                        start_datetime = pd.to_datetime(start_date)

                        # Filtrage du DataFrame
                        filtered_df = df_table[df_table[date_column] >= start_datetime].copy()
                        
                        st.write(f"Aperçu des {len(filtered_df)} lignes à exporter :")
                        st.dataframe(filtered_df, use_container_width=True)

                        if not filtered_df.empty:
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                # Bouton de téléchargement CSV
                                csv_data = convert_df_to_csv(filtered_df)
                                st.download_button(
                                    label="📥 Télécharger en CSV",
                                    data=csv_data,
                                    file_name=f"{table_name}_{start_date}.csv",
                                    mime='text/csv',
                                    key=f"csv_btn_{table_name}"
                                )
                            with col_btn2:
                                # Bouton de téléchargement Excel
                                excel_data = convert_df_to_excel(filtered_df)
                                st.download_button(
                                    label="📥 Télécharger en Excel",
                                    data=excel_data,
                                    file_name=f"{table_name}_{start_date}.xlsx",
                                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    key=f"excel_btn_{table_name}"
                                )
                        else:
                            st.warning("Aucune donnée à exporter pour la période sélectionnée.")

                    except Exception as e:
                        st.error(f"Erreur lors du filtrage par date : {e}. Assurez-vous que la colonne sélectionnée contient des dates valides.")
                
            else:
                st.info("La table est vide.")

            # --- Section de gestion de la table ---
            st.markdown("---")
            st.subheader("Gérer la table")
            col1, col2 = st.columns(2)
            
            with col1:
                # Bouton pour vider la table
                if st.button(f"Vider la table '{table_name}'", key=f"clear_btn_{table_name}"):
                    clear_table(table_name)
                    st.experimental_rerun()
            
            with col2:
                # Logique de confirmation pour la suppression
                if f"confirm_delete_{table_name}" not in st.session_state:
                    st.session_state[f"confirm_delete_{table_name}"] = False

                if not st.session_state[f"confirm_delete_{table_name}"]:
                    if st.button(f"Supprimer la table '{table_name}'", type="primary", key=f"delete_btn_{table_name}"):
                        st.session_state[f"confirm_delete_{table_name}"] = True
                        st.experimental_rerun()
                else:
                    st.warning(f"⚠️ Êtes-vous sûr de vouloir supprimer définitivement la table '{table_name}' ?")
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        if st.button("Oui, supprimer", type="primary", key=f"confirm_del_btn_{table_name}"):
                            delete_table(table_name)
                            st.session_state[f"confirm_delete_{table_name}"] = False
                            st.experimental_rerun()
                    with col2_2:
                        if st.button("Annuler", key=f"cancel_del_btn_{table_name}"):
                            st.session_state[f"confirm_delete_{table_name}"] = False
                            st.experimental_rerun()
