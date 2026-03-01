import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm

st.set_page_config(page_title="Suivi de la Glycémie", layout="wide")
st.title("🩸 Suivi de la Glycémie")

# --- Connexion à Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : AJOUT DE DONNÉES ---
st.header("Importer de nouvelles mesures")
uploaded_file = st.file_uploader("Choisissez un fichier CSV (DateHeure, Valeur, Note1, Note2)", type="csv")

if uploaded_file is not None:
    df_new = pd.read_csv(uploaded_file)
    if st.button("Synchroniser avec Google Sheets"):
        with st.spinner("Mise à jour du Cloud..."):
            try:
                try:
                    existing = conn.read(worksheet="glycemie", ttl=0)
                except:
                    existing = pd.DataFrame()

                final = pd.concat([existing, df_new]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="glycemie", data=final)
                st.success("✅ Données synchronisées !")
                st.cache_data.clear() # Force le rafraîchissement du graphique
            except Exception as e:
                st.error(f"Erreur : {e}")

st.markdown("---")

# --- SECTION 2 : AFFICHAGE DU GRAPHIQUE ---
st.header("📈 Historique et Tendance")

try:
    df_plot = conn.read(worksheet="glycemie", ttl=0)
    
    if not df_plot.empty:
        # 1. Nettoyage des virgules décimales dans la colonne 'Valeur'
        if df_plot['Valeur'].dtype == object:  # Si c'est du texte
            df_plot['Valeur'] = df_plot['Valeur'].str.replace(',', '.')
        
        # 2. Conversion forcée en numérique
        df_plot['Valeur'] = pd.to_numeric(df_plot['Valeur'], errors='coerce')
        
        # 3. Conversion robuste de la Date
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'], dayfirst=True, errors='coerce')
        
        # 4. Suppression des lignes corrompues (si la date ou la valeur est vide)
        df_plot = df_plot.dropna(subset=['DateHeure', 'Valeur'])
        df_plot = df_plot.sort_values('DateHeure')

        if len(df_plot) > 1:
            fig = go.Figure()
            # ... (reste du code du graphique identique) ...
            fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Valeur'], mode='lines+markers', name='Glycémie'))
            
            # Tendance LOWESS
            lowess = sm.nonparametric.lowess(df_plot['Valeur'], df_plot['DateHeure'].astype('int64'), frac=0.3)
            fig.add_trace(go.Scatter(x=pd.to_datetime(lowess[:, 0]), y=lowess[:, 1], mode='lines', name='Tendance', line=dict(dash='dash', color='orange')))
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Données insuffisantes pour le graphique (vérifiez le format des dates).")
except Exception as e:
    st.error(f"Impossible de charger le graphique : {e}")