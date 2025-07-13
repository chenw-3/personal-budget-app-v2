import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

# ---------------------------
# Utility Functions
# ---------------------------

def get_data_path(email, month_year):
    safe_email = email.replace("@", "_at_").replace(".", "_dot_")
    folder = f"data/{safe_email}"
    os.makedirs(folder, exist_ok=True)
    return f"{folder}/{month_year}.csv"

def load_data(email, month_year):
    path = get_data_path(email, month_year)
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame(columns=["type", "category", "amount"])

def save_data(email, month_year, df):
    path = get_data_path(email, month_year)
    df.to_csv(path, index=False)

def display_budget_vs_actual(budget_df, actual_df):
    st.subheader("🧾 Budget vs Actual with Overspending Flags")
    rows = []
    for _, row in budget_df.iterrows():
        cat = row["category"]
        budget_amt = row["amount"]
        actual_amt = actual_df[actual_df["category"] == cat]["amount"].sum()
        status = "✅ OK"
        if actual_amt > budget_amt:
            status = "❌ Over Budget"
        elif actual_amt > 0.9 * budget_amt:
            status = "⚠️ Near Limit"
        rows.append({"Category": cat, "Budgeted": budget_amt, "Actual": actual_amt, "Status": status})

    comp_df = pd.DataFrame(rows)
    st.dataframe(comp_df)

    fig, ax = plt.subplots()
    ax.bar(comp_df["Category"], comp_df["Budgeted"], label="Budgeted", alpha=0.5)
    ax.bar(comp_df["Category"], comp_df["Actual"], label="Actual", alpha=0.8)
    ax.set_ylabel("Amount ($)")
    ax.set_title("Budget vs Actuals")
    ax.legend()
    st.pyplot(fig)

def get_all_months(email):
    safe_email = email.replace("@", "_at_").replace(".", "_dot_")
    folder = f"data/{safe_email}"
    if not os.path.exists(folder):
        return []
    return [f.replace(".csv", "") for f in os.listdir(folder) if f.endswith(".csv")]

def dime_calculator(debt, income, years, mortgage, edu_cost, num_children):
    return debt + (income * years) + mortgage + (edu_cost * num_children)

# ---------------------------
# Streamlit App
# ---------------------------

st.set_page_config(page_title="Smart Budgeting Tool", layout="wide")
st.title("💼 Smart Budgeting and Life Planning App")

# User Email & Month
if "email" not in st.session_state:
    st.session_state.email = st.text_input("Enter your email to begin:", "")
if not st.session_state.email:
    st.stop()

today = datetime.today()
current_month = today.strftime("%Y-%m")
email = st.session_state.email

# Load current data
df = load_data(email, current_month)
budget_df = df[df["type"] == "budget"]
actual_df = df[df["type"] == "actual"]

# Sidebar Navigation
page = st.sidebar.radio("Go to", [
    "📅 Set Monthly Budget",
    "💳 Track Spending",
    "📊 50/30/20 Report",
    "🛡️ Insurance Calculator",
    "📁 Review Past Months"
])

# ---------------------------
# Set Monthly Budget
# ---------------------------
if page == "📅 Set Monthly Budget":
    st.header("📅 Monthly Budget Setup")
    if budget_df.empty:
        st.info("🔔 It's a new month. Please set your budget categories and amounts.")

    categories = st.multiselect("Select or type categories", options=[
        "Housing", "Utilities", "Groceries", "Transportation",
        "Healthcare", "Insurance", "Debt Payments", "Entertainment", "Savings", "Education"
    ])
    for cat in categories:
        amount = st.number_input(f"{cat} budget amount ($)", min_value=0.0, step=10.0, key=f"budget_{cat}")
        if not budget_df[(budget_df["category"] == cat) & (budget_df["type"] == "budget")].empty:
            df.loc[(df["category"] == cat) & (df["type"] == "budget"), "amount"] = amount
        else:
            df = pd.concat([df, pd.DataFrame([{"type": "budget", "category": cat, "amount": amount}])], ignore_index=True)

    save_data(email, current_month, df)
    st.success("✅ Budget saved!")

