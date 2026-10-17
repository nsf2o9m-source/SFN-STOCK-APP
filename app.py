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
INVOICES_FILE = "invoices_web.json"
MOVEMENTS_FILE = "movements_web.json"
LOW_STOCK_DEFAULT = 100

def get_setting(name, default=""):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return os.getenv(name, value)

ADMIN_PASSWORD = str(get_setting("ADMIN_PASSWORD", "")).strip()
DATABASE_URL = str(get_setting("DATABASE_URL", "")).strip()

DEFAULT_INVENTORY = {
    "P001": {"name": "ASHWAGANDHA MATEX 60 TAB", "balance": 2371, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100}
}

# -------------------- دالات الحفظ والتحميل --------------------
def db_connect():
    if not DATABASE_URL:
        return None
    try:
        conn = psycopg.connect(DATABASE_URL, connect_timeout=5)
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
                    return row if isinstance(row, tuple) else row
            save_data(file_name, default_value)
            return default_value
        except Exception:
            pass
        finally:
            conn.close()
    
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_value
    return default_value

def save_data(file_name, data):
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
    
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "inventory" not in st.session_state:
    st.session_state["inventory"] = load_data(DATA_FILE, DEFAULT_INVENTORY)
if "invoices" not in st.session_state:
    st.session_state["invoices"] = load_data(INVOICES_FILE, [])
if "movements" not in st.session_state:
    st.session_state["movements"] = load_data(MOVEMENTS_FILE, [])

# -------------------- واجهة لوحة تحكم المخزون --------------------
st.sidebar.title("⚙️ لوحة التحكم والإدارة")

st.sidebar.subheader("🚨 تصفير المستودع")
confirm_delete = st.sidebar.checkbox("أنا متأكد من رغبتي في مسح كل المخزون الحالي")
if st.sidebar.button("🗑️ مسح كافة المنتجات والبيانات", disabled=not confirm_delete):
    st.session_state["inventory"] = {}
    st.session_state["invoices"] = []
    st.session_state["movements"] = []
    save_data(DATA_FILE, {})
    save_data(INVOICES_FILE, [])
    save_data(MOVEMENTS_FILE, [])
    st.sidebar.success("تم مسح المخزون بالكامل بنجاح وتصفير الموقع!")
    st.rerun()

# ميزة الرفع الذكي للمخزون الجديد (يدعم Excel, CSV, TSV)
st.sidebar.subheader("📤 رفع مخزون جديد بالكامل")
uploaded_file = st.sidebar.file_uploader("اختر ملف المخزون الجديد:", type=["xlsx", "csv", "tsv", "txt"])

if uploaded_file is not None:
    try:
        # تحديد طريقة القراءة بناءً على نوع الملف المرفوع تلقائياً
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.tsv') or uploaded_file.name.endswith('.txt'):
            df = pd.read_csv(uploaded_file, sep='\t')
        else:
            df = pd.read_excel(uploaded_file, engine='calamine')
            
        # تحويل أسماء الأعمدة إلى حروف صغيرة وإزالة الفراغات لضمان التعرف عليها بأي شكل
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        required_cols = ['id', 'name', 'balance', 'cost', 'price', 'expiry', 'min_balance']
        if all(col in df.columns for col in required_cols):
            if st.sidebar.button("🔄 اعتماد وتحديث المخزون الجديد"):
                new_inventory = {}
                for _, row in df.iterrows():
                    p_id = str(row['id']).strip()
                    new_inventory[p_id] = {
                        "name": str(row['name']).strip(),
                        "balance": int(pd.to_numeric(row['balance'], errors='coerce') or 0),
                        "expiry": str(row['expiry']).strip() if pd.notna(row['expiry']) else "غير محدد",
                        "cost": float(pd.to_numeric(row['cost'], errors='coerce') or 0.0),
                        "price": float(pd.to_numeric(row['price'], errors='coerce') or 0.0),
                        "min_balance": int(pd.to_numeric(row['min_balance'], errors='coerce') or 100)
                    }
                st.session_state["inventory"] = new_inventory
                save_data(DATA_FILE, new_inventory)
                st.sidebar.success("✅ تم تحديث المستودع بالكامل بناءً على ملفك!")
                st.rerun()
        else:
            st.sidebar.error("❌ تأكد أن ملفك يحتوي على العناوين التالية في السطر الأول تماماً: id, name, balance, cost, price, expiry, min_balance")
    except Exception as e:
        st.sidebar.error(f"خطأ أثناء قراءة الملف: {str(e)}")

st.sidebar.subheader("➕ إضافة منتج يدوياً")
with st.sidebar.form("add_new_product_form", clear_on_submit=True):
    p_id = st.text_input("كود المنتج (P039):").strip()
    p_name = st.text_input("اسم المنتج / السهم:").strip()
    p_balance = st.number_input("الرصيد:", min_value=0, value=0, step=1)
    p_cost = st.number_input("التكلفة:", min_value=0.0, value=0.0)
    p_price = st.number_input("السعر:", min_value=0.0, value=0.0)
    p_expiry = st.text_input("الصلاحية:", value="غير محدد")
    p_min = st.number_input("الحد الأدنى:", min_value=0, value=100)
    
    submit_product = st.form_submit_button("حفظ المنتج يدوياً")
    
    if submit_product:
        if not p_id or not p_name:
            st.sidebar.error("يرجى إدخال كود واسم المنتج!")
        elif p_id in st.session_state["inventory"]:
            st.sidebar.error("هذا الكود مستخدم بالفعل!")
        else:
            st.session_state["inventory"][p_id] = {
                "name": p_name, "balance": p_balance, "expiry": p_expiry,
                "cost": p_cost, "price": p_price, "min_balance": p_min
            }
            save_data(DATA_FILE, st.session_state["inventory"])
            st.sidebar.success(f"تم إضافة {p_name}!")
            st.rerun()

# -------------------- عرض المخزون الأساسي --------------------
st.write("### 📦 المخزون الحالي في النظام أونلاين:")
if st.session_state["inventory"]:
    df_inv = pd.DataFrame.from_dict(st.session_state["inventory"], orient='index')
    st.dataframe(df_inv, use_container_width=True)
else:
    st.info("المخزون فارغ حالياً. يمكنك تصفح الشريط الجانبي لرفع ملف منتجاتك الجديدة.")
