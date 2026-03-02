import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Tableau de Bord Santé", layout="wide")
st.title("🏥 Résumé Global (Depuis le 01/10/2024)")

# Connexion unique
conn = st.connection("gsheets", type=GSheetsConnection)

def get_filtered_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            df['DateHeure'] = pd.to_datetime(df['DateHeure'])
            # FILTRE : À partir du 1er Octobre 2024
            mask = df['DateHeure'] >= datetime(2024, 10, 1)
            df = df.loc[mask]
            return df.sort_values('DateHeure')
    except:
        return pd.DataFrame()
    return pd.DataFrame()

# Chargement des données filtrées
df_gly = get_filtered_data("glycemie")
df_pre = get_data("PressionSynthese") # On utilise la même logique de filtre
# Note: Si get_data n'est pas définie, utilisez get_filtered_data pour toutes
df_pre = get_filtered_data("PressionSynthese")
df_poids = get_filtered_data("poids")

# --- SECTION 1 : KPI (Dernières valeurs) ---
st.header("📌 État Actuel")
k1, k2, k3, k4 = st.columns(4)

with k1:
    if not df_gly.empty:
        last = df_gly.iloc[-1]
        st.metric("Dernière Glycémie", f"{last['Valeur']} mmol/L")
    else: st.metric("Glycémie", "N/A")

with k2:
    if not df_pre.empty:
        last = df_pre.iloc[-1]
        st.metric("Dernière Tension", f"{int(last['Systolique'])}/{int(last['Diastolique'])}")
    else: st.metric("Tension", "N/A")

with k3:
    if not df_pre.empty:
        st.metric("Dernier Pouls", f"{int(df_pre.iloc[-1]['Pouls'])} BPM")

with k4:
    if not df_poids.empty:
        st.metric("Dernier Poids", f"{df_poids.iloc[-1]['Poids_kg']:.1g} kg")

st.markdown("---")

# --- SECTION 2 : GRAPHIQUES AVEC COURBES DE TENDANCE ---
st.header("📈 Tendances et Analyses")

# 1. GRAPHIQUE PRESSIONS (SYSTOLIQUE)
st.subheader("Pression Artérielle (Synthèse)")
if not df_pre.empty:
    fig_pre = px.scatter(df_pre, x="DateHeure", y="Systolique", 
                         trendline="ols", trendline_color_override="red",
                         title="Évolution de la Systolique avec tendance")
    # On ajoute la Diastolique sur le même graphique
    fig_pre.add_trace(go.Scatter(x=df_pre['DateHeure'], y=df_pre['Diastolique'], 
                                 mode='markers', name='Diastolique', marker=dict(color='green', opacity=0.4)))
    fig_pre.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_pre, use_container_width=True)

c1, c2 = st.columns(2)

# 2. GLYCÉMIE AVEC TENDANCE
with c1:
    st.subheader("Glycémie")
    if not df_gly.empty:
        fig_g = px.scatter(df_gly, x="DateHeure", y="Valeur", 
                           trendline="ols", trendline_color_override="white",
                           title="Tendance Glycémique")
        fig_g.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(fig_g, use_container_width=True)

# 3. POIDS AVEC TENDANCE
with c2:
    st.subheader("Poids (kg)")
    if not df_poids.empty:
        fig_p = px.scatter(df_poids, x="DateHeure", y="Poids_kg", 
                           trendline="ols", trendline_color_override="#00B4D8",
                           title="Tendance du Poids")
        fig_p.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(fig_p, use_container_width=True)

# --- NOTES ---
st.markdown("---")
st.write("**Note :** Les lignes droites colorées représentent la tendance générale (régression linéaire).")