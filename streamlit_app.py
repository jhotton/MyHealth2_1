import streamlit as st

##st.title("MyHealth")
##st.write(
##    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
##)

import streamlit as st
import pandas as pd
import numpy as np
import time


# Define the pages
main_page = st.Page("main.py", title="Accueil MyHealth")
page_2 = st.Page("page2.py", title="Pression")
page_3 = st.Page("page3.py", title="Glycémie")
page_4 = st.Page("page4.py", title="Poids")
adminDB = st.Page("adminDB.py", title="admin")

# Set up navigation
pg = st.navigation([main_page, page_2,page_3, page_4, adminDB])#, page_3,page_4])

# Run the selected page
pg.run()
