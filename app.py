import json
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from pypdf import PdfReader
import psycopg

# -------------------- إعدادات عامة --------------------
st.set_page_config(
    page_title="SFN | إدارة المخزون",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = "inventory_web.json"
LOW_STOCK_DEFAULT = 100

def get_setting(name, default=""):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return os.getenv(name, value)

DATABASE_URL = str(get_setting("DATABASE_URL", "")).strip()

DEFAULT_INVENTORY = {
    "P001": {"name": "ASHWAGANDHA MATEX 60 TAB", "balance": 2371, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100}
}

# -------------------- دالات الحفظ والتحميل السحابية والمحلية الهجينة --------------------
def db_connect():
    if not DATABASE_URL or "اكتب_كلمة_المرور_هنا" in DATABASE_URL:
        return None
    try:
        conn = psycopg.connect(DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS sfn_app_state (
                key_name TEXT PRIMARY KEY,
                json_data JSONB
            );""")
        conn.commit()
        return conn
    except Exception:
        return None

def load_data(file_name, default_value):
    conn = db_connect()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT json_data FROM sfn_app_state WHERE key_name = %s", (file_name,))
                row = cur.fetchone()
                if row and row is not None:
                    return row if isinstance(row, dict) else json.loads(row[0])
        except Exception:
            pass
        finally:
            conn.close()
    return default_value

def save_data(file_name, data):
    # حفظ فوري في الذاكرة الحية لضمان العرض المباشر أمام المستخدم
    st.session_state["inventory"] = data
    
    # محاولة الحفظ الاحتياطي في السحابة
    conn = db_connect()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sfn_app_state (key_name, json_data) 
                    VALUES (%s, %s)
                    ON CONFLICT (key_name) 
                    DO UPDATE SET json_data = EXCLUDED.json_data;
                """, (file_name, json.dumps(data, ensure_ascii=False)))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

# ضمان تهيئة الجلسة لعدم التصفير التلقائي
if "inventory" not in st.session_state:
    st.session_state["inventory"] = load_data(DATA_FILE, DEFAULT_INVENTORY)

# -------------------- واجهة لوحة تحكم المخزون --------------------
st.sidebar.title("⚙️ لوحة التحكم والإدارة")

st.sidebar.subheader("🚨 تصفير المستودع")
confirm_delete = st.sidebar.checkbox("أنا متأكد من رغبتي في مسح كل المخزون الحالي")
if st.sidebar.button("🗑️ مسح كافة المنتجات والبيانات", disabled=not confirm_delete):
    save_data(DATA_FILE, {})
    st.sidebar.success("تم مسح المخزون بالكامل بنجاح وتصفير الموقع!")
    st.rerun()

st.sidebar.subheader("📤 رفع مخزون جديد بالكامل")
uploaded_file = st.sidebar.file_uploader("اختر ملف المخزون الجديد:", type=["xlsx", "csv", "tsv", "txt"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            sample = uploaded_file.read(2048).decode('utf-8', errors='ignore')
            uploaded_file.seek(0)
            sep = ';' if ';' in sample and sample.count(';') > sample.count(',') else ','
            df = pd.read_csv(uploaded_file, sep=sep)
        else:
            df = pd.read_excel(uploaded_file, engine='calamine')
            
        df.columns = [str(col).strip().lower() for col in df.columns]
        required_cols = ['id', 'name', 'balance', 'cost', 'price', 'expiry', 'min_balance']
        
        if all(col in df.columns for col in required_cols):
            new_inventory = {}
            for _, row in df.iterrows():
                p_id = str(row['id']).strip()
                if not p_id or p_id.lower() == 'nan': continue
                new_inventory[p_id] = {
                    "name": str(row['name']).strip(),
                    "balance": int(pd.to_numeric(row['balance'], errors='coerce') or 0),
                    "expiry": str(row['expiry']).strip() if pd.notna(row['expiry']) else "غير محدد",
                    "cost": float(pd.to_numeric(row['cost'], errors='coerce') or 0.0),
                    "price": float(pd.to_numeric(row['price'], errors='coerce') or 0.0),
                    "min_balance": int(pd.to_numeric(row['min_balance'], errors='coerce') or 100)
                }
            
            # تحديث مباشر وفوري للجدول المعروض لتأكيد النجاح أمامك
            if new_inventory:
                save_data(DATA_FILE, new_inventory)
                st.sidebar.success("✅ تم تحديث ونشر المخزون الجديد بنجاح!")
                st.rerun()
        else:
            st.sidebar.error("❌ تأكد أن ملفك يحتوي على العناوين: id, name, balance, cost, price, expiry, min_balance")
    except Exception as e:
        st.sidebar.error(f"خطأ: {str(e)}")

# -------------------- عرض المخزون الأساسي --------------------
st.write("### 📦 المخزون الحالي في النظام أونلاين:")
if st.session_state["inventory"]:
    df_inv = pd.DataFrame.from_dict(st.session_state["inventory"], orient='index')
    st.dataframe(df_inv, use_container_width=True)
else:
    st.info("المخزون فارغ حالياً. يرجى اختيار ملفك الجديد من القائمة الجانبير لتنشيط النظام.")
