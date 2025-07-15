import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import bcrypt
import database as db

# ---------------------------
# App Initialization
# ---------------------------
st.set_page_config(page_title="Smart Budget App", layout="wide", initial_sidebar_state="expanded")
st.markdown("<style>body { background-color: #f9f9f9; }</style>", unsafe_allow_html=True)
db.init_db()

# ---------------------------
# Authentication
# ---------------------------
def login_form():
    st.subheader("🔐 Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = db.authenticate_user(email, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.email = email
            st.rerun()
        else:
            st.error("Invalid email or password.")

def signup_form():
    st.subheader("📝 Sign Up")
    email = st.text_input("New Email")
    password = st.text_input("New Password", type="password")
    if st.button("Create Account"):
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        success = db.create_user(email, hashed)
        if success:
            st.success("Account created. You can now log in.")
        else:
            st.error("Email already registered.")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    auth_choice = st.sidebar.radio("Account", ["Login", "Sign Up"])
    if auth_choice == "Login":
        login_form()
    else:
        signup_form()
    st.stop()

# ---------------------------
# Main Dashboard
# ---------------------------
email = st.session_state.email
user_id = db.get_user_id(email)
today = datetime.today()
current_month = today.strftime("%Y-%m")

st.sidebar.title("📊 Navigation")
page = st.sidebar.radio("Menu", ["Set Budget", "Add Expense", "View/Edit Expenses", "50/30/20 Report"])

# ---------------------------
# Set Budget Page
# ---------------------------
if page == "Set Budget":
    st.header("📅 Monthly Budget Setup")
    categories = st.multiselect("Choose Categories", [
        "Housing", "Utilities", "Groceries", "Transportation",
        "Healthcare", "Insurance", "Debt Payments", "Entertainment",
        "Savings", "Education"
    ])
    for cat in categories:
        amt = st.number_input(f"{cat} Budget ($)", min_value=0.0, step=10.0, key=f"b_{cat}")
        if amt > 0:
            db.save_budget(user_id, current_month, cat, amt)
    st.success("✅ Budget Saved")

# ---------------------------
# Add Expense Page
# ---------------------------
elif page == "Add Expense":
    st.header("💳 Add an Expense")
    budget_data = db.get_budget(user_id, current_month)
    if not budget_data:
        st.warning("Please set your monthly budget first.")
    else:
        cat = st.selectbox("Category", [b["category"] for b in budget_data])
        amt = st.number_input("Expense Amount ($)", min_value=0.0, step=5.0)
        if st.button("Add"):
            db.add_expense(user_id, current_month, cat, amt)
            st.success("✅ Expense Added")
            st.rerun()

# ---------------------------
# View/Edit Expenses
# ---------------------------
elif page == "View/Edit Expenses":
    st.header("✏️ Edit Your Expenses")
    rows = database.get_expenses(user_id, current_month)
    if not rows:
        st.info("No expenses logged yet.")
    else:
        # ✅ FIX: Convert each row to dictionary
        df = pd.DataFrame([dict(r) for r in rows])
        df["Edit"] = df["id"].apply(lambda x: f"edit_{x}")
        for _, row in df.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(f"{row['timestamp'][:16]} | {row['category']}")
            with col2:
                new_amt = st.number_input("Amount", value=row["amount"], key=f"edit_{row['id']}")
            with col3:
                if st.button("💾", key=f"save_{row['id']}"):
                    database.update_expense(row["id"], new_amt)
                    st.success("Updated.")
                    st.rerun()
                if st.button("🗑️", key=f"del_{row['id']}"):
                    database.delete_expense(row["id"])
                    st.warning("Deleted.")
                    st.rerun()

# ---------------------------
# 50/30/20 Report
# ---------------------------
elif page == "50/30/20 Report":
    st.header("📊 50/30/20 Budget Rule")
    actuals = db.get_expenses(user_id, current_month)
    budget = db.get_budget(user_id, current_month)

    total_budget = sum([b["amount"] for b in budget])
    if total_budget == 0:
        st.warning("Please set your monthly budget to see analysis.")
        st.stop()

    limits = {
        "Needs": total_budget * 0.50,
        "Wants": total_budget * 0.30,
        "Savings": total_budget * 0.20,
    }

    categorized = {"Needs": 0, "Wants": 0, "Savings": 0}
    needs = ["Housing", "Utilities", "Groceries", "Transportation", "Healthcare", "Insurance", "Debt Payments"]
    wants = ["Entertainment"]
    savings = ["Savings", "Education"]

    for row in actuals:
        if row["category"] in needs:
            categorized["Needs"] += row["amount"]
        elif row["category"] in wants:
            categorized["Wants"] += row["amount"]
        elif row["category"] in savings:
            categorized["Savings"] += row["amount"]
        else:
            categorized["Wants"] += row["amount"]

    status = []
    for k in categorized:
        ratio = categorized[k] / limits[k]
        if ratio <= 0.9:
            status.append("🟢 Under Budget")
        elif ratio <= 1.0:
            status.append("🟡 At Limit")
        else:
            status.append("🔴 Over Budget")

    st.write("### Analysis")
    analysis_df = pd.DataFrame({
        "Category": ["Needs", "Wants", "Savings"],
        "Limit ($)": list(limits.values()),
        "Actual ($)": list(categorized.values()),
        "Status": status
    })
    st.dataframe(analysis_df)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(analysis_df["Category"], analysis_df["Limit ($)"], label="Limit", alpha=0.5)
    ax.bar(analysis_df["Category"], analysis_df["Actual ($)"], label="Actual", alpha=0.7)
    ax.set_title("50/30/20 Budget Breakdown")
    ax.set_ylabel("Amount ($)")
    ax.legend()
    plt.xticks(rotation=15)
    st.pyplot(fig)
