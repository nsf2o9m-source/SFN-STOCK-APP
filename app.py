import streamlit as st
import json
import os
import pandas as pd

# 1. إعدادات الصفحة والمظهر الاحترافي
st.set_page_config(page_title="نظام إدارة المستودعات الذكي", page_icon="📦", layout="centered")

DATA_FILE = "inventory_web.json"
default_inventory = {
    "1": {"name": "UGC COLLAGEN 10 SACHETS", "balance": 150, "expiry": "2027/12"},
    "2": {"name": "VITAMIN C 1000MG", "balance": 80, "expiry": "2027/05"},
    "3": {"name": "OMEGA 3 FISH OIL", "balance": 200, "expiry": "2028/01"}
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for key, prod in data.items():
                    if "expiry" not in prod:
                        prod["expiry"] = "غير محدد"
                return data
            except:
                return default_inventory
    return default_inventory

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

inventory = load_data()

# 2. رأس الصفحة وتنسيق العنوان
st.markdown("<h1 style='text-align: center; color: #1f538d; font-family: Arial;'>📊 لوحة التحكم الذكية ونظام إدارة المخزون</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>نظام محاسبي متكامل لمتابعة الأرصدة وتواريخ الصلاحية وتنبيهات النواقص</p>", unsafe_allow_html=True)
st.write("---")

# 3. الشغل العالي: حساب الإحصائيات لعرض البطاقات الذكية
total_types = len(inventory)
total_items = sum(prod['balance'] for prod in inventory.values())
low_stock_alerts = sum(1 for prod in inventory.values() if prod['balance'] < 100)

# عرض البطاقات الإحصائية (Metrics) في صف واحد
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric(label="📦 إجمالي أنواع المنتجات", value=total_types)
with col_m2:
    st.metric(label="🔢 إجمالي القطع بالمخزن", value=total_items)
with col_m3:
    # إذا كان هناك نواقص يظهر الرقم بلون تنبيهي
    st.metric(label="⚠️ منتجات تحتاج توريد", value=low_stock_alerts, delta="- انتباه" if low_stock_alerts > 0 else None, delta_color="inverse")

st.write("---")

# 4. بناء الجدول الاحترافي المنظم
st.markdown("### 📋 جدول جرد المخزون الفعلي")

# تحويل البيانات إلى جدول منظم (Dataframe) لعرضه بشكل احترافي
table_data = []
for key, prod in inventory.items():
    bal = prod['balance']
    if bal == 0:
        status_text = "❌ نفذت الكمية!"
    elif bal < 100:
        status_text = "⚠️ رصيد منخفض"
    else:
        status_text = "✅ آمن ومستقر"
        
    table_data.append({
        "كود المنتج": key,
        "إسم المنتج التجاري": prod['name'],
        "تاريخ الصلاحية": prod['expiry'],
        "الرصيد الحالي": bal,
        "حالة الرصيد": status_text
    })

df = pd.DataFrame(table_data)
# عرض الجدول بشكل تفاعلي جميل ومناسب للشاشات
st.dataframe(df, use_container_width=True, hide_index=True)

st.write("---")

# 5. التبويبات المنظمة لإدارة الجرد والعمليات
tab1, tab2 = st.tabs(["⚙️ إدارة حركات المخزن (بيع / توريد)", "➕ تسجيل وإدخال منتج جديد"])

# تبويب العمليات
with tab1:
    st.markdown("#### 🔄 تسجيل حركة سحب أو إضافة كمية")
    prod_id = st.selectbox("اختر المنتج المستهدف:", list(inventory.keys()), format_func=lambda x: f"كود [{x}] - {inventory[x]['name']}", key="action_prod")
    amount = st.number_input("الكمية المطلوبة للحركة:", min_value=1, value=1, step=1, key="action_amount")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔴 تسجيل عملية خصم (بيع)", use_container_width=True):
            if inventory[prod_id]['balance'] >= amount:
                inventory[prod_id]['balance'] -= amount
                save_data(inventory)
                st.success(f"✅ تم خصم {amount} قطعة بنجاح من [{inventory[prod_id]['name']}]")
                st.rerun()
            else:
                st.error("❌ خطأ: الرصيد الحالي بالمستودع لا يكفي لتغطية الكمية المطلوبة!")
                
    with c2:
        if st.button("🟢 تسجيل عملية إضافة (توريد)", use_container_width=True):
            inventory[prod_id]['balance'] += amount
            save_data(inventory)
            st.success(f"✅ تم إضافة {amount} قطعة بنجاح إلى [{inventory[prod_id]['name']}]")
            st.rerun()

# تبويب منتج جديد
with tab2:
    st.markdown("#### 📝 إدخال منتج جديد تماماً في النظام")
    new_id = st.text_input("كود المنتج الجديد (رقم غير مكرر):", placeholder="مثال: 4")
    new_name = st.text_input("إسم المنتج بالكامل باللغة الإنجليزية:", placeholder="مثال: PANADOL EXTRA")
    new_balance = st.number_input("رصيد البداية الافتتاحي بالمخزن:", min_value=0, value=0, step=1)
    new_expiry = st.text_input("تاريخ الصلاحية المسجل:", placeholder="مثال: 2027/12")
    
    if st.button("💾 حفظ المنتج الجديد رسمياً بالنظام", use_container_width=True):
        if not new_id or not new_name:
            st.error("❌ خطأ: يجب كتابة الكود وإسم المنتج لإتمام الحفظ!")
        elif new_id in inventory:
            st.error("❌ خطأ: هذا الكود مسجل مسبقاً لمنتج آخر بالجدول!")
        else:
            expiry_text = new_expiry if new_expiry else "غير محدد"
            inventory[new_id] = {"name": new_name, "balance": new_balance, "expiry": expiry_text}
            save_data(inventory)
            st.success(f"🎉 مبروك! تم تسجيل وحفظ [{new_name}] وإدراجه بالجدول الرئيسي!")
            st.rerun()

