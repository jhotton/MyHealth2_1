import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Mon Suivi Santé Cloud", layout="wide")

st.title("⚖️ Suivi de Poids (Version Cloud)")

# 1. Connexion à Google Sheets
# Les identifiants (JSON) devront être mis dans les "Secrets" sur Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Chargement des données existantes
try:
    # On lit l'onglet nommé "poids"
    df_existant = conn.read(worksheet="poids", ttl=0) # ttl=0 pour forcer la lecture fraîche
except Exception:
    # Si la feuille est vide ou n'existe pas encore
    df_existant = pd.DataFrame(columns=["date_heure", "valeur"])

# 3. Importation de nouveau CSV
st.header("1. Importer des nouvelles données")
uploaded_file = st.file_uploader("Choisir un fichier CSV pour le poids", type="csv")

if uploaded_file is not None:
    df_new = pd.read_csv(uploaded_file)
    
    # On s'assure que les colonnes matchent
    # On suppose que votre CSV a 'date' et 'poids'
    if st.button("Fusionner et Sauvegarder dans le Cloud"):
        # Nettoyage rapide
        df_new = df_new.rename(columns={'date': 'date_heure', 'poids': 'valeur'})
        
        # Fusion avec l'existant et suppression des doublons sur 'date_heure'
        df_final = pd.concat([df_existant, df_new]).drop_duplicates(subset=['date_heure'], keep='last')
        
        # Mise à jour du Google Sheet
        conn.update(worksheet="poids", data=df_final)
        st.success("✅ Google Sheet mis à jour avec succès !")
        st.rerun()

# 4. Visualisation
st.header("2. Historique et Graphique")

if not df_existant.empty:
    df_existant['date_heure'] = pd.to_datetime(df_existant['date_heure'])
    df_existant = df_existant.sort_values('date_heure')

    fig = go.Figure(data=go.Scatter(
        x=df_existant['date_heure'], 
        y=df_existant['valeur'], 
        mode='lines+markers'
    ))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_existant)
else:
    st.info("Aucune donnée disponible dans le Google Sheet.")
