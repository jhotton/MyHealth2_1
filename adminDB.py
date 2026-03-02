import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import os
from streamlit_gsheets import GSheetsConnection
from datetime import datetime  # <--- CETTE LIGNE ÉTAIT MANQUANTE

st.set_page_config(page_title="Admin & Migration", layout="wide")
st.title("⚙️ Centre de Contrôle & Migration")

conn_gsheets = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION MIGRATION ---
st.header("📦 Importation Historique (SQLite)")
uploaded_db = st.file_uploader("Glissez votre fichier .db ici", type="db")

if uploaded_db is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        tmp_file.write(uploaded_db.getvalue())
        tmp_path = tmp_file.name

    try:
        db_conn = sqlite3.connect(tmp_path)
        tables_to_migrate = ["glycemie", "PressionSynthese", "poids", "PressionBrut"]
        
        progress_bar = st.progress(0)
        for i, table in enumerate(tables_to_migrate):
            try:
                df_old = pd.read_sql_query(f"SELECT * FROM {table}", db_conn)
                if not df_old.empty:
                    try:
                        df_current = conn_gsheets.read(worksheet=table, ttl=0)
                    except:
                        df_current = pd.DataFrame()
                    df_final = pd.concat([df_current, df_old]).drop_duplicates(subset=['DateHeure'], keep='last')
                    conn_gsheets.update(worksheet=table, data=df_final)
            except:
                pass
            progress_bar.progress((i + 1) / len(tables_to_migrate))
        
        st.balloons()
        st.success("Migration terminée !")
    finally:
        db_conn.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

st.markdown("---")

# --- SECTION EXPORTATION CORRIGÉE ---
st.header("💾 Exportation & Sauvegarde (Backup)")
st.info("Téléchargez vos données actuelles au format CSV pour les conserver localement.")

try:
    tables_to_export = ["glycemie", "PressionSynthese", "poids", "PressionBrut"]
    ex_col1, ex_col2 = st.columns(2)
    
    for i, table_name in enumerate(tables_to_export):
        target_col = ex_col1 if i % 2 == 0 else ex_col2
        try:
            df_export = conn_gsheets.read(worksheet=table_name, ttl=0)
            if df_export is not None and not df_export.empty:
                # Utilisation de datetime pour le nom du fichier
                datestr = datetime.now().strftime('%Y%m%d')
                csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
                
                target_col.download_button(
                    label=f"⬇️ Télécharger {table_name}.csv",
                    data=csv_data,
                    file_name=f"backup_{table_name}_{datestr}.csv",
                    mime='text/csv',
                    key=f"btn_{table_name}"
                )
            else:
                target_col.warning(f"La table {table_name} est vide.")
        except Exception as e:
            target_col.error(f"Erreur sur {table_name}: {e}")

except Exception as e:
    st.error(f"Erreur lors de la préparation : {e}")