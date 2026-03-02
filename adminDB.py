import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import os
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Administration & Migration", layout="wide")
st.title("⚙️ Administration du Système")

conn_gsheets = st.connection("gsheets", type=GSheetsConnection)

st.header("📦 Migration des anciennes données (SQLite)")
st.info("Utilisez cette section pour importer votre ancien fichier 'mesures_sante.db'.")

uploaded_db = st.file_uploader("Sélectionnez le fichier mesures_sante.db", type="db")

if uploaded_db is not None:
    # Création d'un fichier temporaire pour lire la base SQLite
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        tmp_file.write(uploaded_db.getvalue())
        tmp_path = tmp_file.name

    try:
        # Connexion à la base SQLite téléchargée
        db_conn = sqlite3.connect(tmp_path)
        
        # Liste des tables à migrer
        tables_to_migrate = {
            "glycemie": "glycemie",
            "PressionSynthese": "PressionSynthese",
            "poids": "poids",
            "PressionBrut": "PressionBrut"
        }

        st.write("### État de la migration")
        
        for table_sqlite, sheet_name in tables_to_migrate.items():
            try:
                # 1. Lecture des données SQLite
                df_old = pd.read_sql_query(f"SELECT * FROM {table_sqlite}", db_conn)
                
                if not df_old.empty:
                    st.write(f"🔄 Traitement de la table **{table_sqlite}** ({len(df_old)} lignes)...")
                    
                    # 2. Lecture des données Google Sheets actuelles pour fusionner
                    try:
                        df_current = conn_gsheets.read(worksheet=sheet_name, ttl=0)
                    except:
                        df_current = pd.DataFrame()

                    # 3. Fusion et suppression des doublons sur DateHeure
                    df_final = pd.concat([df_current, df_old]).drop_duplicates(subset=['DateHeure'], keep='last')
                    
                    # 4. Mise à jour de Google Sheets
                    conn_gsheets.update(worksheet=sheet_name, data=df_final)
                    st.success(f"✅ Table {table_sqlite} migrée avec succès !")
                else:
                    st.warning(f"⚠️ La table {table_sqlite} est vide dans le fichier source.")
            
            except Exception as e:
                st.error(f"❌ Erreur sur la table {table_sqlite} : {e}")

        db_conn.close()
        st.balloons()

    finally:
        # Nettoyage du fichier temporaire
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

st.markdown("---")
if st.button("🧹 Vider le cache de l'application"):
    st.cache_data.clear()
    st.success("Cache vidé !")