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


st.markdown("---")
st.header("💾 Exportation & Sauvegarde (Backup)")
st.info("Téléchargez vos données actuelles au format CSV pour les conserver localement.")

try:
    # Liste des tables à exporter
    tables_to_export = ["glycemie", "PressionSynthese", "poids", "PressionBrut"]
    
    # Création de colonnes pour organiser les boutons de téléchargement
    ex_col1, ex_col2 = st.columns(2)
    
    for i, table_name in enumerate(tables_to_export):
        # On alterne entre la colonne 1 et 2
        target_col = ex_col1 if i % 2 == 0 else ex_col2
        
        try:
            # Lecture des données depuis GSheets
            df_export = conn_gsheets.read(worksheet=table_name, ttl=0)
            
            if not df_export.empty:
                # Conversion en CSV (formatage standard)
                csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
                
                target_col.download_button(
                    label=f"⬇️ Télécharger {table_name}.csv",
                    data=csv_data,
                    file_name=f"backup_{table_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv',
                    key=f"btn_{table_name}"
                )
            else:
                target_col.warning(f"La table {table_name} est vide.")
        except Exception as e:
            target_col.error(f"Erreur sur {table_name}: {e}")

except Exception as e:
    st.error(f"Erreur lors de la préparation des exports : {e}")