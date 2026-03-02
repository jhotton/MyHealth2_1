import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go

st.set_page_config(page_title="Tableau de Bord Santé", layout="wide")
st.title("🏥 Résumé Global de Santé")

# Connexion unique
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            df['DateHeure'] = pd.to_datetime(df['DateHeure'])
            return df.sort_values('DateHeure', ascending=False)
    except:
        return pd.DataFrame()
    return pd.DataFrame()

# Chargement des données
df_gly = get_data("glycemie")
df_pre = get_data("PressionSynthese")
df_poids = get_data("poids")

# --- SECTION 1 : DERNIÈRES MESURES (KPI) ---
st.header("📌 Dernières constantes")
k1, k2, k3, k4 = st.columns(4)

with k1:
    if not df_gly.empty:
        last_val = df_gly.iloc[0]['Valeur']
        st.metric("Glycémie", f"{last_val} mmol/L", delta=None)
        st.caption(f"Le {df_gly.iloc[0]['DateHeure'].strftime('%d/%m à %H:%M')}")
    else:
        st.metric("Glycémie", "N/A")

with k2:
    if not df_pre.empty:
        last_sys = df_pre.iloc[0]['Systolique']
        last_dia = df_pre.iloc[0]['Diastolique']
        st.metric("Pression", f"{int(last_sys)}/{int(last_dia)}", help="mmHg")
        st.caption(f"Le {df_pre.iloc[0]['DateHeure'].strftime('%d/%m à %H:%M')}")
    else:
        st.metric("Pression", "N/A")

with k3:
    if not df_pre.empty and 'Pouls' in df_pre.columns:
        last_pouls = df_pre.iloc[0]['Pouls']
        st.metric("Pouls", f"{int(last_pouls)} BPM")
    else:
        st.metric("Pouls", "N/A")

with k4:
    if not df_poids.empty:
        last_p = df_poids.iloc[0]['Poids_kg']
        st.metric("Poids", f"{last_p:.1f} kg")
        st.caption(f"Le {df_poids.iloc[0]['DateHeure'].strftime('%d/%m')}")
    else:
        st.metric("Poids", "N/A")

st.markdown("---")

# --- SECTION 2 : APERÇU GRAPHIQUE RAPIDE ---
st.header("📉 Tendances rapides (7 derniers jours)")

c1, c2 = st.columns(2)

with c1:
    st.subheader("Glycémie")
    if not df_gly.empty:
        # On ne prend que les 20 dernières mesures pour la clarté
        df_sub = df_gly.head(20).sort_values('DateHeure')
        fig = go.Figure(go.Scatter(x=df_sub['DateHeure'], y=df_sub['Valeur'], mode='lines+markers', line=dict(color='#FF4B4B')))
        fig.update_layout(height=300, margin=dict(l=0,r=0,b=0,t=0), template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée de glycémie.")

with c2:
    st.subheader("Poids")
    if not df_poids.empty:
        df_sub_p = df_poids.head(10).sort_values('DateHeure')
        fig_p = go.Figure(go.Scatter(x=df_sub_p['DateHeure'], y=df_sub_p['Poids_kg'], mode='lines+markers', line=dict(color='#00B4D8')))
        fig_p.update_layout(height=300, margin=dict(l=0,r=0,b=0,t=0), template="plotly_dark")
        st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("Aucune donnée de poids.")

# --- SECTION 3 : NOTES RÉCENTES ---
st.markdown("---")
if not df_gly.empty or not df_pre.empty:
    st.header("📝 Notes et observations")
    # On combine les notes si elles existent
    notes = []
    if not df_gly.empty:
        for i, row in df_gly.head(3).iterrows():
            if row['Note1'] and str(row['Note1']) != 'nan':
                notes.append(f"🔴 **Glycémie ({row['DateHeure'].strftime('%d/%m')}):** {row['Note1']}")
    
    if not df_pre.empty:
        for i, row in df_pre.head(3).iterrows():
            if 'Note1' in row and row['Note1'] and str(row['Note1']) != 'nan':
                notes.append(f"🔵 **Pression ({row['DateHeure'].strftime('%d/%m')}):** {row['Note1']}")

    if notes:
        for n in notes:
            st.write(n)
    else:
        st.write("Aucune note récente.")