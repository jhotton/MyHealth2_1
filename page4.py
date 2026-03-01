import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm

# --- Configuration de la page ---
st.set_page_config(page_title="Suivi du Poids", layout="wide")
st.title("⚖️ Suivi du Poids")

# --- Connexion à Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def save_to_gsheets(new_df):
    """
    Récupère les données existantes, fusionne avec les nouvelles,
    supprime les doublons basés sur 'DateHeure' et met à jour Google Sheets.
    """
    try:
        # 1. Lire les données actuelles
        existing_df = conn.read(worksheet="poids", ttl=0)
    except Exception:
        existing_df = pd.DataFrame(columns=['DateHeure', 'Poids_kg', 'Poids_lbs'])

    # 2. Fusionner et dédoublonner (on garde la version la plus récente en cas de doublon)
    updated_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['DateHeure'], keep='last')
    
    # 3. Envoyer vers Google Sheets
    conn.update(worksheet="poids", data=updated_df)
    return len(new_df)

# --- Section 1 : Importation de données ---
st.header("Importer de nouvelles mesures")
uploaded_file = st.file_uploader("Choisissez un fichier CSV pour le poids", type="csv")

if uploaded_file is not None:
    try:
        df_new = pd.read_csv(uploaded_file)
        
        # Vérification minimale des colonnes nécessaires
        required_columns = ['DateHeure', 'Poids_kg', 'Poids_lbs']
        if all(col in df_new.columns for col in required_columns):
            st.success("Fichier chargé avec succès !")
            st.dataframe(df_new.head())

            if st.button("Synchroniser avec Google Sheets"):
                with st.spinner("Mise à jour du Cloud..."):
                    count = save_to_gsheets(df_new)
                    st.success(f"✅ {count} nouvelles mesures synchronisées !")
                    # On force le rechargement pour mettre à jour le graphique
                    st.cache_data.clear()
        else:
            st.error(f"Le fichier doit contenir les colonnes : {', '.join(required_columns)}")
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")

st.markdown("---")

# --- Section 2 : Visualisation des données ---
st.header("Évolution du Poids")

# Lecture des données depuis le Cloud
try:
    df_final = conn.read(worksheet="poids", ttl=0)
except Exception:
    df_final = pd.DataFrame()

if not df_final.empty:
    # Conversion de la colonne date
    df_final['DateHeure'] = pd.to_datetime(df_final['DateHeure'])
    df_final = df_final.sort_values('DateHeure')

    # Choix de l'unité (KG ou LBS) comme dans votre version originale
    unit = st.radio("Sélectionnez l'unité d'affichage :", ("kg", "lbs"), key="poids_unit")
    y_column = "Poids_kg" if unit == "kg" else "Poids_lbs"
    y_label = f"Poids ({unit})"

    if y_column in df_final.columns:
        # Nettoyage des données pour le graphique
        df_plot = df_final.dropna(subset=[y_column]).copy()
        df_plot[y_column] = pd.to_numeric(df_plot[y_column], errors='coerce')

        if len(df_plot) > 1:
            fig = go.Figure()

            # Courbe des mesures
            fig.add_trace(go.Scatter(
                x=df_plot['DateHeure'],
                y=df_plot[y_column],
                mode='lines+markers',
                name=f'Poids ({unit})',
                line=dict(color='#3366CC')
            ))

            # Calcul de la ligne de tendance LOWESS
            try:
                # On utilise l'index temporel converti en entier pour le calcul statistique
                lowess_data = sm.nonparametric.lowess(
                    endog=df_plot[y_column], 
                    exog=df_plot['DateHeure'].astype('int64'), 
                    frac=0.3
                )
                fig.add_trace(go.Scatter(
                    x=pd.to_datetime(lowess_data[:, 0]),
                    y=lowess_data[:, 1],
                    mode='lines',
                    name='Tendance',
                    line=dict(dash='dash', color='orange')
                ))
            except Exception as e:
                st.warning(f"Courbe de tendance indisponible : {e}")

            fig.update_layout(
                title=f"Historique du Poids avec Tendance ({unit})",
                xaxis_title="Date",
                yaxis_title=y_label,
                template="plotly_white",
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # Option d'affichage du tableau brut
            with st.expander("Voir les données brutes"):
                st.dataframe(df_final)
        else:
            st.info("Ajoutez au moins deux mesures pour voir le graphique.")
    else:
        st.warning(f"La colonne '{y_column}' est manquante dans la feuille Google Sheets.")
else:
    st.info("Aucune donnée enregistrée dans Google Sheets pour le moment.")