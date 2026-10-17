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

# لا تضع كلمة مرور المدير داخل الكود. أضف ADMIN_PASSWORD إلى Streamlit Secrets.
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", ""))

DEFAULT_INVENTORY = {
    "1": {"name": "UGC COLLAGEN 10 SACHETS", "balance": 150, "expiry": "2027/12"},
    "2": {"name": "VITAMIN C 1000MG", "balance": 80, "expiry": "2027/05"},
    "3": {"name": "OMEGA 3 FISH OIL", "balance": 200, "expiry": "2028/01"},
}


def read_json(path, fallback):
    if not os.path.exists(path):
        return fallback.copy() if isinstance(fallback, dict) else list(fallback)
    try:
        with open(path, "r", encoding="utf-8") as file:
            value = json.load(file)
        return value if isinstance(value, type(fallback)) else fallback.copy()
    except (OSError, json.JSONDecodeError):
        st.warning(f"تعذر قراءة {path}. لم يتم استبدال الملف تلقائيًا حتى لا نفقد البيانات.")
        return fallback.copy() if isinstance(fallback, dict) else list(fallback)


def write_json(path, value):
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def load_inventory():
    data = read_json(DATA_FILE, DEFAULT_INVENTORY)
    # توافق مع البيانات القديمة والتحقق من الحقول الأساسية
    cleaned = {}
    for key, item in data.items():
        if not isinstance(item, dict):
            continue
        try:
            balance = max(0, int(item.get("balance", 0)))
        except (TypeError, ValueError):
            balance = 0
        cleaned[str(key)] = {
            "name": str(item.get("name", f"صنف {key}")),
            "balance": balance,
            "expiry": str(item.get("expiry", "غير محدد")),
            "cost": float(item.get("cost", 0) or 0),
            "price": float(item.get("price", 0) or 0),
            "min_balance": int(item.get("min_balance", LOW_STOCK_DEFAULT) or LOW_STOCK_DEFAULT),
        }
    return cleaned


def add_movement(product_id, product_name, movement_type, quantity, before, after, note=""):
    movements = read_json(MOVEMENTS_FILE, [])
    movements.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "product_id": str(product_id),
        "product": product_name,
        "type": movement_type,
        "quantity": int(quantity),
        "before": int(before),
        "after": int(after),
        "note": note,
        "user": "مدير النظام",
    })
    write_json(MOVEMENTS_FILE, movements)


def change_stock(product_id, quantity, movement_type, note=""):
    product = inventory[product_id]
    before = int(product["balance"])
    quantity = int(quantity)
    if movement_type in ("بيع", "خصم", "مرتجع شراء") and before < quantity:
        return False, "الرصيد الحالي لا يكفي لإتمام الحركة."
    if movement_type in ("بيع", "خصم", "مرتجع شراء"):
        after = before - quantity
    else:
        after = before + quantity
    product["balance"] = after
    write_json(DATA_FILE, inventory)
    add_movement(product_id, product["name"], movement_type, quantity, before, after, note)
    return True, "تم حفظ حركة المخزون بنجاح."


def extract_data_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        text = "\n".join((page.extract_text() or "") for page in reader.pages).upper()
    except Exception as exc:
        return [], f"تعذر قراءة ملف PDF: {exc}"
    actions = []
    for key, product in inventory.items():
        name = product["name"].upper().strip()
        if not name or name not in text:
            continue
        pattern = rf"(?:{re.escape(name)}.{{0,80}}?(\d+)|(\d+).{{0,80}}?{re.escape(name)})"
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            try:
                amount = int(match.group(1) or match.group(2))
                if amount > 0:
                    actions.append({"key": key, "name": product["name"], "amount": amount})
            except (TypeError, ValueError):
                continue
    return actions, None


inventory = load_inventory()
invoices = read_json(INVOICES_FILE, [])
movements = read_json(MOVEMENTS_FILE, [])

