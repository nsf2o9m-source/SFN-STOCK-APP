import json
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from pypdf import PdfReader

# -------------------- إعدادات عامة --------------------
st.set_page_config(
    page_title="SFN | إدارة المخزون",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOW_STOCK_DEFAULT = 100

# القائمة القديمة الافتراضية (تُستخدم فقط إذا لم يقم المستخدم بتحديث المخزون)
if "default_loaded" not in st.session_state:
    st.session_state["default_loaded"] = {
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

# تهيئة وإدارة المخزون داخل الذاكرة الحية للموقع مباشرة لثباته أونلاين
if "inventory" not in st.session_state:
    st.session_state["inventory"] = st.session_state["default_loaded"]
if "invoices" not in st.session_state:
    st.session_state["invoices"] = []
if "movements" not in st.session_state:
    st.session_state["movements"] = []

# -------------------- واجهة لوحة تحكم المخزون --------------------
st.sidebar.title("⚙️ لوحة التحكم والإدارة")

st.sidebar.subheader("🚨 تصفير المستودع")
confirm_delete = st.sidebar.checkbox("أنا متأكد من رغبتي في مسح كل المخزون الحالي")
if st.sidebar.button("🗑️ مسح كافة المنتجات والبيانات", disabled=not confirm_delete):
    st.session_state["inventory"] = {}
    st.session_state["invoices"] = []
    st.session_state["movements"] = []
    st.sidebar.success("تم مسح المخزون بالكامل وتصفير الموقع!")
    st.rerun()

# ميزة الرفع الفوري المباشر وحفظه في ذاكرة النظام الحية
st.sidebar.subheader("📤 رفع مخزون جديد بالكامل")
uploaded_file = st.sidebar.file_uploader("اختر ملف المخزون الجديد:", type=["xlsx", "csv", "tsv", "txt"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            sample = uploaded_file.read(2048).decode('utf-8', errors='ignore')
            uploaded_file.seek(0)
            sep = ';' if ';' in sample and sample.count(';') > sample.count(',') else ','
            df = pd.read_csv(uploaded_file, sep=sep)
        elif uploaded_file.name.endswith('.tsv') or uploaded_file.name.endswith('.txt'):
            df = pd.read_csv(uploaded_file, sep='\t')
        else:
            df = pd.read_excel(uploaded_file, engine='calamine')
            
        df.columns = [str(col).strip().lower() for col in df.columns]
        required_cols = ['id', 'name', 'balance', 'cost', 'price', 'expiry', 'min_balance']
        
        if all(col in df.columns for col in required_cols):
            new_inventory = {}
            for _, row in df.iterrows():
                p_id = str(row['id']).strip() if pd.notna(row['id']) else ""
                if not p_id or p_id.lower() == 'nan':
                    continue
                p_name = str(row['name']).strip() if pd.notna(row['name']) else "منتج بدون اسم"
                
                try:
                    balance_val = int(float(row['balance'])) if pd.notna(row['balance']) and str(row['balance']).strip() != '' else 0
                except:
                    balance_val = 0
                try:
                    cost_val = float(row['cost']) if pd.notna(row['cost']) and str(row['cost']).strip() != '' else 0.0
                except:
                    cost_val = 0.0
                try:
                    price_val = float(row['price']) if pd.notna(row['price']) and str(row['price']).strip() != '' else 0.0
                except:
                    price_val = 0.0
                try:
                    min_bal_val = int(float(row['min_balance'])) if pd.notna(row['min_balance']) and str(row['min_balance']).strip() != '' else 100
                except:
                    min_bal_val = 100
                    
                expiry_val = str(row['expiry']).strip() if pd.notna(row['expiry']) and str(row['expiry']).strip() != '' else "غير محدد"
                
                new_inventory[p_id] = {
                    "name": p_name, "balance": balance_val, "expiry": expiry_val,
                    "cost": cost_val, "price": price_val, "min_balance": min_bal_val
                }
            
            # التحديث الفوري المباشر للذاكرة دون أزرار خارجية تسبب فقدان الملف
            if new_inventory:
                st.session_state["inventory"] = new_inventory
                st.sidebar.success("✅ تم تحديث ونشر المخزون الجديد في الذاكرة بنجاح!")
        else:
            st.sidebar.error("❌ عذراً، الملف المرفوع لا يحتوي على الأعمدة الصحيحة في السطر الأول. يرجى التأكد من المسميات الإنجليزية.")
    except Exception as e:
        st.sidebar.error(f"خطأ أثناء معالجة بيانات الملف: {str(e)}")

st.sidebar.subheader("➕ إضافة منتج يدوياً")
with st.sidebar.form("add_new_product_form", clear_on_submit=True):
    p_id = st.text_input("كود المنتج (P039):").strip()
    p_name = st.text_input("اسم المنتج / السهم:").strip()
    p_balance = st.number_input("الرصيد:", min_value=0, value=0, step=1)
    p_cost = st.number_input("التكلفة:", min_value=0.0, value=0.0)
