import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="MoneyWise - Mobile Banking Style",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS ตกแต่งให้คล้ายแอปธนาคาร
st.markdown("""
    <style>
    .main-header {
        font-size: 24px;
        font-weight: 700;
        color: #1E293B;
    }
    .balance-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        padding: 24px;
        border-radius: 20px;
        color: white;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# เชื่อมต่อฐานข้อมูล Supabase
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

# สร้างตารางถ้ายังไม่มี (เพิ่มตาราง budgets สำหรับเก็บงบประมาณ)
def init_db():
    try:
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                limit_amount NUMERIC
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล: {e}")

init_db()

# ดึงข้อมูลธุรกรรม
def load_data():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM transactions ORDER BY trans_date DESC, id DESC", conn)
    conn.close()
    return df

# ดึงข้อมูลงบประมาณ
def load_budgets():
    conn = get_connection()
    df_b = pd.read_sql("SELECT * FROM budgets", conn)
    conn.close()
    return df_b

# เมนูด้านข้าง (Sidebar)
st.sidebar.markdown("### 💳 เมนูหลัก")
menu = st.sidebar.radio("เลือกทำรายการ", [
    "🏠 หน้าแรก (Dashboard)", 
    "➕ เพิ่มรายการ (Income/Expense)", 
    "🎯 ตั้งเป้าหมายงบประมาณ (Budget)", 
    "📜 ประวัติรายการ (Statement)"
])

df = load_data()
df_budgets = load_budgets()

# คำนวณยอดเงินรวม
total_income = df[df['trans_type'] == 'รายรับ']['amount'].sum() if not df.empty else 0
total_expense = df[df['trans_type'] == 'รายจ่าย']['amount'].sum() if not df.empty else 0
balance = total_income - total_expense

# ----------------- 1. หน้าแรก (Dashboard) -----------------
if menu == "🏠 หน้าแรก (Dashboard)":
    st.markdown("<p class='main-header'>💸 ภาพรวมบัญชีของคุณ</p>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="balance-card">
            <p style="margin: 0; font-size: 14px; opacity: 0.8;">ยอดเงินคงเหลือสุทธิ</p>
            <h1 style="margin: 5px 0 15px 0; font-size: 36px; font-weight: 700;">฿{balance:,.2f}</h1>
            <div style="display: flex; justify-content: space-between; font-size: 14px;">
                <span>📥 รายรับรวม: ฿{total_income:,.2f}</span>
                <span>📤 รายจ่ายรวม: ฿{total_expense:,.2f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if not df.empty:
        st.markdown("### 📊 สัดส่วนรายจ่ายตามหมวดหมู่")
        expense_df = df[df['trans_type'] == 'รายจ่าย']
        if not expense_df.empty:
            cat_expense = expense_df.groupby('category')['amount'].sum()
            st.bar_chart(cat_expense)
            
            # เช็กงบประมาณเทียบกับที่ใช้ไปจริง
            if not df_budgets.empty:
                st.markdown("### 🎯 สถานะงบประมาณของคุณ")
                for index, row in df_budgets.iterrows():
                    cat = row['category']
                    limit = float(row['limit_amount'])
                    spent = float(cat_expense.get(cat, 0))
                    progress = min(spent / limit, 1.0) if limit > 0 else 0
                    
                    st.text(f"หมวด: {cat} (ใช้ไป ฿{spent:,.2f} / ตั้งไว้ ฿{limit:,.2f})")
                    st.progress(progress)
                    if spent > limit:
                        st.warning(f"⚠️ เตือน: หมวด '{cat}' ใช้เกินงบประมาณที่ตั้งไว้แล้ว!")
        else:
            st.info("ยังไม่มีข้อมูลรายจ่ายในระบบ")
            
        st.markdown("### 🕒 รายการล่าสุด")
        st.dataframe(df[['trans_date', 'trans_type', 'category', 'amount', 'note']].head(5), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลการเงินในระบบ ลองไปที่เมนู 'เพิ่มรายการ' ได้เลยครับ")

# ----------------- 2. เพิ่มรายการ -----------------
elif menu == "➕ เพิ่มรายการ (Income/Expense)":
    st.markdown("<p class='main-header'>➕ บันทึก รายรับ - รายจ่าย</p>", unsafe_allow_html=True)
    
    with st.form("trans_form", clear_on_submit=True):
        trans_date = st.date_input("วันที่ทำรายการ", datetime.today())
        trans_type = st.selectbox("ประเภทรายการ", ["รายจ่าย", "รายรับ"])
        
        if trans_type == "รายจ่าย":
            category = st.selectbox("หมวดหมู่", ["อาหาร/เครื่องดื่ม", "เดินทาง", "ช้อปปิ้ง", "Bills/ค่าน้ำไฟ", "บันเทิง", "อื่นๆ"])
        else:
            category = st.selectbox("หมวดหมู่", ["เงินเดือน", "โบนัส", "รายได้เสริม", "อื่นๆ"])
            
        amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, format="%.2f")
        note = st.text_input("บันทึกช่วยจำ (Note)")
        
        submitted = st.form_submit_button("💾 บันทึกรายการ")
        
        if submitted:
            if amount > 0:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO transactions (trans_date, trans_type, category, amount, note) VALUES (%s, %s, %s, %s, %s)",
                    (trans_date, trans_type, category, amount, note)
                )
                conn.commit()
                cur.close()
                conn.close()
                st.success("บันทึกข้อมูลสำเร็จเรียบร้อยครับ! 🎉")
            else:
                st.warning("กรุณากรอกจำนวนเงินให้มากกว่า 0")

# ----------------- 3. ตั้งเป้าหมายงบประมาณ (Budget) -----------------
elif menu == "🎯 ตั้งเป้าหมายงบประมาณ (Budget)":
    st.markdown("<p class='main-header'>🎯 ตั้งงบประมาณรายจ่ายต่อหมวดหมู่</p>", unsafe_allow_html=True)
    
    with st.form("budget_form"):
        b_category = st.selectbox("เลือกหมวดหมู่รายจ่าย", ["อาหาร/เครื่องดื่ม", "เดินทาง", "ช้อปปิ้ง", "Bills/ค่าน้ำไฟ", "บันเทิง", "อื่นๆ"])
        b_limit = st.number_input("กำหนดงบประมาณสูงสุด (บาท/เดือน)", min_value=0.0, format="%.2f")
        b_submitted = st.form_submit_button("💾 บันทึกงบประมาณ")
        
        if b_submitted:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO budgets (category, limit_amount) VALUES (%s, %s) ON CONFLICT (category) DO UPDATE SET limit_amount = EXCLUDED.limit_amount",
                (b_category, b_limit)
            )
            conn.commit()
            cur.close()
            conn.close()
            st.success(f"ตั้งงบประมาณสำหรับหมวด '{b_category}' เป็นจำนวน ฿{b_limit:,.2f} เรียบร้อยครับ! 🎯")
            
    st.markdown("### 📋 งบประมาณที่คุณตั้งไว้ทั้งหมด")
    if not df_budgets.empty:
        st.dataframe(df_budgets, use_container_width=True)
    else:
        st.info("ยังไม่มีการตั้งงบประมาณในระบบ")

# ----------------- 4. ประวัติรายการ (Statement) -----------------
elif menu == "📜 ประวัติรายการ (Statement)":
    st.markdown("<p class='main-header'>📜 ประวัติธุรกรรมทั้งหมด</p>", unsafe_allow_html=True)
    
    if not df.empty:
        search_cat = st.selectbox("กรองตามหมวดหมู่", ["ทั้งหมด"] + list(df['category'].unique()))
        if search_cat != "ทั้งหมด":
            filtered_df = df[df['category'] == search_cat]
        else:
            filtered_df = df
            
        st.dataframe(filtered_df[['trans_date', 'trans_type', 'category', 'amount', 'note']], use_container_width=True)
    else:
        st.info("ยังไม่มีประวัติรายการในระบบครับ")