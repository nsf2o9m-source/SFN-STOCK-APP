import streamlit as st
import pypdf
from pypdf import PdfReader
import json
import os
import pandas as pd
from datetime import datetime
import re

# 1. إعدادات الصفحة
st.set_page_config(page_title="نظام المستودعات الذكي", page_icon="📦", layout="centered")

DATA_FILE = "inventory_web.json"
INVOICES_FILE = "invoices_web.json"
ADMIN_PASSWORD = "123"  # الباسورد الخاص بك كمدير

default_inventory = {
    "1": {"name": "UGC COLLAGEN 10 SACHETS", "balance": 150, "expiry": "2027/12"},
    "2": {"name": "VITAMIN C 1000MG", "balance": 80, "expiry": "2027/05"},
    "3": {"name": "OMEGA 3 FISH OIL", "balance": 200, "expiry": "2028/01"}
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return default_inventory
    return default_inventory

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_invoices():
    if os.path.exists(INVOICES_FILE):
        with open(INVOICES_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def save_invoices(data):
    with open(INVOICES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

inventory = load_data()
invoices = load_invoices()

# دالة قراءة الـ PDF
def extract_data_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    
    full_text_upper = full_text.upper()
    extracted_actions = []
    
    for key, prod in inventory.items():
        prod_keyword = prod['name'].upper()
        if prod_keyword in full_text_upper:
            pattern = rf"(?:{re.escape(prod_keyword)}.*?(\d+)|(\d+).*?{re.escape(prod_keyword)})"
            match = re.search(pattern, full_text_upper)
            if match:
                amount = int(match.group(1) or match.group(2))
                extracted_actions.append({"key": key, "name": prod['name'], "amount": amount})
                
    return extracted_actions

# --- الشغل العالي: القائمة الجانبية لتحديد المستخدم ---
st.sidebar.markdown("## 🔐 تسجيل الدخول")
user_role = st.sidebar.radio("اختر نوع المستخدم:", ["👤 موظف (عرض فقط)", "👑 مدير النظام (صلاحيات كاملة)"])

is_admin = False
if user_role == "👑 مدير النظام (صلاحيات كاملة)":
    password_input = st.sidebar.text_input("أدخل الرقم السري للمدير:", type="password")
    if password_input == ADMIN_PASSWORD:
        st.sidebar.success("🔓 تم تفعيل صلاحيات المدير!")
        is_admin = True
    elif password_input != "":
        st.sidebar.error("❌ الرقم السري غير صحيح")

# رأس الصفحة
st.markdown("<h1 style='text-align: center; color: #1f538d;'>🧙‍♂️ نظام المخازن الذكي وقارئ الـ PDF</h1>", unsafe_allow_html=True)
st.write("---")

# حساب وعرض الإحصائيات
total_types = len(inventory)
total_items = sum(prod['balance'] for prod in inventory.values())
low_stock_alerts = sum(1 for prod in inventory.values() if prod['balance'] < 100)

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1: st.metric(label="📦 أنواع المنتجات", value=total_types)
with col_m2: st.metric(label="🔢 إجمالي القطع", value=total_items)
with col_m3: st.metric(label="⚠️ منتجات منخفضة", value=low_stock_alerts, delta="- انتباه" if low_stock_alerts > 0 else None, delta_color="inverse")

st.write("---")

# عرض جدول الجرد للجميع
st.markdown("### 📋 جدول جرد المخزون الفعلي")
table_data = []
for key, prod in inventory.items():
    bal = prod['balance']
    status_text = "❌ نفذت الكمية!" if bal == 0 else ("⚠️ رصيد منخفض" if bal < 100 else "✅ آمن ومستقر")
    table_data.append({"كود المنتج": key, "إسم المنتج التجاري": prod['name'], "تاريخ الصلاحية": prod['expiry'], "الرصيد الحالي": bal, "حالة الرصيد": status_text})

st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
st.write("---")

# --- التحكم في الصلاحيات بناءً على المستخدم ---
if is_admin:
    st.markdown("### 🛠️ لوحة التحكم والإدارة (خاصة بالمدير)")
    tab1, tab2, tab3, tab4 = st.tabs(["🤖 قارئ المستندات (PDF)", "🧾 إصدار فاتورة يدوية", "⚙️ حركات المخزن السريعة", "➕ تسجيل منتج جديد"])
    
    with tab1:
        st.markdown("#### 📂 معالجة فواتير وبوالص شحن PDF تلقائياً")
        uploaded_file = st.file_uploader("قم برفع ملف الفاتورة أو البوليصة (PDF):", type="pdf")
        doc_mode = st.radio("نوع المستند المرفوع:", ["مبيعات / بوليصة شحن (خصم من المخزن)", "فاتورة شراء / استلامات (إضافة للمخزن)"])
        
        if uploaded_file is not None and st.button("⚡ معالجة ملف PDF وتحديث المخزن فوراً", use_container_width=True):
            actions = extract_data_from_pdf(uploaded_file)
            if not actions:
                st.warning("⚠️ لم يتم العثور على منتجات مطابقة داخل ملف الـ PDF.")
            else:
                success_count = 0
                for act in actions:
                    key = act['key']
                    amt = act['amount']
                    if "خصم" in doc_mode:
                        if inventory[key]['balance'] >= amt:
                            inventory[key]['balance'] -= amt
                            st.write(f"🔴 تم خصم **{amt}** قطعة من [{act['name']}]")
                            success_count += 1
                        else: st.error(f"❌ الرصيد لا يكفي لخصم {amt} من [{act['name']}]")
                    else:
                        inventory[key]['balance'] += amt
                        st.write(f"🟢 تم إضافة **{amt}** قطعة إلى [{act['name']}]")
                        success_count += 1
                
                if success_count > 0:
                    save_data(inventory)
                    invoices.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "customer": f"مستند PDF مرفوع", "product": f"تحديث تلقائي لعدد {success_count} منتجات", "amount": "-"})
                    save_invoices(invoices)
                    st.success("🎉 تم تحديث المخزن أونلاين بناءً على ملف الـ PDF بنجاح!")
                    st.rerun()

    with tab2:
        st.markdown("#### 📄 إنشاء فاتورة مبيعات يدوية")
        inv_customer = st.text_input("إسم العميل أو الصيدلية:")
        inv_prod_id = st.selectbox("اختر المنتج المباع:", list(inventory.keys()), format_func=lambda x: f"كود [{x}] - {inventory[x]['name']}", key="inv_prod")
        inv_amount = st.number_input("الكمية المباعة بالفاتورة:", min_value=1, value=1, step=1)
        if st.button("🚀 اعتماد الفاتورة اليدوية وخصم الكمية", use_container_width=True):
            if not inv_customer: st.error("❌ يجب كتابة اسم العميل.")
            elif inventory[inv_prod_id]['balance'] < inv_amount: st.error("❌ الرصيد لا يكفي!")
            else:
                inventory[inv_prod_id]['balance'] -= inv_amount
                save_data(inventory)
                invoices.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "customer": inv_customer, "product": inventory[inv_prod_id]['name'], "amount": inv_amount})
                save_invoices(invoices)
                st.success("🎉 تم حفظ الفاتورة أونلاين!")
                st.rerun()

    with tab3:
        st.markdown("#### 🔄 حركات السحب والتوريد اليدوي السريع")
        prod_id = st.selectbox("اختر المنتج المستهدف:", list(inventory.keys()), format_func=lambda x: f"كود [{x}] - {inventory[x]['name']}", key="action_prod")
        amount = st.number_input("الكمية المطلوبة للحركة:", min_value=1, value=1, step=1)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔴 خصم سريع -", use_container_width=True):
                if inventory[prod_id]['balance'] < amount: st.error("❌ الرصيد لا يكفي!")
                else: inventory[prod_id]['balance'] -= amount; save_data(inventory); st.success("✅ تم الخصم!"); st.rerun()
        with c2:
            if st.button("🟢 إضافة سريعة +", use_container_width=True):
                inventory[prod_id]['balance'] += amount; save_data(inventory); st.success("✅ تم التوريد!"); st.rerun()

    with tab4:
        st.markdown("#### 📝 تسجيل منتج جديد في المخزن")
        new_id = st.text_input("كود المنتج الجديد:")
        new_name = st.text_input("إسم المنتج التجاري:")
        new_balance = st.number_input("رصيد البداية الافتتاحي:", min_value=0, value=0, step=1)
        new_expiry = st.text_input("تاريخ الصلاحية:")
        if st.button("💾 حفظ المنتج الجديد رسمياً", use_container_width=True):
            if not new_id or not new_name: st.error("❌ يجب كتابة الكود والإسم!")
            elif new_id in inventory: st.error("❌ هذا الكود مسجل مسبقاً!")
            else:
                inventory[new_id] = {"name": new_name, "balance": new_balance, "expiry": new_expiry if new_expiry else "غير محدد"}
                save_data(inventory)
                st.success(f"🎉 تم حفظ وإدراج [{new_name}] بالجدول الرئيسي!"); st.rerun()

    if invoices:
        st.markdown("##### 📜 سجل الفواتير والعمليات الأخيرة")
        st.dataframe(pd.DataFrame(invoices)[::-1], use_container_width=True, hide_index=True)

else:
    st.markdown("<p style='text-align: center; color: gray; font-style: italic;'>ℹ️ أنت تتصفح النظام بحساب 'موظف'. لرؤية أزرار التعديل، الفواتير، وقارئ الـ PDF، يرجى تسجيل الدخول كمدير من القائمة الجانبية.</p>", unsafe_allow_html=True)
