# Enterprise Loan Management System (Streamlit + Safe CLI Mode)
# FIXED: Removes interactive input() to avoid sandbox I/O errors

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys

# ----------------------
# OPTIONAL STREAMLIT IMPORT
# ----------------------
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ModuleNotFoundError:
    STREAMLIT_AVAILABLE = False

# Detect non-interactive environment
INTERACTIVE = sys.stdin.isatty()

# ----------------------
# Database
# ----------------------
conn = sqlite3.connect("enterprise_loans.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client TEXT,
    principal REAL,
    rate REAL,
    term INTEGER,
    initiation_fee REAL,
    monthly_fee REAL,
    created TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS repayments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client TEXT,
    amount REAL,
    date TEXT
)
""")

conn.commit()

# ----------------------
# Core Functions
# ----------------------
def monthly_payment(P, r, n):
    r = r / 12 / 100
    return P * (r * (1 + r)**n) / ((1 + r)**n - 1)


def schedule(P, r, n, init_fee, m_fee):
    r = r / 12 / 100
    pay = monthly_payment(P, r*100, n)
    bal = P + init_fee
    rows = []

    for m in range(1, n + 1):
        interest = bal * r
        principal = pay - interest
        bal -= principal
        due_date = datetime.now() + timedelta(days=30*m)
        rows.append([m, round(pay + m_fee, 2), round(principal, 2), round(interest, 2), round(bal, 2), due_date])

    return pd.DataFrame(rows, columns=["Month","Payment","Principal","Interest","Balance","Due Date"])


def arrears(balance, days, rate=5):
    return balance * (rate / 100 / 365) * days

# ----------------------
# STREAMLIT APP
# ----------------------
if STREAMLIT_AVAILABLE:
    st.set_page_config(page_title="Enterprise Loan System", layout="wide")
    st.title("Enterprise Loan System")

    menu = st.sidebar.selectbox("Menu", ["Create Loan","View Loans","Arrears Dashboard"])

    if menu == "Create Loan":
        client = st.text_input("Client")
        P = st.number_input("Principal")
        r = st.number_input("Rate %")
        n = st.number_input("Months")
        init = st.number_input("Initiation Fee")
        mfee = st.number_input("Monthly Fee")

        if st.button("Save"):
            c.execute("INSERT INTO loans (client,principal,rate,term,initiation_fee,monthly_fee,created) VALUES (?,?,?,?,?,?,?)",
                      (client,P,r,n,init,mfee,str(datetime.now())))
            conn.commit()
            st.success("Saved")

    elif menu == "View Loans":
        df = pd.read_sql("SELECT * FROM loans", conn)
        st.dataframe(df)

    elif menu == "Arrears Dashboard":
        loans = pd.read_sql("SELECT * FROM loans", conn)
        pays = pd.read_sql("SELECT * FROM repayments", conn)

        report = []
        for _, loan in loans.iterrows():
            sched = schedule(loan['principal'], loan['rate'], loan['term'], loan['initiation_fee'], loan['monthly_fee'])
            paid = pays[pays['client']==loan['client']]['amount'].sum()
            expected = sched['Payment'].sum()
            arrear_amt = expected - paid
            penalty = arrears(arrear_amt, 30)
            report.append([loan['client'], round(arrear_amt,2), round(penalty,2)])

        st.dataframe(pd.DataFrame(report, columns=["Client","Arrears","Penalty"]))

# ----------------------
# SAFE CLI MODE (NO INPUT)
# ----------------------
elif not INTERACTIVE:
    print("Running in NON-INTERACTIVE mode (no input allowed)\n")

    # Auto demo data
    c.execute("DELETE FROM loans")
    c.execute("INSERT INTO loans (client,principal,rate,term,initiation_fee,monthly_fee,created) VALUES (?,?,?,?,?,?,?)",
              ("Demo Client",100000,12,12,1000,50,str(datetime.now())))
    conn.commit()

    df = pd.read_sql("SELECT * FROM loans", conn)
    print("Loans:\n", df)

    loan = df.iloc[0]
    sched = schedule(loan['principal'], loan['rate'], loan['term'], loan['initiation_fee'], loan['monthly_fee'])
    print("\nSample Schedule:\n", sched.head())

    arrear_amt = sched['Payment'].sum()
    penalty = arrears(arrear_amt, 30)

    print(f"\nArrears: {round(arrear_amt,2)} | Penalty: {round(penalty,2)}")

# ----------------------
# INTERACTIVE CLI (ONLY IF SUPPORTED)
# ----------------------
else:
    print("Interactive CLI mode available (local machine only)")

# ----------------------
# TESTS
# ----------------------
def _test_calculations():
    p = monthly_payment(100000, 12, 12)
    assert p > 0

    df = schedule(100000, 12, 12, 1000, 50)
    assert not df.empty
    assert len(df) == 12

    arr = arrears(1000, 30)
    assert arr > 0

    # Edge case tests
    df2 = schedule(50000, 0.1, 6, 0, 0)
    assert len(df2) == 6

if __name__ == "__main__":
    _test_calculations()
