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

def get_setting(name, default=""):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return os.getenv(name, value)

ADMIN_PASSWORD = str(get_setting("ADMIN_PASSWORD", "Sfn2026")).strip()

# 📦 القائمة الثابتة والدائمة لمنتجاتك الـ 38 (مستحيل تختفي بعد الآن)
if "master_inventory" not in st.session_state:
    st.session_state["master_inventory"] = {
        "P001": {"name": "ASHWAGANDHA MATEX 60 TAB", "balance": 2371, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P002": {"name": "BLACK SEED OIL 1000MG 60CAP", "balance": 69, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P003": {"name": "GOFIT CHARCOAL 30 CAP", "balance": 4984, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P004": {"name": "GOFIT CURCUMIN 1000 MG 60 TAB", "balance": 4584, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P005": {"name": "ivy syrp", "balance": 831, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P006": {"name": "JOINT PLANET 90 TAB", "balance": 653, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P007": {"name": "MATOTHREX COLLAGEN 120 TAB", "balance": 0, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P008": {"name": "UGC MATEX MELATONIN 30 TAB", "balance": 1329, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P009": {"name": "ORA SMOOTH BLACKSEED SPRAY 60 ML", "balance": 1010, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P010": {"name": "ORA SMOOTH CLOVE&CINNAMON SPRAY", "balance": 2550, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P011": {"name": "ORA SMOOTH MINT SPRAY 60 ML", "balance": 7948, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P012": {"name": "ORA SMOOTH ORANGE SPRAY 60 ML", "balance": 8152, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P013": {"name": "RELAX-FREE MASSAGE CREAM 100 GM", "balance": 14, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P014": {"name": "SYMPHONY COLLAGEN FACE SERUM", "balance": 535, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P015": {"name": "SYMPHONY HAIR SERUM 5AMP 1M", "balance": 3664, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P016": {"name": "SYMPHONY HYPERTONIC SPRAY", "balance": 3408, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P017": {"name": "Symphony massage cream Colocynth Oil", "balance": 5171, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P018": {"name": "Symphony massage cream black seed oil", "balance": 6177, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P019": {"name": "SYMPHONY CREAM Apple Cider Vinegar", "balance": 7192, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P020": {"name": "SYMPHONY MASSAGE CREAM OSTRICH FAT", "balance": 4318, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P021": {"name": "SYMPHONY SHAMPO 200 ML", "balance": 368, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P022": {"name": "SYMPHONY HAIR MASK 200 GM", "balance": 10, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P023": {"name": "U.G.C D3 4000 I.U. 30 TAB", "balance": 0, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P024": {"name": "U.G.C MAN 30 TAB", "balance": 162, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P025": {"name": "d3+k2", "balance": 102, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P026": {"name": "U.G.C WOMAN 30 TAB", "balance": 37, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P027": {"name": "UGC COLLAGEN 10 SACHETS", "balance": 3038, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P028": {"name": "UGC COLLAGEN 30 SACHETS", "balance": 755, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P029": {"name": "comblix", "balance": 57, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P030": {"name": "VBLS MAGNI B6 90 TAB", "balance": 99, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P031": {"name": "VBLS SLIMMING 30 TAB", "balance": 1912, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P032": {"name": "VBLS VITAMIN-C 1000MG 30 TAB", "balance": 78, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P033": {"name": "omega3  60cap", "balance": 236, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P034": {"name": "cogni draw", "balance": 1902, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P035": {"name": "gelon 120", "balance": 430, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P036": {"name": "gelon60", "balance": 193, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P037": {"name": "rozichika", "balance": 64, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100},
        "P038": {"name": "shartic", "balance": 1376, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100}
    }

# -------------------- نظام الصلاحيات البسيط --------------------
st.sidebar.title("🔐 صلاحيات النظام")
user_role = st.sidebar.selectbox("نوع الحساب الحالي:", ["موظف (مشاهدة فقط)", "مدير النظام (Admin)"])

is_admin = False
if user_role == "مدير النظام (Admin)":
    password_input = st.sidebar.text_input("أدخل كلمة مرور الإدارة لوضع التعديل:", type="password")
    if password_input == ADMIN_PASSWORD:
        is_admin = True
        st.sidebar.success("🔑 تم تفعيل صلاحيات المدير!")
    elif password_input != "":
        st.sidebar.error("❌ كلمة المرور غير صحيحة!")
else:
    st.sidebar.info("ℹ️ وضع المشاهدة نشط (موظف). الخيارات مقفلة.")

# -------------------- لوحة التحديث اليومي السريع --------------------
if is_admin:
    st.write("## ⚡ التحديث اليومي السريع للمخزون")
    with st.expander("🛠️ اضغط هنا لزيادة أو إنقاص كمية أي منتج بلمحة بصر", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            product_options = {k: f"{k} - {v['name']} (الحالي: {v['balance']})" for k, v in st.session_state["master_inventory"].items()}
            selected_prod_key = st.selectbox("اختر المنتج المراد تعديله:", options=list(product_options.keys()), format_func=lambda x: product_options[x])
        with col2:
            action = st.radio("نوع العملية اليومية:", ["➕ زيادة (وارد)", "➖ نقصان (منصرف)"])
        with col3:
            amount = st.number_input("الكمية المراد تعديلها:", min_value=1, value=1, step=1)
        with col4:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("🚀 تحديث الكمية الآن", type="primary", use_container_width=True):
                current_balance = st.session_state["master_inventory"][selected_prod_key]["balance"]
                if action == "➕ زيادة (وارد)":
                    st.session_state["master_inventory"][selected_prod_key]["balance"] = current_balance + amount
                    st.success("✅ تم تحديث المخزون بنجاح!")
                else:
                    if current_balance >= amount:
                        st.session_state["master_inventory"][selected_prod_key]["balance"] = current_balance - amount
                        st.success("✅ تم تحديث المخزون بنجاح!")
                    else:
                        st.error("❌ المخزون الحالي لا يكفي!")
                st.rerun()

    # -------------------- واجهة تحكم المدير الجانبية السهلة --------------------
    st.sidebar.markdown("---")
    st.sidebar.title("⚙️ لوحة الإدارة والتحكم")
    
    st.sidebar.subheader("➕ إضافة منتج جديد تماماً")
    p_id = st.sidebar.text_input("كود المنتج الجديد (مثل P039):").strip()
    p_name = st.sidebar.text_input("اسم المنتج الجديد:").strip()
    p_balance = st.sidebar.number_input("الرصيد الابتدائي:", min_value=0, value=0, step=1)
    
    if st.sidebar.button("حفظ المنتج الجديد"):
        if p_id and p_name:
            if p_id not in st.session_state["master_inventory"]:
                st.session_state["master_inventory"][p_id] = {
                    "name": p_name, "balance": p_balance, "expiry": "غير محدد", "cost": 0.0, "price": 0.0, "min_balance": 100
                }
                st.sidebar.success(f"تم إضافة {p_name} بنجاح!")
                st.rerun()
            else:
                st.sidebar.error("هذا الكود مستخدم بالفعل!")
        else:
            st.sidebar.error("يرجى إدخال الكود والاسم!")

# -------------------- عرض واجهة المستخدم الأساسية الهيكلية المستقرة --------------------
st.write("---")
st.write("### 📦 المخزون الحالي في النظام أونلاين:")

# قراءة الجدول بشكل مباشر ومستقل تماماً لضمان عرضه في كل الأحوال
df_inv = pd.DataFrame.from_dict(st.session_state["master_inventory"], orient='index')

if is_admin:
    st.info("💡 يمكنك أيضاً تعديل التفاصيل الأخرى مباشرة من الجدول بالأسفل ثم اضغط حفظ:")
    edited_df = st.data_editor(df_inv, use_container_width=True)
    if st.button("💾 حفظ تعديلات الجدول الكلية"):
        st.session_state["master_inventory"] = edited_df.to_dict(orient='index')
