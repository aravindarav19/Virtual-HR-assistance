import streamlit as st
from components import conversation_flow

# Set page configuration
st.set_page_config(page_title="Virtual HR Assistant", layout="centered")

# Run the full assistant logic
conversation_flow.run()
