import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from pypdf import PdfReader
import re

# 1. إعدادات الصفحة والمظهر الاحترافي
st.set_page_config(page_title="نظام المستودعات الذكي بالذكاء الاصطناعي", page_icon="📦", layout="centered")

ADMIN_PASSWORD = "123" 
DATA_FILE = "inventory_web.json"
INVOICES_FILE = "invoices_web.json"

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

# دالة ذكية لقراءة الـ PDF واستخراج الكميات تلقائياً
def extract_data_from_pdf(pdf_file, mode):
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    
    full_text_upper = full_text.upper()
    extracted_actions = []
    
    # البحث الذكي عن المنتجات والكميات المجاورة لها باستخدام العبارات النمطية (Regex)
    for key, prod in inventory.items():
        prod_keyword = prod['name'].split()[1] if len(prod['name'].split()) > 1 else prod['name']
        if prod_keyword in full_text_upper:
            # البحث عن أرقام قريبة من اسم المنتج في النص
            pattern = rf"(?:{prod_keyword}.*?(\d+)|(\d+).*?{prod_keyword})"
            match = re.search(pattern, full_text_upper)
            if match:
                amount = int(match.group(1) or match.group(2))
                extracted_actions.append({"key": key, "name": prod['name'], "amount": amount})
                
    return extracted_actions, full_text

# 2. رأس الصفحة وتنسيق العنوان
st.markdown("<h1 style='text-align: center; color: #1f538d; font-family: Arial;'>🧙‍♂️ نظام المخازن الساحر وقارئ المستندات</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>ارفع فواتير PDF وبوالص الشحن ليقوم النظام بخصمها وتوريدها تلقائياً</p>", unsafe_allow_html=True)
st.write("---")

# 3. عرض بطاقات الإحصائيات
total_types = len(inventory)
total_items = sum(prod['balance'] for prod in inventory.values())
low_stock_alerts = sum(1 for prod in inventory.values() if prod['balance'] < 100)

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1: st.metric(label="📦 أنواع المنتجات", value=total_types)
with col_m2: st.metric(label="🔢 إجمالي القطع", value=total_items)
with col_m3: st.metric(label="⚠️ منتجات منخفضة", value=low_stock_alerts, delta="- انتباه" if low_stock_alerts > 0 else None, delta_color="inverse")

st.write("---")

# 4. بناء الجدول الاحترافي المنظم للجميع
st.markdown("### 📋 جدول جرد المخزون الفعلي أونلاين")
table_data = []
for key, prod in inventory.items():
    bal = prod['balance']
    status_text = "❌ نفذت الكمية!" if bal == 0 else ("⚠️ رصيد منخفض" if bal < 100 else "✅ آمن ومستقر")
    table_data.append({"كود المنتج": key, "إسم المنتج التجاري": prod['name'], "تاريخ الصلاحية": prod['expiry'], "الرصيد الحالي": bal, "حالة الرصيد": status_text})

st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
st.write("---")

# 5. التبويبات الاحترافية (إضافة تبويب قراءة المستندات الذكي)
tab1, tab2, tab3, tab4 = st.tabs(["🤖 قارئ الفواتير و البوالص (PDF)", "🧾 إصدار فاتورة يدوية", "⚙️ حركات المخزن السريعة", "➕ تسجيل منتج جديد"])

# التبويب الأول والأهم: قارئ مستندات PDF الذكي
with tab1:
    st.markdown("#### 📂 معالجة فواتير وبوالص شحن PDF تلقائياً")
    uploaded_file = st.file_uploader("قم برفع ملف الفاتورة أو البوليصة (صيغة PDF):", type="pdf")
    doc_mode = st.radio("نوع المستند المرفوع:", ["مبيعات / بوليصة شحن (خصم من المخزن)", "فاتورة شراء / استلامات (إضافة للمخزن)"])
    doc_password = st.text_input("أدخل الرقم السري لتأكيد المعالجة التلقائية:", type="password", key="doc_pass")
    
    if uploaded_file is not None and st.button("⚡ معالجة الملف وتحديث الأرصدة فوراً", use_container_width=True):
        if doc_password != ADMIN_PASSWORD:
            st.error("❌ خطأ: الرقم السري غير صحيح!")
        else:
            actions, text_found = extract_data_from_pdf(uploaded_file, doc_mode)
            if not actions:
                st.warning("⚠️ تم قراءة الملف بنجاح، ولكن لم يتم العثور على أسماء منتجات مطابقة داخل النص.")
            else:
                st.markdown("##### 🔍 المنتجات التي تم رصدها واستخراجها من الملف:")
                success_count = 0
                for act in actions:
                    key = act['key']
                    amt = act['amount']
                    if "خصم" in doc_mode:
                        if inventory[key]['balance'] >= amt:
                            inventory[key]['balance'] -= amt
                            st.write(f"🔴 تم خصم **{amt}** قطعة من [{act['name']}]")
                            success_count += 1
                        else:
                            st.error(f"❌ تعذر خصم {amt} من [{act['name']}] لأن الرصيد لا يكفي!")
                    else:
                        inventory[key]['balance'] += amt
                        st.write(f"🟢 تم إضافة **{amt}** قطعة إلى [{act['name']}]")
                        success_count += 1
                
                if success_count > 0:
                    save_data(inventory)
                    # تسجيل العملية في الأرشيف
                    new_invoice = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "customer": f"مستند مرفوع ({'شحن' if 'خصم' in doc_mode else 'توريد'})",
                        "product": f"تحديث تلقائي لعدد {success_count} منتجات",
                        "amount": "-"
                    }
                    invoices.append(new_invoice)
                    save_invoices(invoices)
                    st.success("🎉 تم تحديث قاعدة البيانات والمخزن أونلاين بناءً على ملف الـ PDF!")
                    st.rerun()

