import streamlit as st

st.title("Basic Streamlit Test")
st.write("Hello World!")
st.success("If you see this, Streamlit is working")

name = st.text_input("Enter your name:")
if name:
    st.write(f"Hello {name}!")

if st.button("Click me"):
    st.balloons()
    st.write("Button clicked!")
