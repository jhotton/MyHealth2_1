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
    # Lecture des données (on utilise ttl=0 pour voir les ajouts immédiatement)
    df_plot = conn.read(worksheet="glycemie", ttl=0)
    
    if not df_plot.empty:
        # Nettoyage et conversion
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot = df_plot.sort_values('DateHeure')
        df_plot['Valeur'] = pd.to_numeric(df_plot['Valeur'], errors='coerce')
        df_plot = df_plot.dropna(subset=['Valeur'])

        if len(df_plot) > 1:
            fig = go.Figure()
            
            # Points de mesure
            fig.add_trace(go.Scatter(
                x=df_plot['DateHeure'], 
                y=df_plot['Valeur'], 
                mode='lines+markers', 
                name='Glycémie (mmol/L)',
                line=dict(color='#FF4B4B')
            ))

            # Ligne de tendance LOWESS
            try:
                lowess = sm.nonparametric.lowess(
                    df_plot['Valeur'], 
                    df_plot['DateHeure'].astype('int64'), 
                    frac=0.3
                )
                fig.add_trace(go.Scatter(
                    x=pd.to_datetime(lowess[:, 0]), 
                    y=lowess[:, 1], 
                    mode='lines', 
                    name='Tendance', 
                    line=dict(dash='dash', color='white')
                ))
            except:
                pass

            fig.update_layout(
                xaxis_title="Date et Heure",
                yaxis_title="mmol/L",
                template="plotly_dark", # Optionnel : pour un look moderne
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Voir le tableau des données"):
                st.dataframe(df_plot)
        else:
            st.info("Ajoutez au moins deux mesures pour afficher le graphique.")
    else:
        st.info("La feuille Google Sheets est vide.")
except Exception as e:
    st.error(f"Impossible de charger le graphique : {e}")