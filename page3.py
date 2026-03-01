import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.title("🩸 Suivi de la Glycémie")
conn = st.connection("gsheets", type=GSheetsConnection)

uploaded_file = st.file_uploader("Fichier Glycémie CSV", type="csv")
if uploaded_file:
    df_new = pd.read_csv(uploaded_file)
    if st.button("Synchroniser avec Google Sheets"):
        try:
            existing = conn.read(worksheet='glycemie', ttl=0)
            final = pd.concat([existing, df_new]).drop_duplicates(subset=['DateHeure'], keep='last')
        except:
            final = df_new
        conn.update(worksheet='glycemie', data=final)
        st.success("Synchronisation réussie !")