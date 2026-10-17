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

# 🔐 كلمة مرور المدير الافتراضية هي Sfn2026 
# (يمكنك كتابة أي كلمة سر تريدها بين العلامتين بدلاً منها مباشرة داخل الكود هنا)
ADMIN_PASSWORD = str(get_setting("ADMIN_PASSWORD", "Sfn2026")).strip()

# قاعدة البيانات المحدثة للمنتجات الـ 38
NEW_MUKHZON = {
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

if "inventory" not in st.session_state:
    st.session_state["inventory"] = NEW_MUKHZON

# -------------------- نظام البوابة وصلاحيات الدخول --------------------
st.sidebar.title("🔐 صلاحيات النظام")
user_role = st.sidebar.selectbox("نوع الحساب الحالي:", ["موظف (مشاهدة فقط)", "مدير النظام (Admin)"])

is_admin = False
if user_role == "مدير النظام (Admin)":
    password_input = st.sidebar.text_input("أدخل كلمة مرور الإدارة لوضع التعديل:", type="password")
    if password_input == ADMIN_PASSWORD:
        is_admin = True
        st.sidebar.success("🔑 تم تفعيل صلاحيات المدير التعديلية!")
    elif password_input != "":
        st.sidebar.error("❌ كلمة المرور غير صحيحة!")
else:
    st.sidebar.info("ℹ️ وضع المشاهدة نشط (موظف). الخيارات مقفلة.")

# -------------------- واجهة تحكم المدير (تظهر فقط بعد كتابة كلمة المرور الصحيحة) --------------------
if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.title("⚙️ لوحة الإدارة والتحكم")
    
    st.sidebar.subheader("🚨 تصفير المستودع")
    confirm_delete = st.sidebar.checkbox("أنا متأكد من رغبتي في مسح كل المخزون الحالي")
    if st.sidebar.button("🗑️ مسح كافة المنتجات والبيانات", disabled=not confirm_delete):
        st.session_state["inventory"] = {}
        st.sidebar.success("تم تصفير المخزون!")
        st.rerun()

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
                st.sidebar.success(f"تم إضافة {p_name}!")
                st.rerun()

# -------------------- عرض واجهة المستخدم الأساسية --------------------
st.write("### 📦 المخزون الحالي في النظام أونلاين:")
if st.session_state["inventory"]:
    df_inv = pd.DataFrame.from_dict(st.session_state["inventory"], orient='index')
    
    # للمدير: واجهة تعديل حية تفاعلية لحفظ وتغيير الأرقام
    if is_admin:
        st.info("💡 يمكنك تعديل كميات أو أسعار المنتجات مباشرة من داخل الجدول بالأسفل ثم اضغط حفظ:")
        edited_df = st.data_editor(df_inv, use_container_width=True)
        if st.button("💾 حفظ تعديلات الجدول الحالية"):
            st.session_state["inventory"] = edited_df.to_dict(orient='index')
            st.success("✅ تم حفظ وتثبيت تعديلاتك الجديدة بنجاح!")
            st.rerun()
    # للموظف: جدول قراءة فقط ثابت غير قابل للنقر والتعديل
    else:
        st.dataframe(df_inv, use_container_width=True)
else:
    st.info("المخزون فارغ حالياً.")
