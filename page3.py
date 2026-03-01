import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.title("🩸 Suivi de la Glycémie")
conn = st.connection("gsheets", type=GSheetsConnection)

uploaded_file = st.file_uploader("Fichier Glycémie CSV", type="csv")
if uploaded_file:
    df_new = pd.read_csv(uploaded_file)
    if st.button("Synchroniser avec Google Sheets"):
    with st.spinner("Mise à jour..."):
        try:
            # On tente de lire l'existant
            try:
                existing = conn.read(worksheet='glycemie', ttl=0)
            except:
                existing = pd.DataFrame()

            # Fusion
            if not existing.empty:
                final = pd.concat([existing, df_new]).drop_duplicates(subset=['DateHeure'], keep='last')
            else:
                final = df_new
            
            # Mise à jour (C'est ici que l'URL est nécessaire dans les secrets)
            conn.update(worksheet='glycemie', data=final)
            st.success("Synchronisation réussie !")
        except Exception as e:
            st.error(f"Erreur lors de la mise à jour : {e}")