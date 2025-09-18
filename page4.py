import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import statsmodels.api as sm

# --- Fonctions de gestion de la base de données ---
def get_db_connection():
    """
    Établit une connexion à la base de données SQLite.
    """
    try:
        conn = sqlite3.connect('mesures_sante.db')
        return conn
    except sqlite3.Error as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        return None

def create_poids_table_if_not_exists():
    """
    Crée la table 'poids' si elle n'existe pas.
    """
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poids (
                DateHeure TEXT PRIMARY KEY,
                Poids_kg REAL,
                Poids_lbs REAL
            )
        ''')
        conn.commit()
        conn.close()

def insert_new_data(df):
    """
    Insère de nouvelles données dans la table 'poids'.
    """
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        new_rows_count = 0
        for _, row in df.iterrows():
            try:
                # Utiliser INSERT OR IGNORE pour insérer uniquement les nouvelles lignes
                cursor.execute('''
                    INSERT OR IGNORE INTO poids (DateHeure, Poids_kg, Poids_lbs)
                    VALUES (?, ?, ?)
                ''', (row['DateHeure'], row['Poids_kg'], row['Poids_lbs']))
                if cursor.rowcount > 0:
                    new_rows_count += 1
            except sqlite3.IntegrityError:
                pass  # Ignorer les lignes déjà existantes
        conn.commit()
        conn.close()
        return new_rows_count
    return 0

def read_data_from_db():
    """
    Lit toutes les données de la table 'poids' et les retourne dans un DataFrame.
    """
    conn = get_db_connection()
    if conn:
        df = pd.read_sql_query("SELECT * FROM poids ORDER BY DateHeure", conn)
        conn.close()
        return df
    return pd.DataFrame()

# --- Configuration de la Page Streamlit ---
st.set_page_config(page_title="Suivi de Poids", layout="wide")
create_poids_table_if_not_exists()

# --- Titre de la Page ---
st.title("⚖️ Suivi de Poids")
st.markdown("---")

# --- Section 1: Importation et Sélection des Données ---
st.header("1. Importer votre fichier de données")
uploaded_file = st.file_uploader(
    "Choisissez un fichier CSV ou Excel",
    type=["csv", "xlsx"],
    help="Le fichier doit contenir des colonnes pour la date et les poids en kg et lbs."
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded_file, dtype=str).fillna('')
        else:
            df_input = pd.read_excel(uploaded_file, dtype=str).fillna('')

        st.success("Fichier importé avec succès ! Voici un aperçu :")
        st.dataframe(df_input.head())

        st.markdown("---")
        st.header("2. Associer vos colonnes")

        with st.form("column_selection_form"):
            available_columns = df_input.columns.tolist()
            col_datetime = st.selectbox("Colonne pour la date et l'heure :", available_columns)
            col_weight_kg = st.selectbox("Colonne pour le Poids (kg) :", available_columns)
            col_weight_lbs = st.selectbox("Colonne pour le Poids (lbs) :", available_columns)
            submit_button = st.form_submit_button(label="Valider et Enregistrer les Données")

        if submit_button:
            df_processed = df_input[[col_datetime, col_weight_kg, col_weight_lbs]].copy()
            df_processed.columns = ["Date-Heure", "Poids_kg", "Poids_lbs"]

            # --- Traitement des données et conversion des types ---
            df_processed["Date-Heure"] = pd.to_datetime(df_processed["Date-Heure"], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
            df_processed["Poids_kg"] = pd.to_numeric(df_processed["Poids_kg"], errors='coerce')
            df_processed["Poids_lbs"] = pd.to_numeric(df_processed["Poids_lbs"], errors='coerce')
            
            # Suppression des lignes avec des valeurs non valides
            df_processed.dropna(subset=["Date-Heure"], how='all', inplace=True)
            df_processed.dropna(subset=["Poids_kg", "Poids_lbs"], how='all', inplace=True)
            
            # Renommage des colonnes pour la base de données
            df_processed.rename(columns={'Date-Heure': 'DateHeure'}, inplace=True)
            
            new_rows_count = insert_new_data(df_processed)
            st.success(f"Données enregistrées avec succès ! {new_rows_count} nouvelles lignes ont été ajoutées.")

    except Exception as e:
        st.error(f"Une erreur est survenue lors du traitement : {e}")
        st.warning("Vérifiez le format de votre fichier et les colonnes sélectionnées.")

# --- Section 3: Visualisation des Données ---
st.markdown("---")
st.header("3. Graphique de suivi du poids")

# Sélection de l'unité par l'utilisateur
unit = st.radio("Sélectionnez l'unité de mesure pour le graphique :", ("kg", "lbs"))
y_column = "Poids_kg" if unit == "kg" else "Poids_lbs"
y_label = f"Poids ({unit})"

df_final = read_data_from_db()

if not df_final.empty:
    df_final['DateHeure'] = pd.to_datetime(df_final['DateHeure'])
    df_final[y_column] = pd.to_numeric(df_final[y_column], errors='coerce')
    df_final.dropna(subset=[y_column], inplace=True)

    if not df_final.empty and len(df_final) > 1:
        st.write(f"Graphique du poids ({unit}) en fonction du temps, avec sa courbe de tendance.")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_final['DateHeure'], y=df_final[y_column], mode='lines+markers', name='Poids'))
        
        # Calcul et ajout de la ligne de tendance LOWESS
        try:
            lowess_data = sm.nonparametric.lowess(endog=df_final[y_column], exog=df_final['DateHeure'].astype('int64'), frac=0.3)
            fig.add_trace(go.Scatter(x=pd.to_datetime(lowess_data[:, 0]), y=lowess_data[:, 1], mode='lines', name='Tendance', line=dict(dash='dash')))
        except Exception as e:
            st.warning(f"Impossible de calculer la ligne de tendance. Erreur: {e}")
        
        fig.update_layout(
            title=f"Évolution du Poids ({unit}) avec Courbe de Tendance",
            xaxis_title="Date et Heure",
            yaxis_title=y_label,
            legend_title_text="Légende"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Afficher les données enregistrées dans la base de données"):
            st.dataframe(df_final)
    elif not df_final.empty:
        st.warning(f"Il faut au moins deux points de données valides pour le poids en {unit} pour dessiner une courbe de tendance.")
        st.dataframe(df_final)
    else:
        st.info("La table `poids` est vide.")
else:
    st.info("Veuillez importer un fichier pour afficher le graphique.")