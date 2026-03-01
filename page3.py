import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import statsmodels.api as sm

st.set_page_config(page_title="Suivi de la Glycémie", layout="wide")
st.title("🩸 Suivi de la Glycémie (Complet)")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ET MAPPING ---
st.header("📥 Importer des données")
uploaded_file = st.file_uploader("Choisissez votre fichier CSV", type="csv")

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    cols = df_raw.columns.tolist()
    
    st.info("Associez les colonnes de votre fichier aux champs de la base de données :")
    
    # Création de 4 colonnes pour les sélecteurs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_date = st.selectbox("Date et Heure", cols, index=0)
    with c2:
        sel_val = st.selectbox("Valeur (Glycémie)", cols, index=1 if len(cols)>1 else 0)
    with c3:
        sel_n1 = st.selectbox("Note 1 (ex: Repas)", ["Aucune"] + cols)
    with c4:
        sel_n2 = st.selectbox("Note 2 (ex: Feeling)", ["Aucune"] + cols)

    if st.button("🚀 Nettoyer et Synchroniser"):
        try:
            # --- LOGIQUE DE NETTOYAGE DE DATE (Votre format spécifique) ---
            month_map = {
                "janv.": "01", "févr.": "02", "mars": "03", "avr.": "04",
                "mai": "05", "juin": "06", "juill.": "07",
                "août": "08", "sept.": "09", "oct.": "10", "nov.": "11", "déc.": "12"
            }

            def clean_custom_date(date_str):
                try:
                    s = str(date_str).lower()
                    for fr, num in month_map.items():
                        s = s.replace(fr, num)
                    s = s.replace(',', '').replace(' h ', ':').replace(' h', ':')
                    s = s.strip()
                    # Format: "27 01 2026 09:39"
                    return pd.to_datetime(s, format="%d %m %Y %H:%M", errors='coerce')
                except:
                    return pd.NaT

            # --- CONSTRUCTION DU DATAFRAME FINAL ---
            df_to_push = pd.DataFrame()
            
            # 1. Traitement Date
            df_to_push['DateHeure'] = df_raw[sel_date].apply(clean_custom_date)
            
            # 2. Traitement Valeur (Virgule -> Point)
            val_clean = df_raw[sel_val].astype(str).str.replace(',', '.')
            df_to_push['Valeur'] = pd.to_numeric(val_clean, errors='coerce')
            
            # 3. Récupération des Notes
            df_to_push['Note1'] = df_raw[sel_n1] if sel_n1 != "Aucune" else ""
            df_to_push['Note2'] = df_raw[sel_n2] if sel_n2 != "Aucune" else ""

            # Nettoyage des lignes vides
            df_to_push = df_to_push.dropna(subset=['DateHeure', 'Valeur'])
            
            # Formatage de la date en texte pour Google Sheets
            df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

            if not df_to_push.empty:
                with st.spinner("Mise à jour du Cloud..."):
                    # Lecture de l'existant
                    try:
                        existing = conn.read(worksheet="glycemie", ttl=0)
                    except:
                        existing = pd.DataFrame(columns=['DateHeure', 'Valeur', 'Note1', 'Note2'])

                    # Fusion et suppression des doublons
                    final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                    
                    # Envoi
                    conn.update(worksheet="glycemie", data=final)
                    
                    st.success(f"✅ {len(df_to_push)} lignes synchronisées !")
                    st.cache_data.clear()
            else:
                st.error("Erreur : Aucune donnée valide détectée après nettoyage.")

        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.markdown("---")

# --- SECTION 2 : VISUALISATION ---
st.header("📈 Historique")

try:
    df_plot = conn.read(worksheet="glycemie", ttl=0)
    if not df_plot.empty:
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot['Valeur'] = pd.to_numeric(df_plot['Valeur'])
        df_plot = df_plot.sort_values('DateHeure')

        # Graphique
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Valeur'], mode='lines+markers', name='Glycémie'))
        
        # Courbe de tendance
        try:
            lowess = sm.nonparametric.lowess(df_plot['Valeur'], df_plot['DateHeure'].astype('int64'), frac=0.3)
            fig.add_trace(go.Scatter(x=pd.to_datetime(lowess[:, 0]), y=lowess[:, 1], mode='lines', name='Tendance', line=dict(dash='dash', color='orange')))
        except: pass
        
        fig.update_layout(xaxis_title="Date", yaxis_title="mmol/L", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau complet (incluant Note1 et Note2)
        st.subheader("📋 Liste des mesures")
        st.dataframe(df_plot[['DateHeure', 'Valeur', 'Note1', 'Note2']], use_container_width=True)
except:
    st.info("Aucune donnée à afficher.")