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
    "P001": {"name": "ASHWAGANDHA MATEX 60 TAB", "balance": 2371, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P002": {"name": "BLACK SEED OIL 1000MG 60CAP", "balance": 69, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P003": {"name": "GOFIT CHARCOAL 30 CAP", "balance": 4984, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P004": {"name": "GOFIT CURCUMIN 1000 MG 60 TAB", "balance": 4584, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P005": {"name": "ivy syrp", "balance": 831, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P006": {"name": "JOINT PLANET 90 TAB", "balance": 653, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P007": {"name": "MATOTHREX COLLAGEN 120 TAB", "balance": 0, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P008": {"name": "UGC MATEX MELATONIN 30 TAB", "balance": 1329, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P009": {"name": "ORA SMOOTH BLACKSEED SPRAY 60 ML", "balance": 1010, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P010": {"name": "ORA SMOOTH CLOVE&CINNAMON SPRAY", "balance": 2550, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P011": {"name": "ORA SMOOTH MINT SPRAY 60 ML", "balance": 7948, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P012": {"name": "ORA SMOOTH ORANGE SPRAY 60 ML", "balance": 8152, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P013": {"name": "RELAX-FREE MASSAGE CREAM 100 GM", "balance": 14, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P014": {"name": "SYMPHONY COLLAGEN FACE SERUM", "balance": 535, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P015": {"name": "SYMPHONY HAIR SERUM 5AMP 1M", "balance": 3664, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P016": {"name": "SYMPHONY HYPERTONIC SPRAY", "balance": 3408, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P017": {"name": "Symphony massage cream Colocynth Oil", "balance": 5171, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P018": {"name": "Symphony massage cream black seed oil", "balance": 6177, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P019": {"name": "SYMPHONY CREAM Apple Cider Vinegar", "balance": 7192, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P020": {"name": "SYMPHONY MASSAGE CREAM OSTRICH FAT", "balance": 4318, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P021": {"name": "SYMPHONY SHAMPO 200 ML", "balance": 368, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P022": {"name": "SYMPHONY HAIR MASK 200 GM", "balance": 10, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P023": {"name": "U.G.C D3 4000 I.U. 30 TAB", "balance": 0, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P024": {"name": "U.G.C MAN 30 TAB", "balance": 162, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P025": {"name": "d3+k2", "balance": 102, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P026": {"name": "U.G.C WOMAN 30 TAB", "balance": 37, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P027": {"name": "UGC COLLAGEN 10 SACHETS", "balance": 3038, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P028": {"name": "UGC COLLAGEN 30 SACHETS", "balance": 755, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P029": {"name": "comblix", "balance": 57, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P030": {"name": "VBLS MAGNI B6 90 TAB", "balance": 99, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P031": {"name": "VBLS SLIMMING 30 TAB", "balance": 1912, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P032": {"name": "VBLS VITAMIN-C 1000MG 30 TAB", "balance": 78, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P033": {"name": "omega3  60cap", "balance": 236, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P034": {"name": "cogni draw", "balance": 1902, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P035": {"name": "gelon 120", "balance": 430, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P036": {"name": "gelon60", "balance": 193, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P037": {"name": "rozichika", "balance": 64, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100},
    "P038": {"name": "shartic", "balance": 1376, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100}
}

STATE_KEYS = {DATA_FILE: "inventory", INVOICES_FILE: "invoices", MOVEMENTS_FILE: "movements"}

# -------------------- دالات الاتصال والحفظ --------------------
def db_connect():
    if not DATABASE_URL:
        return None
    try:
        conn = psycopg.connect(DATABASE_URL, connect_timeout=8)
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
                if row:
                    return row[0]
            save_data(file_name, default_value)
            return default_value
        except Exception:
            pass
        finally:
            conn.close()
    
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            return json.load(f)
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

st.sidebar.subheader("➕ إضافة منتج جديد")
with st.sidebar.form("add_new_product_form", clear_on_submit=True):
    p_id = st.text_input("كود المنتج (مثال: P039):").strip()
    p_name = st.text_input("اسم المنتج / السهم:").strip()
    p_balance = st.number_input("الرصيد الحالي / المخزون:", min_value=0, value=0, step=1)
    p_cost = st.number_input("التكلفة:", min_value=0.0, value=0.0)
    p_price = st.number_input("سعر البيع:", min_value=0.0, value=0.0)
    p_expiry = st.text_input("تاريخ الصلاحية:", value="غير محدد")
    p_min = st.number_input("الحد الأدنى للمخزون:", min_value=0, value=100)
    
    submit_product = st.form_submit_button("حفظ المنتج في المخزون")
    
    if submit_product:
        if not p_id or not p_name:
            st.sidebar.error("يرجى إدخال كود واسم المنتج أولاً!")
        elif p_id in st.session_state["inventory"]:
            st.sidebar.error("هذا الكود مستخدم بالفعل لمنتج آخر!")
        else:
            st.session_state["inventory"][p_id] = {
                "name": p_name,
                "balance": p_balance,
                "expiry": p_expiry,
                "cost": p_cost,
                "price": p_price,
                "min_balance": p_min
            }
            save_data(DATA_FILE, st.session_state["inventory"])
            st.sidebar.success(f"تم إضافة المنتج ({p_name}) بنجاح!")
            st.rerun()

# -------------------- عرض المخزون الأساسي --------------------
