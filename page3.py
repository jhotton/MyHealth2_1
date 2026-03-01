import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm
import re

st.set_page_config(page_title="Suivi de la Glycémie", layout="wide")
st.title("🩸 Suivi de la Glycémie")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ET NETTOYAGE ---
st.header("📥 Importer des données")
uploaded_file = st.file_uploader("Choisissez votre fichier CSV", type="csv")

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    cols = df_raw.columns.tolist()
    
    c1, c2 = st.columns(2)
    with c1:
        sel_date = st.selectbox("Colonne Date/Heure", cols, index=0)
    with c2:
        sel_val = st.selectbox("Colonne Valeur", cols, index=1 if len(cols)>1 else 0)

    if st.button("🚀 Nettoyer et Synchroniser"):
        try:
            # 1. Copie de travail
            df_work = df_raw.copy()

            # --- LOGIQUE DE CONVERSION DE DATE PERSONNALISÉE ---
            month_map = {
                "janv.": "01", "févr.": "02", "mars": "03", "avr.": "04",
                "mai": "05", "juin": "06", "juill.": "07",
                "août": "08", "sept.": "09", "oct.": "10", "nov.": "11", "déc.": "12"
            }

            def clean_custom_date(date_str):
                try:
                    s = str(date_str).lower()
                    # Remplacement des mois via la table de conversion
                    for fr, num in month_map.items():
                        s = s.replace(fr, num)
                    
                    # Nettoyage des caractères parasites (virgules, le "h", espaces doubles)
                    s = s.replace(',', '').replace(' h ', ':').replace(' h', ':')
                    s = s.strip()
                    
                    # Tentative de conversion finale (Format attendu: "27 01 2026 09:39")
                    return pd.to_datetime(s, format="%d %m %Y %H:%M", errors='coerce')
                except:
                    return pd.NaT

            # Application du nettoyage
            df_work['DateHeure'] = df_work[sel_date].apply(clean_custom_date)

            # 2. NETTOYAGE DE LA VALEUR
            df_work['Valeur'] = df_work[sel_val].astype(str).str.replace(',', '.')
            df_work['Valeur'] = pd.to_numeric(df_work['Valeur'], errors='coerce')

            # 3. FILTRAGE ET PRÉPARATION
            df_to_push = df_work.dropna(subset=['DateHeure', 'Valeur'])[['DateHeure', 'Valeur']].copy()
            df_to_push['Note1'] = ""
            df_to_push['Note2'] = ""
            
            # Conversion en string pour Google Sheets (pour éviter les problèmes de format JSON)
            df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

            if df_to_push.empty:
                st.error("❌ Aucune donnée convertie. Format détecté non compatible.")
                st.write("Exemple lu :", df_raw[sel_date].iloc[0])
            else:
                # 4. ENVOI VERS GSHEETS
                try:
                    existing = conn.read(worksheet="glycemie", ttl=0)
                except:
                    existing = pd.DataFrame(columns=['DateHeure', 'Valeur', 'Note1', 'Note2'])

                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="glycemie", data=final)
                
                st.success(f"✅ {len(df_to_push)} lignes synchronisées !")
                st.cache_data.clear()

        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.markdown("---")

# --- SECTION 2 : AFFICHAGE ---
st.header("📈 Historique")

try:
    df_plot = conn.read(worksheet="glycemie", ttl=0)
    if not df_plot.empty:
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot['Valeur'] = pd.to_numeric(df_plot['Valeur'])
        df_plot = df_plot.sort_values('DateHeure')

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Valeur'], mode='lines+markers', name='Glycémie'))
        
        # Courbe de tendance
        try:
            lowess = sm.nonparametric.lowess(df_plot['Valeur'], df_plot['DateHeure'].astype('int64'), frac=0.3)
            fig.add_trace(go.Scatter(x=pd.to_datetime(lowess[:, 0]), y=lowess[:, 1], mode='lines', name='Tendance', line=dict(dash='dash', color='orange')))
        except: pass
        
        fig.update_layout(xaxis_title="Date", yaxis_title="mmol/L", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_plot, use_container_width=True)
except:
    st.info("En attente de données...")