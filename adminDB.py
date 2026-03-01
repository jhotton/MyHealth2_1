import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.title("⚙️ Administration des données")
conn = st.connection("gsheets", type=GSheetsConnection)

tab_to_clear = st.selectbox("Choisir l'onglet à vider :", ['PressionBrut', 'PressionSynthese', 'glycemie', 'poids'])

if st.button(f"Vider l'onglet {tab_to_clear}", type="primary"):
    # On crée un DataFrame vide avec les bonnes colonnes pour réinitialiser
    empty_df = pd.DataFrame(columns=['DateHeure']) 
    conn.update(worksheet=tab_to_clear, data=empty_df)
    st.warning(f"L'onglet {tab_to_clear} a été réinitialisé.")