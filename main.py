# -*- coding: utf-8 -*-
"""
Created on Thu Aug 28 09:53:36 2025

@author: hotju02
"""

""" import streamlit as st
import plotly.express as px

#st.title("This is the title main page")

# Main page content
st.markdown("# Main page 🎈")
st.sidebar.markdown("# Main page 🎈") """

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import statsmodels.api as sm
from datetime import date

# --- Fonctions de gestion de la base de données ---
def get_db_connection():
    """Établit une connexion à la base de données SQLite."""
    try:
        conn = sqlite3.connect('mesures_sante.db')
        return conn
    except sqlite3.Error as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        return None

def read_data_from_db(table_name):
    """Lit les données d'une table spécifiée."""
    conn = get_db_connection()
    if conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY DateHeure", conn)
        conn.close()
        return df
    return pd.DataFrame()

# --- Configuration de la Page Streamlit ---
#st.set_page_config(page_title="Tableau de bord de santé", layout="wide")
st.title("📊 Tableau de bord de suivi de santé")
st.markdown("---")

# --- Sélecteur de date ---
st.header("Sélectionner la période d'affichage")
start_date = st.date_input(
    "Afficher les données à partir de :",
    value=date(2023, 1, 1), # Date par défaut
    help="Sélectionnez la date à partir de laquelle vous souhaitez voir les données."
)
st.markdown("---")

# --- Fonctions de tracé de graphique ---
def plot_data(df, y_column, y_label, title):
    """Génère et affiche un graphique pour une colonne de données donnée."""
    df_filtered = df[df['DateHeure'].dt.date >= start_date]

    if df_filtered.empty or len(df_filtered) <= 1:
        st.info(f"Pas assez de données pour le graphique '{title}' à partir de la date sélectionnée.")
        return

    st.subheader(f"Graphique : {title}")
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_filtered['DateHeure'],
        y=df_filtered[y_column],
        mode='lines+markers',
        name='Mesures'
    ))

    # Calcul de la courbe de tendance LOWESS
    try:
        lowess = sm.nonparametric.lowess(
            endog=df_filtered[y_column],
            exog=df_filtered['DateHeure'].astype('int64'),
            frac=0.3
        )
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(lowess[:, 0]),
            y=lowess[:, 1],
            mode='lines',
            name='Tendance',
            line=dict(dash='dash')
        ))
    except Exception as e:
        st.warning(f"Impossible de calculer la courbe de tendance pour '{title}'. Erreur: {e}")

    fig.update_layout(
        title=f"Évolution de {title} avec courbe de tendance",
        xaxis_title="Date et Heure",
        yaxis_title=y_label,
        legend_title_text="Légende"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Lecture et affichage des données ---

# Données de Pression
df_pression = read_data_from_db('PressionSynthese')
if not df_pression.empty:
    df_pression['DateHeure'] = pd.to_datetime(df_pression['DateHeure'])
    df_pression['Systolique'] = pd.to_numeric(df_pression['Systolique'], errors='coerce')
    df_pression['Diastolique'] = pd.to_numeric(df_pression['Diastolique'], errors='coerce')
    plot_data(df_pression, 'Systolique', 'mmHg', "Pression Artérielle (Systolique)")
    plot_data(df_pression, 'Diastolique', 'mmHg', "Pression Artérielle (Diastolique)")
else:
    st.info("Aucune donnée de Pression Artérielle trouvée.")
st.markdown("---")

# Données de Glycémie
df_glycemie = read_data_from_db('glycemie')
if not df_glycemie.empty:
    df_glycemie['DateHeure'] = pd.to_datetime(df_glycemie['DateHeure'])
    df_glycemie['Valeur'] = pd.to_numeric(df_glycemie['Valeur'], errors='coerce')
    plot_data(df_glycemie, 'Valeur', 'mmol/L', "Glycémie")
else:
    st.info("Aucune donnée de Glycémie trouvée.")
st.markdown("---")

# Données de Poids
df_poids = read_data_from_db('poids')
if not df_poids.empty:
    df_poids['DateHeure'] = pd.to_datetime(df_poids['DateHeure'])
    # Ajout du sélecteur d'unité pour le poids
    unit = st.radio("Sélectionnez l'unité pour le graphique de poids :", ("kg", "lbs"))
    y_column = "Poids_kg" if unit == "kg" else "Poids_lbs"
    y_label = f"Poids ({unit})"
    df_poids[y_column] = pd.to_numeric(df_poids[y_column], errors='coerce')
    plot_data(df_poids, y_column, y_label, "Poids")
else:
    st.info("Aucune donnée de Poids trouvée.")