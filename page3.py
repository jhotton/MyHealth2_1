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

# --- SECTION 2 : AFFICHAGE DU GRAPHIQUE ET DES DONNÉES ---
st.header("📈 Historique et Données")

try:
    # Lecture brute sans cache pour le débogage
    df_plot = conn.read(worksheet="glycemie", ttl=0)
    
    if not df_plot.empty:
        # --- ÉTAPE A : NETTOYAGE RIGOUREUX ---
        
        # 1. Gestion des virgules décimales
        if 'Valeur' in df_plot.columns:
            if df_plot['Valeur'].dtype == object: 
                df_plot['Valeur'] = df_plot['Valeur'].astype(str).str.replace(',', '.')
            df_plot['Valeur'] = pd.to_numeric(df_plot['Valeur'], errors='coerce')
        
        # 2. Gestion des Dates (très important pour l'erreur 'DateHeure')
        if 'DateHeure' in df_plot.columns:
            df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'], dayfirst=True, errors='coerce')
        else:
            st.error("⚠️ La colonne 'DateHeure' est introuvable dans Google Sheets. Vérifiez l'orthographe exacte.")

        # 3. Tri et suppression des lignes vides
        df_plot = df_plot.dropna(subset=['DateHeure', 'Valeur'])
        df_plot = df_plot.sort_values('DateHeure')

        # --- ÉTAPE B : AFFICHAGE DU GRAPHIQUE ---
        if len(df_plot) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_plot['DateHeure'], 
                y=df_plot['Valeur'], 
                mode='lines+markers', 
                name='Glycémie',
                line=dict(color='#FF4B4B')
            ))
            
            # Tendance LOWESS
            try:
                lowess = sm.nonparametric.lowess(df_plot['Valeur'], df_plot['DateHeure'].astype('int64'), frac=0.3)
                fig.add_trace(go.Scatter(x=pd.to_datetime(lowess[:, 0]), y=lowess[:, 1], mode='lines', name='Tendance', line=dict(dash='dash', color='white')))
            except:
                pass
            
            fig.update_layout(xaxis_title="Date", yaxis_title="mmol/L", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Besoin d'au moins 2 mesures valides pour le graphique.")

        # --- ÉTAPE C : AFFICHAGE DU TABLEAU AU BAS ---
        st.markdown("### 📋 Tableau des données enregistrées")
        # On affiche le tableau nettoyé pour voir ce que Python "comprend"
        st.dataframe(df_plot, use_container_width=True)

    else:
        st.info("La feuille 'glycemie' est vide dans Google Sheets.")

except Exception as e:
    st.error(f"Erreur technique : {e}")
    # En cas d'erreur, on essaie quand même d'afficher ce qu'on a lu pour déboguer
    if 'df_plot' in locals():
        st.write("Données brutes lues avant erreur :")
        st.dataframe(df_plot)