# التبويب الثاني: الفواتير اليدوية
with tab2:
    st.markdown("#### 📄 إنشاء فاتورة مبيعات يدوية")
    inv_customer = st.text_input("إسم العميل أو الصيدلية:", placeholder="مثال: صيدلية مصر")
    inv_prod_id = st.selectbox("اختر المنتج المباع:", list(inventory.keys()), format_func=lambda x: f"كود [{x}] - {inventory[x]['name']}", key="inv_prod")
    inv_amount = st.number_input("الكمية المباعة بالفاتورة:", min_value=1, value=1, step=1, key="inv_amount")
    inv_password = st.text_input("أدخل الرقم السري لاعتماد الفاتورة:", type="password", key="inv_pass")
    
    if st.button("🚀 اعتماد وحفظ الفاتورة اليدوية", use_container_width=True):
        if inv_password != ADMIN_PASSWORD: st.error("❌ رقم سري خاطئ!")
        elif not inv_customer: st.error("❌ يجب كتابة اسم العميل.")
        elif inventory[inv_prod_id]['balance'] < inv_amount: st.error("❌ الرصيد لا يكفي!")
        else:
            inventory[inv_prod_id]['balance'] -= inv_amount
            save_data(inventory)
            invoices.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "customer": inv_customer, "product": inventory[inv_prod_id]['name'], "amount": inv_amount})
            save_invoices(invoices)
            st.success("🎉 تم حفظ الفاتورة وخصم الكمية أونلاين!")
            st.rerun()

# التبويب الثالث: التعديل السريع المحمي
with tab3:
    st.markdown("#### 🔄 حركات السحب والتوريد اليدوي السريع")
    prod_id = st.selectbox("اختر المنتج المستهدف:", list(inventory.keys()), format_func=lambda x: f"كود [{x}] - {inventory[x]['name']}", key="action_prod")
    amount = st.number_input("الكمية المطلوبة للحركة:", min_value=1, value=1, step=1, key="action_amount")
    action_password = st.text_input("أدخل الرقم السري لتعديل الرصيد:", type="password", key="action_pass")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔴 خصم سريع -", use_container_width=True):
            if action_password != ADMIN_PASSWORD: st.error("❌ رقم سري خاطئ!")
            elif inventory[prod_id]['balance'] < amount: st.error("❌ الرصيد لا يكفي!")
            else: inventory[prod_id]['balance'] -= amount; save_data(inventory); st.success("✅ تم الخصم!"); st.rerun()
    with c2:
        if st.button("🟢 إضافة سريعة +", use_container_width=True):
            if action_password != ADMIN_PASSWORD: st.error("❌ رقم سري خاطئ!")
            else: inventory[prod_id]['balance'] += amount; save_data(inventory); st.success("✅ تم التوريد!"); st.rerun()

# تبويب تسجيل منتج جديد المحمي
with tab4:
    st.markdown("#### 📝 تسجيل منتج جديد في المخزن")
    new_id = st.text_input("كود المنتج الجديد:", placeholder="مثال: 4")
    new_name = st.text_input("إسم المنتج التجاري:", placeholder="مثال: PANADOL EXTRA")
    new_balance = st.number_input("رصيد البداية الافتتاحي:", min_value=0, value=0, step=1)
    new_expiry = st.text_input("تاريخ الصلاحية:", placeholder="مثال: 2027/12")
    new_password = st.text_input("أدخل الرقم السري لحفظ المنتج الجديد:", type="password", key="new_pass")
    if st.button("💾 حفظ المنتج الجديد رسمياً", use_container_width=True):
        if new_password != ADMIN_PASSWORD: st.error("❌ رقم سري خاطئ!")
        elif not new_id or not new_name: st.error("❌ يجب كتابة الكود والإسم!")
        elif new_id in inventory: st.error("❌ هذا الكود مسجل مسبقاً!")
        else:
            inventory[new_id] = {"name": new_name, "balance": new_balance, "expiry": new_expiry if new_expiry else "غير محدد"}
            save_data(inventory)
