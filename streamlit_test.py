import streamlit as st

st.set_page_config(page_title="Test App", layout="wide")
st.title("🧪 Streamlit Test")
st.write("If you can see this, Streamlit is working!")
st.success("✅ Basic Streamlit functionality confirmed")

# Test basic components
if st.button("Test Button"):
    st.balloons()
    st.write("Button clicked!")

st.info("This is a minimal test to verify Streamlit loads properly in Modal")
