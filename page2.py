import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go

st.title("🩸 Gestion de la Pression Artérielle")
conn = st.connection("gsheets", type=GSheetsConnection)

def save_to_sheet(df, sheet_name):
    try:
        existing = conn.read(worksheet=sheet_name, ttl=0)
        final = pd.concat([existing, df]).drop_duplicates(subset=['DateHeure'], keep='last')
    except:
        final = df
    conn.update(worksheet=sheet_name, data=final)

uploaded_file = st.file_uploader("Importer CSV Pression", type="csv")
if uploaded_file:
    df_new = pd.read_csv(uploaded_file)
    # Transformation (assurez-vous que vos noms de colonnes CSV matchent)
    if st.button("Enregistrer les mesures brutes"):
        save_to_sheet(df_new, 'PressionBrut')
        st.success("Données brutes enregistrées !")

if st.button("Lancer la Synthèse (Moyenne par 30min)"):
    df_brut = conn.read(worksheet='PressionBrut', ttl=0)
    df_brut['DateHeure'] = pd.to_datetime(df_brut['DateHeure'])
    # Logique de synthèse
    df_brut.set_index('DateHeure', inplace=True)
    df_synth = df_brut.resample('30min').mean().dropna().reset_index()
    save_to_sheet(df_synth, 'PressionSynthese')
    st.success("Synthèse terminée et enregistrée !")