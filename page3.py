import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm
import sqlite3

# --- Database Management Functions ---
def get_db_connection():
    try:
        conn = sqlite3.connect('mesures_sante.db')
        return conn
    except sqlite3.Error as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        return None

def create_glycemie_table_if_not_exists():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS glycemie (
                DateHeure TEXT PRIMARY KEY,
                Valeur REAL,
                Note1 TEXT,
                Note2 TEXT
            )
        ''')
        conn.commit()
        conn.close()

def insert_new_data(df):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        new_rows_count = 0
        for _, row in df.iterrows():
            try:
                # Use INSERT OR REPLACE for existing keys or new rows
                cursor.execute('''
                    INSERT OR REPLACE INTO glycemie (DateHeure, Valeur, Note1, Note2)
                    VALUES (?, ?, ?, ?)
                ''', (row['DateHeure'], row['Valeur'], row['Note1'], row['Note2']))
                new_rows_count += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        conn.close()
        return new_rows_count
    return 0

def read_data_from_db():
    conn = get_db_connection()
    if conn:
        df = pd.read_sql_query("SELECT * FROM glycemie ORDER BY DateHeure", conn)
        conn.close()
        return df
    return pd.DataFrame()

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Suivi de Glycémie", layout="wide")
create_glycemie_table_if_not_exists()

# --- Page Title ---
st.title("🩸 Suivi de Glycémie")
st.markdown("---")

# --- Section 1: Data Import and Selection ---
st.header("1. Importer votre fichier de données")
uploaded_file = st.file_uploader(
    "Choisissez un fichier CSV",
    type="csv",
    help="Le fichier doit contenir des colonnes pour la date, la glycémie et des notes."
)

if uploaded_file is not None:
    try:
        df_input = pd.read_csv(uploaded_file, dtype=str).fillna('')
        st.success("Fichier importé avec succès ! Voici un aperçu :")
        st.dataframe(df_input.head())

        st.markdown("---")
        st.header("2. Associer vos colonnes")
        st.info('**Note :** Le format attendu pour la date-heure est `J MMM AAAA, HH "h" MM` (ex: `3 sept. 2025, 09 h 51`).')

        with st.form("column_selection_form"):
            available_columns = df_input.columns.tolist()
            col_datetime = st.selectbox("Colonne pour la date et l'heure :", available_columns)
            col_glucose = st.selectbox("Colonne pour la Glycémie (mmol/L) :", available_columns)
            col_note1 = st.selectbox("Colonne pour la Note 1 :", available_columns)
            col_note2 = st.selectbox("Colonne pour la Note 2 :", available_columns)
            submit_button = st.form_submit_button(label="Valider et Enregistrer les Données")

        if submit_button:
            df_processed = df_input[[col_datetime, col_glucose, col_note1, col_note2]].copy()
            df_processed.columns = ["Date-Heure", "Glycémie (mmol/L)", "Note-1", "Note-2"]

            # Month map is applied here
            month_map = {
                "janv.": "01", "févr.": "02", "mars": "03", "avr.": "04",
                "mai": "05", "juin": "06", "juill.": "07",
                "août": "08", "sept.": "09", "oct.": "10", "nov.": "11", "déc.": "12"
            }
            date_series = df_processed["Date-Heure"].astype(str)
            for month_str, month_num in month_map.items():
                date_series = date_series.str.replace(month_str, month_num, regex=False)
            date_format_string = "%d %m %Y, %H h %M"
            df_processed["Date-Heure"] = pd.to_datetime(date_series, format=date_format_string, errors='coerce')
            
            # --- The key fix is here ---
            # Convert Timestamp column to a string format for SQLite
            df_processed.dropna(subset=["Date-Heure"], inplace=True)
            df_processed['Glycémie (mmol/L)'] = pd.to_numeric(df_processed['Glycémie (mmol/L)'], errors='coerce')
            df_processed['Date-Heure'] = df_processed['Date-Heure'].dt.strftime('%Y-%m-%d %H:%M:%S')

            # Rename columns before insertion
            df_processed.rename(columns={'Date-Heure': 'DateHeure', 'Glycémie (mmol/L)': 'Valeur', 'Note-1': 'Note1', 'Note-2': 'Note2'}, inplace=True)
            
            new_rows_count = insert_new_data(df_processed)
            st.success(f"Données enregistrées avec succès dans la base de données ! {new_rows_count} nouvelles lignes ont été ajoutées.")

    except Exception as e:
        st.error(f"Une erreur est survenue lors du traitement : {e}")
        st.warning("Vérifiez que le format de date dans votre fichier correspond bien au format attendu et que les colonnes sélectionnées sont les bonnes.")

# --- Section 3: Data Visualization ---
st.markdown("---")
st.header("3. Graphique de suivi de la glycémie")

df_final = read_data_from_db()

if not df_final.empty:
    df_final['DateHeure'] = pd.to_datetime(df_final['DateHeure'])
    df_final['Valeur'] = pd.to_numeric(df_final['Valeur'], errors='coerce')
    df_final.dropna(subset=["Valeur"], inplace=True)

    if not df_final.empty and len(df_final) > 1:
        st.write("Graphique de la glycémie en fonction du temps, avec sa courbe de tendance.")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_final['DateHeure'], y=df_final['Valeur'], mode='lines+markers', name='Mesures'))
        
        # Calculate and add the LOWESS trend line
        lowess_data = sm.nonparametric.lowess(endog=df_final['Valeur'], exog=df_final['DateHeure'].astype('int64'), frac=0.3)
        fig.add_trace(go.Scatter(x=pd.to_datetime(lowess_data[:, 0]), y=lowess_data[:, 1], mode='lines', name='Tendance', line=dict(dash='dash')))
        
        fig.update_layout(
            title="Évolution de la Glycémie avec Courbe de Tendance",
            xaxis_title="Date et Heure",
            yaxis_title="Glycémie (mmol/L)",
            legend_title_text="Légende"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Afficher les données enregistrées dans la base de données"):
            st.dataframe(df_final)
    elif not df_final.empty:
        st.warning("Il faut au moins deux points de données pour dessiner une courbe de tendance.")
        st.dataframe(df_final)
    else:
        st.info("La table `glycemie` est vide.")
else:
    st.info("Veuillez importer un fichier pour afficher le graphique.")