import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm

st.set_page_config(page_title="Suivi de la Glycémie", layout="wide")
st.title("🩸 Suivi de la Glycémie (Format Import Spécifique)")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ET NETTOYAGE ---
st.header("📥 Importer des données")
uploaded_file = st.file_uploader("Choisissez votre fichier CSV de glycémie", type="csv")

if uploaded_file is not None:
    df_upload = pd.read_csv(uploaded_file)
    st.write("Aperçu des données brutes :")
    st.dataframe(df_upload.head(3))

    cols = df_upload.columns.tolist()
    st.info("Associez les colonnes de votre fichier :")
    
    col_a, col_b = st.columns(2)
    with col_a:
        sel_date = st.selectbox("Colonne Date/Heure", cols, index=0)
    with col_b:
        sel_val = st.selectbox("Colonne Valeur", cols, index=1 if len(cols)>1 else 0)

    if st.button("🚀 Nettoyer et Synchroniser"):
        with st.spinner("Application de la logique de nettoyage..."):
            try:
                # 1. Création du DataFrame de destination
                df_to_push = pd.DataFrame()
                
                # 2. APPLICATION DE VOTRE LOGIQUE DE DATE (Fichier Original)
                # On convertit en texte et on traite le caractère " à "
                date_series = df_upload[sel_date].astype(str)
                date_series = date_series.str.replace(' à ', ' ', regex=False).str.strip()
                
                # Conversion avec format spécifique (JJ/MM/AAAA HH:MM)
                df_to_push['DateHeure'] = pd.to_datetime(date_series, dayfirst=True, errors='coerce')
                
                # 3. Traitement de la valeur (Virgule -> Point)
                val_series = df_upload[sel_val].astype(str).str.replace(',', '.')
                df_to_push['Valeur'] = pd.to_numeric(val_series, errors='coerce')
                
                # Colonnes vides pour Note1 et Note2 (Structure Google Sheet)
                df_to_push['Note1'] = ""
                df_to_push['Note2'] = ""

                # Suppression des lignes invalides
                df_to_push = df_to_push.dropna(subset=['DateHeure', 'Valeur'])

                # 4. ENVOI VERS GOOGLE SHEETS
                try:
                    existing = conn.read(worksheet="glycemie", ttl=0)
                except:
                    existing = pd.DataFrame()

                # Fusion et dédoublonnage sur la date
                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="glycemie", data=final)
                
                st.success(f"✅ {len(df_to_push)} mesures synchronisées avec succès !")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erreur lors du traitement : {e}")

st.markdown("---")

# --- SECTION 2 : GRAPHIQUE ET TABLEAU ---
st.header("📈 Historique de Glycémie")

try:
    df_plot = conn.read(worksheet="glycemie", ttl=0)
    
    if not df_plot.empty:
        # On s'assure que les types sont corrects pour Plotly
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot['Valeur'] = pd.to_numeric(df_plot['Valeur'])
        df_plot = df_plot.sort_values('DateHeure')

        if len(df_plot) > 1:
            fig = go.Figure()
            # Tracé des mesures
            fig.add_trace(go.Scatter(
                x=df_plot['DateHeure'], 
                y=df_plot['Valeur'], 
                mode='lines+markers', 
                name='Glycémie (mmol/L)',
                line=dict(color='#FF4B4B')
            ))
            
            # Courbe de tendance LOWESS
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
                    line=dict(dash='dash', color='orange')
                ))
            except: pass
            
            fig.update_layout(xaxis_title="Temps", yaxis_title="mmol/L", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Données enregistrées (Google Sheets)")
        st.dataframe(df_plot, use_container_width=True)
    else:
        st.info("Aucune donnée disponible.")
except Exception as e:
    st.error(f"Erreur d'affichage : {e}")