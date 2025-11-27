import streamlit as st
from datetime import datetime
import json

JSON_PATH = "user_info.json"
def load_users():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_user(users: dict):
    if isinstance(users, dict):
        cur_users = load_users()
        cur_users.append(users)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cur_users, f, indent=3)

users = load_users()

st.title("Practice Service")
st.write("Service for simple attending on HSE events")
tab1, tab2, tab3 = st.tabs(["authorization", "Student tab", "Admin tab"])

with tab1:
    name = st.text_area("Name", height=20)
    surname = st.text_area("Surname", height=20)
    number = st.text_area("Student ticket number", height=20)

    if st.button("Save"):
        try:
            save_user({"name": name, "surname": surname, "number": number, "score": 0})
            st.write("Authorization finished successful!")
        except Exception:
            st.write("Authorization finished unsuccessful!")

with tab2:
    check = st.button("Check score")
    if check:
        st.write(users[0].get("score"))

    e_name = st.text_area("Event name")
    submit = st.button("Submit")
    if submit:
        users[0]["score"] = users[0].get("score", 0) + 2
        st.write(users[0].get("score"))

with tab3:
    tasks=load_users()
    for id, val in enumerate(tasks):
        with st.container():
            name, surname, number, score = st.columns([2, 2, 2, 1])
            name.write(val.get("name"))
            surname.write(val.get("surname"))
            number.write(val.get("number"))
            score.write(val.get("score"))