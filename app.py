import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="MoneyWise - Personal Finance", page_icon="💚", layout="centered")

# เชื่อมต่อฐานข้อมูล Supabase จาก secrets.toml
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

# สร้างตารางข้อมูลถ้ายังไม่มี
def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            trans_date DATE,
            trans_type TEXT,
            category TEXT,
            amount NUMERIC,
            note TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# หัวข้อแอป
st.title("💚 MoneyWise")
st.caption("จัดการเงินของคุณ ให้ง่ายขึ้นทุกวัน")

# เมนูเลือกการทำงาน
menu = st.sidebar.radio("เมนูการใช้งาน", ["ภาพรวมการเงิน", "เพิ่มรายการใหม่"])

# ดึงข้อมูลทั้งหมดจากฐานข้อมูล
def load_data():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM transactions ORDER BY trans_date DESC", conn)
    conn.close()
    return df

df = load_data()

if menu == "ภาพรวมการเงิน":
    st.subheader("สรุปการเงินทั้งหมด")
    
    if not df.empty:
        total_income = df[df["trans_type"] == "รายรับ"]["amount"].sum()
        total_expense = df[df["trans_type"] == "รายจ่าย"]["amount"].sum()
        balance = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 เงินคงเหลือ", f"฿{balance:,.2f}")
        col2.metric("📈 รายรับรวม", f"฿{total_income:,.2f}")
        col3.metric("📉 รายจ่ายรวม", f"฿{total_expense:,.2f}")
        
        st.divider()
        st.subheader("ประวัติรายการล่าสุด")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลรายการเงินในระบบ ลองไปที่เมนู 'เพิ่มรายการใหม่' ได้เลยครับ")

elif menu == "เพิ่มรายการใหม่":
    st.subheader("📝 บันทึกรายรับ - รายจ่าย")
    
    with st.form("transaction_form", clear_on_submit=True):
        trans_date = st.date_input("วันที่", datetime.today())
        trans_type = st.selectbox("ประเภท", ["รายรับ", "รายจ่าย"])
        category = st.text_input("หมวดหมู่ (เช่น ค่าอาหาร, เงินเดือน, ช้อปปิ้ง)")
        amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, format="%.2f")
        note = st.text_input("บันทึกเพิ่มเติม (ถ้ามี)")
        
        submitted = st.form_submit_button("บันทึกข้อมูล")
        
        if submitted:
            if category and amount > 0:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO transactions (trans_date, trans_type, category, amount, note) VALUES (%s, %s, %s, %s, %s)",
                    (trans_date, trans_type, category, amount, note)
                )
                conn.commit()
                cur.close()
                conn.close()
                st.success("บันทึกข้อมูลสำเร็จเรียบร้อยแล้วครับ!")
            else:
                st.warning("กรุณากรอกหมวดหมู่และจำนวนเงินให้ถูกต้องด้วยครับ")