import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm  # Importation pour LOWESS
from datetime import datetime

# --- Configuration ---
st.set_page_config(page_title="Tableau de Bord Santé", layout="wide")
st.title("🏥 Résumé Global")
st.markdown("> *Données filtrées à partir du 01/10/2024*")

# Connexion à Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_filtered_data(sheet_name):
    """Lit et filtre les données par date."""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None and not df.empty:
            df['DateHeure'] = pd.to_datetime(df['DateHeure'], errors='coerce')
            df = df.dropna(subset=['DateHeure'])
            # Filtre temporel demandé
            mask = df['DateHeure'] >= datetime(2024, 10, 1)
            return df.loc[mask].sort_values('DateHeure')
    except Exception as e:
        st.error(f"Erreur sur {sheet_name}: {e}")
    return pd.DataFrame()

def add_lowess_trend(fig, df, y_col, name, color):
    """Calcule et ajoute la courbe de tendance LOWESS (méthode main.py)."""
    if len(df) > 5:  # LOWESS nécessite un minimum de points pour être stable
        try:
            # Conversion des dates en format numérique pour le calcul
            x_numeric = df['DateHeure'].astype('int64')
            lowess = sm.nonparametric.lowess(
                endog=df[y_col],
                exog=x_numeric,
                frac=0.3  # Paramètre de lissage (identique à votre main.py)
            )
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(lowess[:, 0]),
                y=lowess[:, 1],
                mode='lines',
                name=f'Tendance {name}',
                line=dict(color=color, dash='dash', width=3)
            ))
        except Exception as e:
            st.warning(f"Courbe de tendance indisponible pour {name}")

# Chargement des sources
df_gly = get_filtered_data("glycemie")
df_pre = get_filtered_data("PressionSynthese")
df_poids = get_filtered_data("poids")

# --- GRAPHIQUE PRESSION ---
st.header("📈 Pression Artérielle & Pouls")
if not df_pre.empty:
    fig_pre = go.Figure()
    # Points bruts pour contexte
    fig_pre.add_trace(go.Scatter(x=df_pre['DateHeure'], y=df_pre['Systolique'], mode='markers', name='Sys. (mesures)', marker=dict(color='#FF4B4B', opacity=0.3)))
    fig_pre.add_trace(go.Scatter(x=df_pre['DateHeure'], y=df_pre['Diastolique'], mode='markers', name='Dia. (mesures)', marker=dict(color='#00CC96', opacity=0.3)))
    
    # Courbes LOWESS (votre méthode préférée)
    add_lowess_trend(fig_pre, df_pre, 'Systolique', 'Systolique', '#FF4B4B')
    add_lowess_trend(fig_pre, df_pre, 'Diastolique', 'Diastolique', '#00CC96')
    
    fig_pre.update_layout(template="plotly_dark", height=450, xaxis_title="Temps", yaxis_title="mmHg")
    st.plotly_chart(fig_pre, use_container_width=True)
else:
    st.info("Aucune donnée de pression après le 01/10/2024.")

# --- SECTION DEUX COLONNES ---
col1, col2 = st.columns(2)

with col1:
    st.header("🩸 Glycémie")
    if not df_gly.empty:
        fig_g = go.Figure()
        fig_g.add_trace(go.Scatter(x=df_gly['DateHeure'], y=df_gly['Valeur'], mode='markers', name='Glycémie', marker=dict(color='white', opacity=0.4)))
        add_lowess_trend(fig_g, df_gly, 'Valeur', 'Glycémie', 'white')
        fig_g.update_layout(template="plotly_dark", height=350, yaxis_title="mmol/L")
        st.plotly_chart(fig_g, use_container_width=True)

with col2:
    st.header("⚖️ Poids")
    if not df_poids.empty:
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=df_poids['DateHeure'], y=df_poids['Poids_kg'], mode='markers', name='Poids (kg)', marker=dict(color='#00B4D8', opacity=0.4)))
        add_lowess_trend(fig_p, df_poids, 'Poids_kg', 'Poids', '#00B4D8')
        fig_p.update_layout(template="plotly_dark", height=350, yaxis_title="kg")
        st.plotly_chart(fig_p, use_container_width=True)

st.celebrate()