# ---------------------------
# Track Spending
# ---------------------------
elif page == "💳 Track Spending":
    st.header("💳 Track Your Spending")
    if budget_df.empty:
        st.warning("⚠️ Please set your monthly budget first.")
    else:
        cat = st.selectbox("Select a category", budget_df["category"].unique())
        amt = st.number_input("Amount Spent ($)", min_value=0.0, step=5.0)
        if st.button("Add Expense"):
            df = pd.concat([df, pd.DataFrame([{"type": "actual", "category": cat, "amount": amt}])], ignore_index=True)
            save_data(email, current_month, df)
            st.success("✅ Expense recorded!")

        st.subheader("📊 Budget vs Actuals This Month")
        display_budget_vs_actual(budget_df, actual_df)

# ---------------------------
# 50/30/20 Rule
# ---------------------------
elif page == "📊 50/30/20 Report":
    st.header("📊 50/30/20 Rule Analysis")

    total_income = budget_df["amount"].sum()
    if total_income == 0:
        st.warning("Please define a monthly budget to perform analysis.")
        st.stop()

    limits = {
        "Needs": total_income * 0.50,
        "Wants": total_income * 0.30,
        "Savings": total_income * 0.20,
    }

    categorized = {"Needs": 0, "Wants": 0, "Savings": 0}
    needs = ["Housing", "Utilities", "Groceries", "Transportation", "Healthcare", "Insurance", "Debt Payments"]
    wants = ["Entertainment"]
    savings = ["Savings", "Education"]

    for _, row in actual_df.iterrows():
        if row["category"] in needs:
            categorized["Needs"] += row["amount"]
        elif row["category"] in wants:
            categorized["Wants"] += row["amount"]
        elif row["category"] in savings:
            categorized["Savings"] += row["amount"]
        else:
            categorized["Wants"] += row["amount"]

    st.markdown("""
    ### 📘 Understanding the 50/30/20 Rule:
    - **50% Needs**: Essential expenses (housing, utilities, groceries, etc.)
    - **30% Wants**: Lifestyle choices (entertainment, dining out, etc.)
    - **20% Savings**: Future planning (retirement, education, savings)

    The bars below show your actual spending compared to these targets:
    """)

    fig, ax = plt.subplots()
    ax.bar(categorized.keys(), categorized.values(), label="Actual")
    ax.bar(limits.keys(), limits.values(), alpha=0.3, label="Target")
    ax.set_ylabel("Amount ($)")
    ax.set_title("50/30/20 Spending Breakdown")
    ax.legend()
    st.pyplot(fig)

# ---------------------------
# Insurance Calculator
# ---------------------------
elif page == "🛡️ Insurance Calculator":
    st.header("🛡️ DIME Life Insurance Calculator")

    with st.expander("What is the DIME Method?"):
        st.markdown("""
        **DIME** helps calculate how much life insurance you may need:
        - **D**ebt: Your current outstanding obligations
        - **I**ncome: Support your family for X years
        - **M**ortgage: Remaining home loan
        - **E**ducation: Future cost for your children
        """)

    col1, col2 = st.columns(2)
    with col1:
        debt = st.number_input("Outstanding Debt ($)", min_value=0.0, step=500.0)
        income = st.number_input("Annual Income ($)", min_value=0.0, step=1000.0)
        years = st.number_input("Years to Support Family", min_value=1, value=10)
    with col2:
        mortgage = st.number_input("Remaining Mortgage ($)", min_value=0.0, step=1000.0)
        edu = st.number_input("Education Cost per Child ($)", min_value=0.0, step=1000.0)
        kids = st.number_input("Number of Children", min_value=0, step=1, value=0)

    coverage = dime_calculator(debt, income, years, mortgage, edu, kids)
    st.success(f"✅ Recommended Insurance Coverage: **${coverage:,.2f}**")

# ---------------------------
# Review Past Months
# ---------------------------
elif page == "📁 Review Past Months":
    st.header("📁 Review Historical Budgets")
    months = get_all_months(email)
    if not months:
        st.info("No data found for past months.")
    else:
        selected_month = st.selectbox("Select a month", months)
        review_df = load_data(email, selected_month)
        if review_df.empty:
            st.info("No data for selected month.")
        else:
            b_df = review_df[review_df["type"] == "budget"]
            a_df = review_df[review_df["type"] == "actual"]
            display_budget_vs_actual(b_df, a_df)
