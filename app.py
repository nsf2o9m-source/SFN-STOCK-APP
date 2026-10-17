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

DATA_FILE = "inventory_web.json"
INVOICES_FILE = "invoices_web.json"
MOVEMENTS_FILE = "movements_web.json"
LOW_STOCK_DEFAULT = 100

DEFAULT_INVENTORY = {
    "P001": {"name": "ASHWAGANDHA MATEX 60 TAB", "balance": 2371, "expiry": "غير محدد", "cost": 0, "price": 0, "min_balance": 100}
}

# -------------------- نظام الحفظ المحلي الذكي والدائم --------------------
def load_local_data(file_name, default_value):
    # إذا كان الملف موجوداً مسبقاً على السيرفر، نقوم بالقراءة منه فوراً
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                content = json.load(f)
                # نضمن ألا يعود للنظام القديم طالما تم تصفيره أو تعديله
                return content
        except Exception:
            return default_value
    
    # إذا لم يكن الملف موجوداً (أول تشغيل)، ننشئه بالبيانات الافتراضية
    save_local_data(file_name, default_value)
    return default_value

def save_local_data(file_name, data):
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# تهيئة البيانات في الجلسة بشكل مستقر لا يضيع مع التحديث
if "inventory" not in st.session_state:
    st.session_state["inventory"] = load_local_data(DATA_FILE, DEFAULT_INVENTORY)
if "invoices" not in st.session_state:
    st.session_state["invoices"] = load_local_data(INVOICES_FILE, [])
if "movements" not in st.session_state:
    st.session_state["movements"] = load_local_data(MOVEMENTS_FILE, [])

# -------------------- واجهة لوحة تحكم المخزون --------------------
st.sidebar.title("⚙️ لوحة التحكم والإدارة")

st.sidebar.subheader("🚨 تصفير المستودع")
confirm_delete = st.sidebar.checkbox("أنا متأكد من رغبتي في مسح كل المخزون الحالي")
if st.sidebar.button("🗑️ مسح كافة المنتجات والبيانات", disabled=not confirm_delete):
    st.session_state["inventory"] = {}
    st.session_state["invoices"] = []
    st.session_state["movements"] = []
    save_local_data(DATA_FILE, {})
    save_local_data(INVOICES_FILE, [])
    save_local_data(MOVEMENTS_FILE, [])
    st.sidebar.success("تم مسح المخزون بالكامل وتصفير الموقع!")
    st.rerun()

# ميزة رفع المخزون الجديد بالكامل عبر معالج الأزرار المباشر
st.sidebar.subheader("📤 رفع مخزون جديد بالكامل")
uploaded_file = st.sidebar.file_uploader("اختر ملف المخزون الجديد:", type=["xlsx", "csv", "tsv", "txt"])

if uploaded_file is not None:
    st.info("🔄 جاري قراءة وتحليل ملفك المرفوع حالياً... يرجى مراجعة زر الحفظ بالأسفل.")
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
            
            st.warning("⚠️ تم التعرف على ملفك بنجاح. اضغط على الزر بالأسفل لتحديث الموقع:")
            if st.button("💾 اضغط هنا لاعتماد وحفظ منتجات الملف الجديد أونلاين", type="primary"):
                st.session_state["inventory"] = new_inventory
                save_local_data(DATA_FILE, new_inventory)
                st.success("✅ تم تحديث ونشر المستودع الجديد بنجاح وثبات!")
                st.rerun()
        else:
            st.error("❌ عذراً، الملف المرفوع لا يحتوي على الأعمدة الصحيحة في السطر الأول. يرجى التأكد من المسميات الإنجليزية.")
    except Exception as e:
        st.error(f"خطأ أثناء معالجة بيانات الملف: {str(e)}")

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
            save_local_data(DATA_FILE, st.session_state["inventory"])
            st.sidebar.success(f"تم إضافة {p_name}!")
            st.rerun()

# -------------------- عرض المخزون الأساسي --------------------
st.write("### 📦 المخزون الحالي في النظام أونلاين:")
if st.session_state["inventory"]:
    df_inv = pd.DataFrame.from_dict(st.session_state["inventory"], orient='index')
    st.dataframe(df_inv, use_container_width=True)
else:
    st.info("المخزون فارغ حالياً. يمكنك تصفح الشريط الجانبي لرفع ملف منتجاتك الجديدة.")
