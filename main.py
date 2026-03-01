import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm
from datetime import date

st.set_page_config(page_title="Dashboard Santé", layout="wide")
st.title("📊 Tableau de bord de suivi de santé")

conn = st.connection("gsheets", type=GSheetsConnection)

def read_sheet(name):
    try:
        return conn.read(worksheet=name, ttl=0)
    except:
        return pd.DataFrame()

# --- Sélecteur de date ---
start_date = st.date_input("Afficher à partir de :", value=date(2023, 1, 1))

def plot_data(df, y_col, label, title):
    if df.empty or y_col not in df.columns:
        st.info(f"Pas de données pour {title}")
        return
    df['DateHeure'] = pd.to_datetime(df['DateHeure'])
    df = df[df['DateHeure'].dt.date >= start_date].sort_values('DateHeure')
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['DateHeure'], y=df[y_col], mode='lines+markers', name=label))
    try:
        lowess = sm.nonparametric.lowess(df[y_col], df['DateHeure'].astype('int64'), frac=0.3)
        fig.add_trace(go.Scatter(x=pd.to_datetime(lowess[:, 0]), y=lowess[:, 1], mode='lines', name="Tendance", line=dict(dash='dash')))
    except: pass
    fig.update_layout(title=title)
    st.plotly_chart(fig, use_container_width=True)

# Affichage des graphiques
col1, col2 = st.columns(2)
with col1:
    plot_data(read_sheet('PressionSynthese'), 'Systolique', 'mmHg', "Pression Systolique")
with col2:
    plot_data(read_sheet('glycemie'), 'Valeur', 'mmol/L', "Glycémie")

plot_data(read_sheet('poids'), 'Poids_kg', 'kg', "Évolution du Poids")