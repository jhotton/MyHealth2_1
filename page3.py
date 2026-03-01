import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm

st.set_page_config(page_title="Suivi de la Glycémie", layout="wide")
st.title("🩸 Suivi de la Glycémie (Format Spécifique)")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ET TRAITEMENT SPÉCIFIQUE ---
st.header("📥 Importer des données")
uploaded_file = st.file_uploader("Choisissez votre fichier CSV de glycémie", type="csv")

if uploaded_file is not None:
    # Lecture initiale
    df_upload = pd.read_csv(uploaded_file)
    st.write("Aperçu du fichier brut :")
    st.dataframe(df_upload.head(3))

    cols = df_upload.columns.tolist()
    st.info("Associez les colonnes (votre logique de nettoyage sera appliquée à la date) :")
    
    c1, c2 = st.columns(2)
    with c1:
        sel_date = st.selectbox("Colonne Date/Heure", cols, index=0)
    with c2:
        sel_val = st.selectbox("Colonne Valeur (Glycémie)", cols, index=1 if len(cols)>1 else 0)

    if st.button("🚀 Nettoyer et Synchroniser"):
        with st.spinner("Traitement du format de date..."):
            try:
                df_to_push = pd.DataFrame()
                
                # --- VOTRE LOGIQUE ORIGINALE DE NETTOYAGE ---
                # On récupère la colonne sélectionnée
                date_col = df_upload[sel_date].astype(str)
                
                # Suppression du "à " et nettoyage des espaces (votre logique initiale)
                date_col = date_col.str.replace(' à ', ' ', regex=False).str.strip()
                
                # Conversion en datetime (format JJ/MM/AAAA HH:MM)
                df_to_push['DateHeure'] = pd.to_datetime(date_col, dayfirst=True, errors='coerce')
                
                # Traitement de la valeur (virgule -> point)
                val_col = df_upload[sel_val].astype(str).str.replace(',', '.')
                df_to_push['Valeur'] = pd.to_numeric(val_col, errors='coerce')
                
                # Notes par défaut si non présentes
                df_to_push['Note1'] = ""
                df_to_push['Note2'] = ""

                # Suppression des erreurs de conversion
                df_to_push = df_to_push.dropna(subset=['DateHeure', 'Valeur'])

                # --- SYNCHRONISATION GOOGLE SHEETS ---
                try:
                    existing = conn.read(worksheet="glycemie", ttl=0)
                except:
                    existing = pd.DataFrame()

                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="glycemie", data=final)
                
                st.success(f"✅ {len(df_to_push)} mesures traitées et envoyées au Cloud !")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erreur lors du traitement : {e}")

st.markdown("---")

# --- SECTION 2 : GRAPHIQUE ET TABLEAU ---
st.header("📈 Historique")

try:
    df_plot = conn.read(worksheet="glycemie", ttl=0)
    
    if not df_plot.empty:
        # Assurer le formatage pour le graphique
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot['Valeur'] = pd.to_numeric(df_plot['Valeur'])
        df_plot = df_plot.sort_values('DateHeure')

        if len(df_plot) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Valeur'], mode='lines+markers', name='Glycémie'))
            
            # Tendance LOWESS
            lowess = sm.nonparametric.lowess(df_plot['Valeur'], df_plot['DateHeure'].astype('int64'), frac=0.3)
            fig.add_trace(go.Scatter(x=pd.to_datetime(lowess[:, 0]), y=lowess[:, 1], mode='lines', name='Tendance', line=dict(dash='dash', color='white')))
            
            fig.update_layout(xaxis_title="Temps", yaxis_title="mmol/L", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Données enregistrées (Cloud)")
        st.dataframe(df_plot, use_container_width=True)
    else:
        st.info("Aucune donnée enregistrée.")
except Exception as e:
    st.error(f"Erreur d'affichage : {e}")