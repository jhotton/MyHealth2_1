import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm

st.set_page_config(page_title="Suivi de la Glycémie", layout="wide")
st.title("🩸 Suivi de la Glycémie (Version Robuste)")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION AVEC MAPPING ---
st.header("📥 Importer des données")
uploaded_file = st.file_uploader("Choisissez votre fichier CSV", type="csv")

if uploaded_file is not None:
    df_upload = pd.read_csv(uploaded_file)
    st.write("Aperçu du fichier importé :")
    st.dataframe(df_upload.head(3))

    st.info("Associez les colonnes de votre fichier aux colonnes de destination :")
    
    # Création des sélecteurs pour mapper les colonnes
    cols = df_upload.columns.tolist()
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_date = st.selectbox("Date et Heure", cols, index=cols.index('DateHeure') if 'DateHeure' in cols else 0)
    with c2:
        sel_val = st.selectbox("Valeur (Glycémie)", cols, index=cols.index('Valeur') if 'Valeur' in cols else 0)
    with c3:
        sel_n1 = st.selectbox("Note 1 (Optionnel)", ["Aucune"] + cols)
    with c4:
        sel_n2 = st.selectbox("Note 2 (Optionnel)", ["Aucune"] + cols)

    if st.button("🚀 Synchroniser avec Google Sheets"):
        # 1. Préparation du DataFrame formaté
        df_to_push = pd.DataFrame()
        df_to_push['DateHeure'] = df_upload[sel_date]
        df_to_push['Valeur'] = df_upload[sel_val]
        df_to_push['Note1'] = df_upload[sel_n1] if sel_n1 != "Aucune" else ""
        df_to_push['Note2'] = df_upload[sel_n2] if sel_n2 != "Aucune" else ""

        # 2. Nettoyage immédiat avant l'envoi
        # Remplacement virgule par point
        if df_to_push['Valeur'].dtype == object:
            df_to_push['Valeur'] = df_to_push['Valeur'].astype(str).str.replace(',', '.')
        df_to_push['Valeur'] = pd.to_numeric(df_to_push['Valeur'], errors='coerce')
        
        # Format Date
        df_to_push['DateHeure'] = pd.to_datetime(df_to_push['DateHeure'], dayfirst=True, errors='coerce')
        df_to_push = df_to_push.dropna(subset=['DateHeure', 'Valeur'])

        # 3. Fusion avec l'existant
        with st.spinner("Mise à jour du Cloud..."):
            try:
                try:
                    existing = conn.read(worksheet="glycemie", ttl=0)
                except:
                    existing = pd.DataFrame()

                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="glycemie", data=final)
                st.success(f"✅ {len(df_to_push)} lignes ajoutées/mises à jour !")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erreur lors de l'envoi : {e}")

st.markdown("---")

# --- SECTION 2 : AFFICHAGE ---
st.header("📈 Historique et Tendance")

try:
    df_plot = conn.read(worksheet="glycemie", ttl=0)
    
    if not df_plot.empty:
        # Nettoyage pour affichage (au cas où des données sales seraient déjà dans la sheet)
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'], errors='coerce')
        if df_plot['Valeur'].dtype == object:
            df_plot['Valeur'] = df_plot['Valeur'].astype(str).str.replace(',', '.')
        df_plot['Valeur'] = pd.to_numeric(df_plot['Valeur'], errors='coerce')
        df_plot = df_plot.dropna(subset=['DateHeure', 'Valeur']).sort_values('DateHeure')

        # Graphique
        if len(df_plot) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Valeur'], mode='lines+markers', name='Glycémie'))
            
            # Tendance
            lowess = sm.nonparametric.lowess(df_plot['Valeur'], df_plot['DateHeure'].astype('int64'), frac=0.3)
            fig.add_trace(go.Scatter(x=pd.to_datetime(lowess[:, 0]), y=lowess[:, 1], mode='lines', name='Tendance', line=dict(dash='dash', color='white')))
            
            fig.update_layout(xaxis_title="Date", yaxis_title="mmol/L", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        # Tableau au bas
        st.subheader("📋 Données enregistrées")
        st.dataframe(df_plot, use_container_width=True)
    else:
        st.info("Aucune donnée dans Google Sheets.")
except Exception as e:
    st.error(f"Erreur technique : {e}")