# -------------------- تنسيق الواجهة --------------------
st.markdown("""
<style>
html, body, [class*="css"] { font-family: "Arial", "Tahoma", sans-serif; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
.hero { padding: 1.4rem 1.6rem; border-radius: 16px;
        background: linear-gradient(120deg,#102a43,#176b87); color: white; margin-bottom: 1rem; }
.hero h1 { color: white; margin: 0; font-size: 2rem; }
.hero p { color: #e4f3f8; margin: .4rem 0 0 0; }
[data-testid="stMetric"] { background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,.18); padding: 14px; border-radius: 12px; }
.stButton button { border-radius: 9px; min-height: 2.6rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>📦 SFN | نظام إدارة المخزون</h1>
  <p>إدارة الأصناف، حركة المخزون، المبيعات والمشتريات من لوحة واحدة</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🔐 الدخول والصلاحيات")
    st.caption("تسجيل دخول المدير مطلوب لإجراء أي تعديل.")
    password_input = st.text_input("كلمة مرور المدير", type="password")
    is_admin = bool(ADMIN_PASSWORD) and password_input == ADMIN_PASSWORD
    if not ADMIN_PASSWORD:
        st.warning("لم يتم ضبط ADMIN_PASSWORD في إعدادات التطبيق؛ وضع الإدارة معطّل حتى ضبطه.")
    elif is_admin:
        st.success("تم تسجيل الدخول كمدير.")
    elif password_input:
        st.error("كلمة المرور غير صحيحة.")
    st.divider()
    low_limit = st.number_input("حد تنبيه نقص المخزون الافتراضي", min_value=0, value=LOW_STOCK_DEFAULT, step=5)
    st.caption("يمكن تخصيص حد التنبيه لكل صنف من صفحة الأصناف.")

# Normalize optional fields in memory
for product in inventory.values():
    product.setdefault("cost", 0.0)
    product.setdefault("price", 0.0)
    product.setdefault("min_balance", int(low_limit) if low_limit else LOW_STOCK_DEFAULT)

total_types = len(inventory)
total_units = sum(int(p["balance"]) for p in inventory.values())
low_products = [p for p in inventory.values() if int(p["balance"]) <= int(p.get("min_balance", low_limit))]
out_products = [p for p in inventory.values() if int(p["balance"]) == 0]
stock_cost_value = sum(float(p.get("cost", 0)) * int(p["balance"]) for p in inventory.values())

m1, m2, m3, m4 = st.columns(4)
m1.metric("عدد الأصناف", f"{total_types:,}")
m2.metric("إجمالي الوحدات", f"{total_units:,}")
m3.metric("أصناف منخفضة الرصيد", f"{len(low_products):,}")
m4.metric("قيمة المخزون بالتكلفة", f"{stock_cost_value:,.2f}")

if out_products:
    st.error("🚨 أصناف نفد مخزونها: " + "، ".join(p["name"] for p in out_products))
elif low_products:
    st.warning("⚠️ تنبيه نقص المخزون: " + "، ".join(p["name"] for p in low_products))
else:
    st.success("مستويات المخزون ضمن الحدود المحددة.")

tab_dashboard, tab_inventory, tab_sales, tab_purchases, tab_movements, tab_reports, tab_pdf = st.tabs([
    "🏠 الرئيسية", "📦 الأصناف والمخزون", "🧾 المبيعات", "🛒 المشتريات",
    "🔄 حركة المخزون", "📊 التقارير", "📄 استيراد PDF"
])

with tab_dashboard:
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("حالة المخزون")
        stock_rows = []
        for key, p in inventory.items():
            threshold = int(p.get("min_balance", low_limit))
            stock_rows.append({"الكود": key, "الصنف": p["name"], "الرصيد": int(p["balance"]),
                               "حد التنبيه": threshold,
                               "الحالة": "نفد" if p["balance"] == 0 else ("منخفض" if p["balance"] <= threshold else "جيد")})
        st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)
    with right:
        st.subheader("آخر الفواتير")
        if invoices:
            st.dataframe(pd.DataFrame(invoices).tail(8).iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد فواتير مسجلة حتى الآن.")
        st.subheader("أكثر الأصناف احتياجًا للمتابعة")
        if low_products:
            st.dataframe(pd.DataFrame([{"الصنف": p["name"], "الرصيد": p["balance"], "الحد": p["min_balance"]} for p in low_products]),
                         use_container_width=True, hide_index=True)
        else:
            st.caption("لا توجد أصناف تحت حد التنبيه.")

with tab_inventory:
    st.subheader("قائمة الأصناف")
    search = st.text_input("ابحث بالكود أو اسم الصنف", key="product_search")
    rows = []
    for key, p in inventory.items():
        if search.strip().lower() in key.lower() or search.strip().lower() in p["name"].lower():
            rows.append({"الكود": key, "اسم الصنف": p["name"], "الرصيد": p["balance"],
                         "الصلاحية": p["expiry"], "التكلفة": p["cost"], "سعر البيع": p["price"],
                         "حد التنبيه": p["min_balance"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if is_admin:
        with st.expander("➕ إضافة صنف جديد", expanded=False):
            with st.form("add_product_form"):
                new_id = st.text_input("كود الصنف")
                new_name = st.text_input("اسم الصنف")
                c1, c2, c3 = st.columns(3)
                new_balance = c1.number_input("رصيد البداية", min_value=0, step=1)
                new_cost = c2.number_input("تكلفة الوحدة", min_value=0.0, step=1.0)
                new_price = c3.number_input("سعر البيع", min_value=0.0, step=1.0)
                new_expiry = st.text_input("الصلاحية (مثال 2027/12)")
                new_min = st.number_input("حد التنبيه", min_value=0, value=int(low_limit), step=1)
                submitted = st.form_submit_button("حفظ الصنف", use_container_width=True)
            if submitted:
                if not new_id.strip() or not new_name.strip():
                    st.error("أدخل كود الصنف واسمه.")
                elif new_id.strip() in inventory:
                    st.error("هذا الكود مستخدم بالفعل.")
                else:
                    inventory[new_id.strip()] = {"name": new_name.strip(), "balance": int(new_balance),
                        "expiry": new_expiry.strip() or "غير محدد", "cost": float(new_cost),
                        "price": float(new_price), "min_balance": int(new_min)}
                    write_json(DATA_FILE, inventory)
                    if new_balance:
                        add_movement(new_id.strip(), new_name.strip(), "رصيد افتتاحي", int(new_balance), 0, int(new_balance), "إضافة صنف")
                    st.success("تمت إضافة الصنف.")
                    st.rerun()
        with st.expander("✏️ تعديل بيانات صنف", expanded=False):
            if inventory:
                edit_id = st.selectbox("اختر الصنف", list(inventory), format_func=lambda k: f"{k} — {inventory[k]['name']}", key="edit_product")
                p = inventory[edit_id]
                with st.form("edit_product_form"):
                    edit_name = st.text_input("اسم الصنف", value=p["name"])
                    edit_expiry = st.text_input("الصلاحية", value=p["expiry"])
                    ec1, ec2, ec3 = st.columns(3)
                    edit_cost = ec1.number_input("التكلفة", min_value=0.0, value=float(p["cost"]))
                    edit_price = ec2.number_input("سعر البيع", min_value=0.0, value=float(p["price"]))
                    edit_min = ec3.number_input("حد التنبيه", min_value=0, value=int(p["min_balance"]))
                    edit_submit = st.form_submit_button("حفظ التعديلات")
                if edit_submit:
                    if not edit_name.strip():
                        st.error("اسم الصنف مطلوب.")
                    else:
                        p.update({"name": edit_name.strip(), "expiry": edit_expiry.strip() or "غير محدد",
                                  "cost": float(edit_cost), "price": float(edit_price), "min_balance": int(edit_min)})
                        write_json(DATA_FILE, inventory)
                        st.success("تم تحديث بيانات الصنف.")
                        st.rerun()
    else:
        st.info("سجّل دخول المدير لإضافة الأصناف أو تعديلها.")

with tab_sales:
    st.subheader("فاتورة مبيعات")
    if not inventory:
        st.info("أضف صنفًا أولًا.")
    else:
        with st.form("sales_form"):
            customer = st.text_input("اسم العميل / الصيدلية")
            sale_id = st.selectbox("الصنف", list(inventory), format_func=lambda k: f"{k} — {inventory[k]['name']}")
            sale_qty = st.number_input("الكمية", min_value=1, value=1, step=1)
            sale_price = st.number_input("سعر بيع الوحدة", min_value=0.0, value=float(inventory[sale_id]["price"]), step=1.0)
            sale_discount = st.number_input("خصم الفاتورة", min_value=0.0, value=0.0, step=1.0)
            sale_submit = st.form_submit_button("اعتماد البيع وخصم المخزون", use_container_width=True)
        if sale_submit:
            if not is_admin:
                st.error("هذه العملية متاحة للمدير فقط.")
            elif not customer.strip():
                st.error("اسم العميل مطلوب.")
            elif int(sale_qty) > int(inventory[sale_id]["balance"]):
                st.error("الرصيد لا يكفي لإتمام البيع.")
            elif sale_discount > float(sale_qty) * float(sale_price):
                st.error("الخصم لا يمكن أن يتجاوز قيمة الفاتورة.")
            else:
                before = int(inventory[sale_id]["balance"])
                inventory[sale_id]["balance"] = before - int(sale_qty)
                write_json(DATA_FILE, inventory)
                total = int(sale_qty) * float(sale_price) - float(sale_discount)
                cost = int(sale_qty) * float(inventory[sale_id]["cost"])
                invoice = {"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": "بيع",
                           "customer": customer.strip(), "product_id": sale_id, "product": inventory[sale_id]["name"],
                           "quantity": int(sale_qty), "unit_price": float(sale_price), "discount": float(sale_discount),
                           "total": total, "cost": cost, "gross_profit": total - cost}
                invoices.append(invoice)
                write_json(INVOICES_FILE, invoices)
                add_movement(sale_id, inventory[sale_id]["name"], "بيع", int(sale_qty), before,
                             inventory[sale_id]["balance"], f"فاتورة بيع للعميل {customer.strip()}")
                st.success(f"تم حفظ الفاتورة. الإجمالي: {total:,.2f}")
                st.rerun()

with tab_purchases:
    st.subheader("فاتورة مشتريات / توريد")
    if not inventory:
        st.info("أضف صنفًا أولًا.")
    else:
        with st.form("purchase_form"):
            supplier = st.text_input("اسم المورد")
            purchase_id = st.selectbox("الصنف", list(inventory), format_func=lambda k: f"{k} — {inventory[k]['name']}", key="purchase_product")
            purchase_qty = st.number_input("الكمية المستلمة", min_value=1, value=1, step=1)
            purchase_cost = st.number_input("تكلفة الوحدة", min_value=0.0, value=float(inventory[purchase_id]["cost"]), step=1.0)
            purchase_submit = st.form_submit_button("اعتماد الشراء وإضافة المخزون", use_container_width=True)
        if purchase_submit:
            if not is_admin:
                st.error("هذه العملية متاحة للمدير فقط.")
            elif not supplier.strip():
                st.error("اسم المورد مطلوب.")
            else:
                before = int(inventory[purchase_id]["balance"])
                inventory[purchase_id]["balance"] = before + int(purchase_qty)
                inventory[purchase_id]["cost"] = float(purchase_cost)
                write_json(DATA_FILE, inventory)
                total = int(purchase_qty) * float(purchase_cost)
                invoices.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": "شراء",
                    "customer": supplier.strip(), "product_id": purchase_id, "product": inventory[purchase_id]["name"],
                    "quantity": int(purchase_qty), "unit_price": float(purchase_cost), "discount": 0.0,
                    "total": total, "cost": total, "gross_profit": 0.0})
                write_json(INVOICES_FILE, invoices)
                add_movement(purchase_id, inventory[purchase_id]["name"], "شراء", int(purchase_qty), before,
                             inventory[purchase_id]["balance"], f"توريد من {supplier.strip()}")
                st.success(f"تم تسجيل المشتريات. الإجمالي: {total:,.2f}")
                st.rerun()

with tab_movements:
    st.subheader("سجل حركة المخزون")
    if is_admin and inventory:
        with st.form("manual_movement_form"):
            move_id = st.selectbox("الصنف", list(inventory), format_func=lambda k: f"{k} — {inventory[k]['name']}", key="move_product")
            move_type = st.selectbox("نوع الحركة", ["إضافة", "خصم", "تسوية جرد"])
            move_qty = st.number_input("الكمية", min_value=1, value=1, step=1)
            move_note = st.text_input("ملاحظات / سبب الحركة")
            move_submit = st.form_submit_button("حفظ الحركة")
        if move_submit:
            before = int(inventory[move_id]["balance"])
            if move_type == "تسوية جرد":
                after = int(move_qty)
                inventory[move_id]["balance"] = after
                write_json(DATA_FILE, inventory)
                add_movement(move_id, inventory[move_id]["name"], "تسوية جرد", abs(after-before), before, after, move_note)
                st.success("تم حفظ تسوية الجرد.")
                st.rerun()
            else:
                ok, message = change_stock(move_id, int(move_qty), "خصم" if move_type == "خصم" else "إضافة", move_note)
                (st.success if ok else st.error)(message)
                if ok:
                    st.rerun()
    elif not is_admin:
        st.info("سجّل دخول المدير لإجراء حركات المخزون.")
    if movements:
        movement_df = pd.DataFrame(movements)
        st.dataframe(movement_df.iloc[::-1], use_container_width=True, hide_index=True)
        st.download_button("تنزيل سجل الحركة CSV", movement_df.to_csv(index=False).encode("utf-8-sig"),
                           file_name="sfn_stock_movements.csv", mime="text/csv")
    else:
        st.info("لم يتم تسجيل حركات بعد.")

with tab_reports:
    st.subheader("التقارير")
    if invoices:
        df = pd.DataFrame(invoices)
        if "type" not in df.columns:
            df["type"] = "بيع"
        if "total" not in df.columns:
            df["total"] = 0.0
        if "gross_profit" not in df.columns:
            df["gross_profit"] = 0.0
        if "date" in df.columns:
            df["date"] = df["date"].astype(str)
            dates = pd.to_datetime(df["date"], errors="coerce")
            valid_dates = dates.dropna()
            if not valid_dates.empty:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
                date_range = st.date_input("الفترة الزمنية", value=(min_date, max_date))
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    mask = (dates.dt.date >= date_range[0]) & (dates.dt.date <= date_range[1])
                    df = df.loc[mask]
        sales_df = df[df["type"] == "بيع"]
        purchase_df = df[df["type"] == "شراء"]
        revenue = pd.to_numeric(sales_df["total"], errors="coerce").fillna(0).sum()
        purchase_total = pd.to_numeric(purchase_df["total"], errors="coerce").fillna(0).sum()
        gross_profit = pd.to_numeric(sales_df["gross_profit"], errors="coerce").fillna(0).sum()
        r1, r2, r3 = st.columns(3)
        r1.metric("إجمالي المبيعات", f"{revenue:,.2f}")
        r2.metric("إجمالي المشتريات", f"{purchase_total:,.2f}")
        r3.metric("الربح الإجمالي التقديري", f"{gross_profit:,.2f}")
        st.caption("الربح المعروض تقديري قبل المصروفات والضرائب والمرتجعات. الفواتير القديمة التي لا تحتوي على أسعار لا تدخل في الحساب المالي.")
        st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
        st.download_button("تنزيل تقرير الفواتير CSV", df.to_csv(index=False).encode("utf-8-sig"),
                           file_name="sfn_invoices_report.csv", mime="text/csv")
    else:
        st.info("ستظهر التقارير المالية بعد تسجيل فواتير المبيعات والمشتريات.")

with tab_pdf:
    st.subheader("قراءة مستند PDF")
    st.caption("يجب مراجعة الكميات المستخرجة قبل اعتمادها. استخراج النص قد لا يعمل مع المستندات الممسوحة ضوئيًا.")
    uploaded_file = st.file_uploader("رفع فاتورة أو بوليصة PDF", type=["pdf"])
    doc_mode = st.radio("نوع المستند", ["بيع / خصم من المخزون", "شراء / إضافة إلى المخزون"], horizontal=True)
    if uploaded_file is not None:
        if st.button("استخراج الأصناف والكميات", use_container_width=True):
            actions, error = extract_data_from_pdf(uploaded_file)
            if error:
                st.error(error)
            elif not actions:
                st.warning("لم يتم العثور على أصناف وكميات واضحة. لم يتغير المخزون.")
            else:
                st.session_state["pdf_actions"] = actions
                st.session_state["pdf_mode"] = doc_mode
        actions = st.session_state.get("pdf_actions", [])
        if actions:
            st.dataframe(pd.DataFrame(actions), use_container_width=True, hide_index=True)
            st.warning("راجع الكميات قبل الاعتماد. سيتم تحديث المخزون بعد الضغط على زر الاعتماد فقط.")
            if st.button("اعتماد الحركات المستخرجة", type="primary", use_container_width=True):
                if not is_admin:
                    st.error("سجّل دخول المدير لاعتماد المستند.")
                else:
                    mode = st.session_state.get("pdf_mode", "")
                    failed = []
                    for action in actions:
                        key, qty = action["key"], int(action["amount"])
                        before = int(inventory[key]["balance"])
                        is_sale = mode.startswith("بيع")
                        if is_sale and before < qty:
                            failed.append(f"{action['name']}: الرصيد لا يكفي")
                            continue
                        inventory[key]["balance"] = before - qty if is_sale else before + qty
                        add_movement(key, inventory[key]["name"], "بيع من PDF" if is_sale else "شراء من PDF",
                                     qty, before, inventory[key]["balance"], "مستند PDF")
                    write_json(DATA_FILE, inventory)
                    invoices.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                     "type": "بيع من PDF" if mode.startswith("بيع") else "شراء من PDF",
                                     "customer": "مستند PDF", "product": f"{len(actions)} أصناف",
                                     "quantity": sum(int(a["amount"]) for a in actions),
                                     "total": 0.0, "gross_profit": 0.0})
                    write_json(INVOICES_FILE, invoices)
                    st.session_state.pop("pdf_actions", None)
                    if failed:
                        st.warning("تم تنفيذ الأصناف المتاحة فقط: " + "؛ ".join(failed))
                    else:
                        st.success("تم تحديث المخزون وتسجيل الحركة.")
                    st.rerun()

st.caption("SFN Stock App • احتفظ بنسخة احتياطية دورية من ملفات البيانات. تخزين JSON المحلي قد لا يكون دائمًا على الاستضافات السحابية.")
