import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date, timedelta

st.set_page_config(page_title="VetControl Pro", layout="wide", page_icon="🐾")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)
DEFAULT_EXPIRY_DATE = "2099-12-31"


# ==============================
# LOGIN
# ==============================
def check_password():
    def password_entered():
        if (
            st.session_state.get("username") == st.secrets["LOGIN_USER"]
            and st.session_state.get("password") == st.secrets["LOGIN_PASS"]
        ):
            st.session_state["password_correct"] = True
            st.session_state["flash_success"] = "Bienvenido"
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered, use_container_width=True)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Acceso Restringido")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered, use_container_width=True)
        st.error("Usuario o contraseña incorrectos")
        return False
    return True


# ==============================
# ESTILOS
# ==============================
def inject_css():
    st.markdown(
        """
        <style>
            .main { background: #f6f8fb; }
            .block-container { padding-top: 1rem; padding-bottom: 2rem; }
            .hero-card, .section-card {
                background: white;
                border-radius: 24px;
                padding: 18px 20px;
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
                border: 1px solid rgba(226, 232, 240, 0.8);
                margin-bottom: 14px;
            }
            .kpi-card {
                background: white;
                border-radius: 20px;
                padding: 18px;
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
                border: 1px solid rgba(226, 232, 240, 0.85);
                margin-bottom: 10px;
            }
            .kpi-label {
                font-size: 0.88rem;
                color: #64748b;
                margin-bottom: 8px;
                text-transform: uppercase;
                font-weight: 700;
                letter-spacing: 0.02em;
            }
            .kpi-value {
                font-size: 1.95rem;
                font-weight: 800;
                color: #0f172a;
                line-height: 1.05;
            }
            .kpi-delta { font-size: 0.88rem; color: #475569; margin-top: 8px; }
            .small-muted { color: #64748b; font-size: 0.92rem; }
            .stMetric {
                background: white;
                border: 1px solid rgba(226, 232, 240, 0.85);
                padding: 10px;
                border-radius: 16px;
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
            }
            div[data-testid="stDataFrame"] {
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid rgba(226, 232, 240, 0.85);
            }
            section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
                background: #ffffff !important;
                color: #0f172a !important;
                opacity: 1 !important;
                filter: none !important;
            }
            div[data-baseweb="popover"] * {
                opacity: 1 !important;
                filter: none !important;
                color: #0f172a !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==============================
# HELPERS
# ==============================
def safe_float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def safe_int(value):
    try:
        return int(value or 0)
    except Exception:
        return 0


def format_bs(value):
    return f"Bs {safe_float(value):,.2f}"


def format_dt(value, with_time=True):
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M") if with_time else dt.strftime("%d/%m/%Y")
    except Exception:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return str(value)


def parse_iso_to_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except Exception:
            return None


def get_date_range_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtros globales")
    preset = st.sidebar.selectbox("Rango", ["Hoy", "Últimos 7 días", "Este mes", "Mes pasado", "Personalizado"], index=0)
    today = date.today()
    if preset == "Hoy":
        start_date, end_date = today, today
    elif preset == "Últimos 7 días":
        start_date, end_date = today - timedelta(days=6), today
    elif preset == "Este mes":
        start_date, end_date = today.replace(day=1), today
    elif preset == "Mes pasado":
        first_this_month = today.replace(day=1)
        end_date = first_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    else:
        c1, c2 = st.sidebar.columns(2)
        with c1:
            start_date = st.date_input("Desde", value=today.replace(day=1), key="global_start")
        with c2:
            end_date = st.date_input("Hasta", value=today, key="global_end")
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def get_timestamp_range(start_date, end_date):
    return f"{start_date.isoformat()}T00:00:00", f"{end_date.isoformat()}T23:59:59"


def set_flash_success(message):
    st.session_state["flash_success"] = message


def show_flash_success():
    msg = st.session_state.pop("flash_success", None)
    if msg:
        st.success(msg)


def render_kpi_card(label, value, delta_text=""):
    st.markdown(
        f"""
        <div class=\"kpi-card\">
            <div class=\"kpi-label\">{label}</div>
            <div class=\"kpi-value\">{value}</div>
            <div class=\"kpi-delta\">{delta_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def confirm_block(label, key):
    return st.checkbox(f"Confirmo: {label}", key=key)


def init_cart():
    if "cart_items" not in st.session_state:
        st.session_state["cart_items"] = []


def clear_cart():
    st.session_state["cart_items"] = []


# ==============================
# QUERIES
# ==============================
def fetch_clientes():
    try:
        return supabase.table("clientes").select("id, nombre, telefono, puntos_lealtad").order("nombre").execute().data or []
    except Exception:
        return []


def fetch_categorias():
    try:
        return supabase.table("categorias").select("id, nombre").order("nombre").execute().data or []
    except Exception:
        return []


def fetch_productos():
    try:
        return (
            supabase.table("productos")
            .select("id, nombre, descripcion, precio_venta, unidad_medida, stock_minimo, categoria_id, categorias(nombre)")
            .order("nombre")
            .execute()
            .data
            or []
        )
    except Exception:
        return []


def fetch_ventas(start_date=None, end_date=None):
    query = supabase.table("ventas").select("id, fecha, metodo_pago, total, observacion, estado, cliente_id, clientes(nombre)").order("fecha", desc=True)
    if start_date and end_date:
        start_ts, end_ts = get_timestamp_range(start_date, end_date)
        query = query.gte("fecha", start_ts).lte("fecha", end_ts)
    return query.execute().data or []


def fetch_flujo_caja(start_date=None, end_date=None):
    query = supabase.table("flujo_caja").select("*").order("fecha", desc=True)
    if start_date and end_date:
        start_ts, end_ts = get_timestamp_range(start_date, end_date)
        query = query.gte("fecha", start_ts).lte("fecha", end_ts)
    return query.execute().data or []


def fetch_detalle_ventas_con_producto(start_date=None, end_date=None):
    query = (
        supabase.table("detalle_ventas")
        .select("id, venta_id, producto_id, lote_id, cantidad, precio_unitario_aplicado, costo_unitario_lote, ventas(fecha, metodo_pago, total, estado), productos(nombre, unidad_medida)")
        .order("id", desc=True)
    )
    if start_date and end_date:
        start_ts, end_ts = get_timestamp_range(start_date, end_date)
        query = query.gte("ventas.fecha", start_ts).lte("ventas.fecha", end_ts)
    return query.execute().data or []


def fetch_detalles_por_venta(venta_id):
    try:
        return (
            supabase.table("detalle_ventas")
            .select("id, venta_id, producto_id, lote_id, cantidad, precio_unitario_aplicado, costo_unitario_lote, productos(nombre, unidad_medida)")
            .eq("venta_id", venta_id)
            .execute()
            .data
            or []
        )
    except Exception:
        return []


def fetch_inventario_lotes():
    try:
        return (
            supabase.table("inventario_lotes")
            .select("id, producto_id, lote, cantidad_actual, cantidad_inicial, costo_unidad, fecha_vencimiento, fecha_ingreso, productos(nombre, unidad_medida, stock_minimo, precio_venta)")
            .order("fecha_ingreso", desc=True)
            .execute()
            .data
            or []
        )
    except Exception:
        return []


def fetch_categorias_caja():
    try:
        return (
            supabase.table("categorias_caja")
            .select("id, nombre, tipo, activo")
            .eq("activo", True)
            .order("nombre")
            .execute()
            .data
            or []
        )
    except Exception:
        return []


# ==============================
# NEGOCIO
# ==============================
def build_stock_summary(lotes_data):
    grouped = {}
    for item in lotes_data:
        prod = item.get("productos") or {}
        producto_id = item.get("producto_id")
        grouped.setdefault(
            producto_id,
            {
                "Producto ID": producto_id,
                "Producto": prod.get("nombre", "Sin nombre"),
                "Unidad": prod.get("unidad_medida", "Unidad"),
                "Precio referencial": safe_float(prod.get("precio_venta", 0)),
                "Stock actual": 0,
                "Stock mínimo": safe_int(prod.get("stock_minimo", 0)),
            },
        )
        grouped[producto_id]["Stock actual"] += safe_int(item.get("cantidad_actual", 0))
    rows = []
    for row in grouped.values():
        stock_actual = safe_int(row["Stock actual"])
        stock_minimo = safe_int(row["Stock mínimo"])
        row["Estado"] = "Agotado" if stock_actual <= 0 else "Bajo" if stock_actual <= stock_minimo else "OK"
        rows.append(row)
    return pd.DataFrame(rows)


def compute_product_metrics(producto_id, lotes_data, precio_referencia=None):
    lotes_prod = [l for l in lotes_data if l.get("producto_id") == producto_id and safe_int(l.get("cantidad_actual")) > 0]
    stock_total = sum(safe_int(l.get("cantidad_actual")) for l in lotes_prod)
    costo_total = sum(safe_int(l.get("cantidad_actual")) * safe_float(l.get("costo_unidad")) for l in lotes_prod)
    costo_promedio = costo_total / stock_total if stock_total > 0 else 0
    precio_ref = safe_float(precio_referencia)
    margen_pct_ref = ((precio_ref - costo_promedio) / precio_ref) * 100 if precio_ref > 0 else 0
    return {"stock_total": stock_total, "costo_promedio": costo_promedio, "margen_pct_ref": margen_pct_ref}


def search_suggestions(df, column, query):
    if df.empty or not query.strip():
        return pd.DataFrame()
    mask = df[column].astype(str).str.contains(query.strip(), case=False, na=False)
    return df[mask].head(12)


def create_cliente(nombre, telefono):
    nombre = (nombre or "").strip()
    telefono = (telefono or "").strip()
    if not nombre:
        return None, "El nombre es obligatorio"
    res = supabase.table("clientes").insert({"nombre": nombre, "telefono": telefono}).execute()
    data = res.data or []
    if not data:
        return None, "No se pudo crear el cliente"
    return data[0]["id"], "Cliente creado"


def update_lote(lote_id, lote_txt, cantidad_actual, cantidad_inicial, costo_unidad, fecha_vencimiento):
    supabase.table("inventario_lotes").update(
        {
            "lote": lote_txt or None,
            "cantidad_actual": safe_int(cantidad_actual),
            "cantidad_inicial": safe_int(cantidad_inicial),
            "costo_unidad": safe_float(costo_unidad),
            "fecha_vencimiento": str(fecha_vencimiento),
        }
    ).eq("id", lote_id).execute()


def anular_venta(venta_id):
    try:
        venta_rows = supabase.table("ventas").select("id, total, estado, metodo_pago").eq("id", venta_id).execute().data or []
        if not venta_rows:
            return False, "No se encontró la venta."
        venta = venta_rows[0]
        if venta.get("estado") == "ANULADA":
            return False, "La venta ya está anulada."
        detalles = fetch_detalles_por_venta(venta_id)
        if not detalles:
            return False, "La venta no tiene detalle; no se puede anular de forma segura."
        for det in detalles:
            lote_id = det.get("lote_id")
            cantidad = safe_int(det.get("cantidad"))
            lote_rows = supabase.table("inventario_lotes").select("id, cantidad_actual").eq("id", lote_id).execute().data or []
            if not lote_rows:
                return False, f"No se encontró el lote {lote_id}."
            nuevo_stock = safe_int(lote_rows[0].get("cantidad_actual")) + cantidad
            supabase.table("inventario_lotes").update({"cantidad_actual": nuevo_stock}).eq("id", lote_id).execute()
        supabase.table("ventas").update({"estado": "ANULADA"}).eq("id", venta_id).execute()
        supabase.table("flujo_caja").insert(
            {
                "tipo": "EGRESO",
                "monto": safe_float(venta.get("total")),
                "motivo": f"Anulación de venta {venta_id}",
                "fecha": datetime.now().isoformat(),
                "categoria": "ANULACION_VENTA",
                "metodo_pago": venta.get("metodo_pago", "Efectivo"),
                "observacion": "Reversión automática por anulación de venta",
                "venta_id": venta_id,
            }
        ).execute()
        return True, "Venta anulada correctamente. El stock volvió y caja fue ajustada."
    except Exception as e:
        return False, f"No se pudo anular la venta: {e}"


def allocate_stock_for_sale(producto_id, cantidad, lotes):
    lotes_data = [l for l in lotes if l.get("producto_id") == producto_id and safe_int(l.get("cantidad_actual")) > 0]
    lotes_data = sorted(lotes_data, key=lambda x: (str(x.get("fecha_vencimiento") or "9999-12-31"), str(x.get("fecha_ingreso") or "")))
    stock_total = sum(safe_int(l["cantidad_actual"]) for l in lotes_data)
    if stock_total < cantidad:
        return False, f"Stock insuficiente. Disponible: {stock_total}", []
    pending = cantidad
    allocations = []
    for lote in lotes_data:
        if pending <= 0:
            break
        disponible = safe_int(lote.get("cantidad_actual"))
        if disponible <= 0:
            continue
        quitar = min(disponible, pending)
        allocations.append({"lote_id": lote["id"], "cantidad": quitar, "costo": safe_float(lote.get("costo_unidad")), "nuevo_stock": disponible - quitar})
        pending -= quitar
    return True, "OK", allocations


def create_sale_with_cart(cliente_id, metodo_pago, observacion, cart_items, lotes):
    total_general = sum(safe_float(i["subtotal"]) for i in cart_items)
    venta_insert = supabase.table("ventas").insert(
        {
            "cliente_id": cliente_id,
            "total": total_general,
            "metodo_pago": metodo_pago,
            "fecha": datetime.now().isoformat(),
            "observacion": observacion,
            "estado": "COMPLETADA",
        }
    ).execute()
    venta_data = venta_insert.data or []
    if not venta_data:
        return False, "No se pudo crear la venta."
    venta_id = venta_data[0]["id"]

    for item in cart_items:
        ok, msg, allocations = allocate_stock_for_sale(item["producto_id"], safe_int(item["cantidad"]), lotes)
        if not ok:
            return False, f"{item['producto']}: {msg}"
        for alloc in allocations:
            supabase.table("detalle_ventas").insert(
                {
                    "venta_id": venta_id,
                    "producto_id": item["producto_id"],
                    "lote_id": alloc["lote_id"],
                    "cantidad": alloc["cantidad"],
                    "precio_unitario_aplicado": safe_float(item["precio_final"]),
                    "costo_unitario_lote": safe_float(alloc["costo"]),
                }
            ).execute()
            supabase.table("inventario_lotes").update({"cantidad_actual": alloc["nuevo_stock"]}).eq("id", alloc["lote_id"]).execute()

    supabase.table("flujo_caja").insert(
        {
            "tipo": "INGRESO",
            "monto": total_general,
            "motivo": f"Venta #{venta_id}",
            "fecha": datetime.now().isoformat(),
            "categoria": "VENTA",
            "metodo_pago": metodo_pago,
            "observacion": observacion,
            "venta_id": venta_id,
        }
    ).execute()
    return True, venta_id


# ==============================
# APP
# ==============================
if check_password():
    inject_css()
    init_cart()
    show_flash_success()

    st.sidebar.success("Conectado como Administrador")
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

    start_date, end_date = get_date_range_sidebar()

    st.markdown(
        """
        <div class='hero-card'>
            <h1 style='margin:0;color:#123c63;'>🐾 VetControl Pro</h1>
            <div class='small-muted' style='margin-top:6px;'>Control de ventas, inventario, caja y reportes en una sola vista</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    menu = ["📊 Dashboard", "📦 Catálogo", "📥 Entradas", "📦 Stock", "🛒 Ventas", "💰 Caja", "📑 Reportes"]
    choice = st.sidebar.selectbox("Menú", menu)

    # DASHBOARD
    if choice == "📊 Dashboard":
        ventas = fetch_ventas(start_date, end_date)
        flujo = fetch_flujo_caja(start_date, end_date)
        lotes = fetch_inventario_lotes()
        detalles = fetch_detalle_ventas_con_producto(start_date, end_date)
        ventas_ok = [v for v in ventas if v.get("estado") != "ANULADA"]
        ingresos = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "INGRESO")
        egresos = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "EGRESO")
        total_ventas = sum(safe_float(v.get("total")) for v in ventas_ok)
        cantidad_ventas = len(ventas_ok)
        ticket_promedio = total_ventas / cantidad_ventas if cantidad_ventas else 0
        stock_df = build_stock_summary(lotes)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_kpi_card("Ventas del periodo", format_bs(total_ventas), f"{cantidad_ventas} venta(s)")
        with c2:
            render_kpi_card("Ingresos", format_bs(ingresos), "Ventas y otros ingresos")
        with c3:
            render_kpi_card("Egresos", format_bs(egresos), "Compras y gastos")
        with c4:
            render_kpi_card("Saldo neto", format_bs(ingresos - egresos), f"Ticket promedio: {format_bs(ticket_promedio)}")

        d1, d2 = st.columns(2)
        with d1:
            st.markdown("### Evolución de ventas")
            if ventas_ok:
                ventas_df = pd.DataFrame(ventas_ok)
                ventas_df["fecha"] = pd.to_datetime(ventas_df["fecha"])
                ventas_por_dia = ventas_df.groupby(ventas_df["fecha"].dt.date)["total"].sum().reset_index()
                ventas_por_dia.columns = ["Fecha", "Ventas"]
                st.line_chart(ventas_por_dia.set_index("Fecha"))
            else:
                st.info("No hay ventas en el rango seleccionado.")
        with d2:
            st.markdown("### Alertas de stock")
            if not stock_df.empty:
                alertas = stock_df[stock_df["Estado"].isin(["Bajo", "Agotado"])][["Producto", "Unidad", "Stock actual", "Stock mínimo", "Estado"]]
                st.dataframe(alertas, use_container_width=True, hide_index=True) if not alertas.empty else st.success("Sin alertas.")
            else:
                st.info("Sin datos.")

    # CATALOGO
    elif choice == "📦 Catálogo":
        st.header("Gestión de categorías y productos")
        tab1, tab2, tab3, tab4 = st.tabs(["Crear categoría", "Editar categoría", "Crear producto", "Editar producto"])
        categorias = fetch_categorias()
        with tab1:
            with st.form("form_categoria"):
                n_cat = st.text_input("Nombre de la categoría")
                ok_confirm = confirm_block("crear esta categoría", "confirm_cat_create")
                submit = st.form_submit_button("Guardar categoría", use_container_width=True)
                if submit:
                    if not n_cat.strip():
                        st.warning("Ingresa un nombre.")
                    elif not ok_confirm:
                        st.warning("Debes confirmar la acción.")
                    else:
                        supabase.table("categorias").insert({"nombre": n_cat.strip()}).execute()
                        set_flash_success("✅ Categoría creada correctamente")
                        st.rerun()
        with tab2:
            if categorias:
                cat_map = {c["nombre"]: c for c in categorias}
                cat_name = st.selectbox("Categoría", list(cat_map.keys()))
                cat_item = cat_map[cat_name]
                with st.form("form_edit_categoria"):
                    nuevo_nombre = st.text_input("Nuevo nombre", value=cat_item["nombre"])
                    ok_confirm = confirm_block("guardar cambios de la categoría", "confirm_cat_edit")
                    submit = st.form_submit_button("Actualizar categoría", use_container_width=True)
                    if submit and ok_confirm:
                        supabase.table("categorias").update({"nombre": nuevo_nombre.strip()}).eq("id", cat_item["id"]).execute()
                        set_flash_success("✅ Categoría actualizada")
                        st.rerun()
        with tab3:
            if categorias:
                cats = {c["nombre"]: c["id"] for c in categorias}
                with st.form("form_producto"):
                    sel_c = st.selectbox("Categoría", list(cats.keys()))
                    n_p = st.text_input("Nombre del producto")
                    desc_p = st.text_area("Descripción")
                    u_m = st.selectbox("Unidad de medida", ["Unidad", "Kg", "Gr", "Ml", "Lt", "Tabletas", "Caja", "Frasco", "Bolsa"])
                    p_v = st.number_input("Precio de venta referencial", min_value=0.0, step=0.5)
                    s_min = st.number_input("Stock mínimo", min_value=0, value=5, step=1)
                    ok_confirm = confirm_block("crear este producto", "confirm_prod_create")
                    submit = st.form_submit_button("Guardar producto", use_container_width=True)
                    if submit and ok_confirm:
                        supabase.table("productos").insert({"nombre": n_p.strip(), "descripcion": desc_p.strip(), "categoria_id": cats[sel_c], "precio_venta": p_v, "unidad_medida": u_m, "stock_minimo": s_min}).execute()
                        set_flash_success("✅ Producto creado correctamente")
                        st.rerun()
        with tab4:
            productos = fetch_productos()
            if productos and categorias:
                prod_map = {p["nombre"]: p for p in productos}
                prod_name = st.selectbox("Producto", list(prod_map.keys()))
                prod_item = prod_map[prod_name]
                cats = {c["nombre"]: c["id"] for c in categorias}
                categoria_actual = next((k for k, v in cats.items() if v == prod_item.get("categoria_id")), list(cats.keys())[0])
                with st.form("form_edit_producto"):
                    new_cat = st.selectbox("Categoría", list(cats.keys()), index=list(cats.keys()).index(categoria_actual))
                    new_nombre = st.text_input("Nombre", value=prod_item.get("nombre", ""))
                    new_desc = st.text_area("Descripción", value=prod_item.get("descripcion", ""))
                    unidades = ["Unidad", "Kg", "Gr", "Ml", "Lt", "Tabletas", "Caja", "Frasco", "Bolsa"]
                    idx_unidad = unidades.index(prod_item.get("unidad_medida", "Unidad")) if prod_item.get("unidad_medida", "Unidad") in unidades else 0
                    new_unidad = st.selectbox("Unidad de medida", unidades, index=idx_unidad)
                    new_precio = st.number_input("Precio de venta referencial", min_value=0.0, value=safe_float(prod_item.get("precio_venta")), step=0.5)
                    new_stock_min = st.number_input("Stock mínimo", min_value=0, value=safe_int(prod_item.get("stock_minimo")), step=1)
                    ok_confirm = confirm_block("guardar cambios del producto", "confirm_prod_edit")
                    submit = st.form_submit_button("Actualizar producto", use_container_width=True)
                    if submit and ok_confirm:
                        supabase.table("productos").update({"categoria_id": cats[new_cat], "nombre": new_nombre.strip(), "descripcion": new_desc.strip(), "unidad_medida": new_unidad, "precio_venta": new_precio, "stock_minimo": new_stock_min}).eq("id", prod_item["id"]).execute()
                        set_flash_success("✅ Producto actualizado")
                        st.rerun()

    # ENTRADAS
    elif choice == "📥 Entradas":
        st.header("Entradas de inventario")
        productos = fetch_productos()
        lotes = fetch_inventario_lotes()
        tab1, tab2 = st.tabs(["Registrar entrada", "Editar entrada"])
        with tab1:
            if productos:
                prods = {f"{p['nombre']} ({p.get('unidad_medida', 'Unidad')})": p for p in productos}
                with st.form("f_ent"):
                    p_sel = st.selectbox("Producto", list(prods.keys()))
                    lote_txt = st.text_input("Lote")
                    ca = st.number_input("Cantidad", min_value=1, step=1)
                    co = st.number_input("Costo unitario", min_value=0.0, step=0.5)
                    ve = st.date_input("Fecha de vencimiento", value=date(2099, 12, 31))
                    metodo_pago = st.selectbox("Método de pago", ["Efectivo", "QR", "Tarjeta", "Transferencia", "Otro"])
                    observacion = st.text_input("Observación")
                    ok_confirm = confirm_block("registrar esta entrada", "confirm_entry_create")
                    submit = st.form_submit_button("Guardar entrada", use_container_width=True)
                    if submit and ok_confirm:
                        prod = prods[p_sel]
                        supabase.table("inventario_lotes").insert({"producto_id": prod["id"], "lote": lote_txt.strip() or None, "cantidad_actual": ca, "cantidad_inicial": ca, "costo_unidad": co, "fecha_vencimiento": str(ve)}).execute()
                        supabase.table("flujo_caja").insert({"tipo": "EGRESO", "monto": ca * co, "motivo": f"Compra de inventario: {prod['nombre']}", "fecha": datetime.now().isoformat(), "categoria": "COMPRA_INVENTARIO", "metodo_pago": metodo_pago, "observacion": observacion}).execute()
                        set_flash_success("✅ Entrada registrada")
                        st.rerun()
        with tab2:
            if lotes:
                labels = {f"{(l.get('productos') or {}).get('nombre', '-')} | Lote: {l.get('lote') or '-'} | {format_dt(l.get('fecha_ingreso'))}": l for l in lotes}
                sel = st.selectbox("Selecciona la entrada", list(labels.keys()))
                lote_sel = labels[sel]
                with st.form("form_edit_lote"):
                    new_lote = st.text_input("Lote", value=lote_sel.get("lote") or "")
                    new_ca = st.number_input("Cantidad actual", min_value=0, value=safe_int(lote_sel.get("cantidad_actual")), step=1)
                    new_ci = st.number_input("Cantidad inicial", min_value=0, value=safe_int(lote_sel.get("cantidad_inicial")), step=1)
                    new_co = st.number_input("Costo unitario", min_value=0.0, value=safe_float(lote_sel.get("costo_unidad")), step=0.5)
                    new_ve = st.date_input("Fecha de vencimiento", value=parse_iso_to_date(lote_sel.get("fecha_vencimiento")) or date(2099, 12, 31))
                    ok_confirm = confirm_block("guardar cambios de esta entrada", "confirm_entry_edit")
                    submit = st.form_submit_button("Actualizar entrada", use_container_width=True)
                    if submit and ok_confirm:
                        update_lote(lote_sel.get("id"), new_lote.strip(), new_ca, new_ci, new_co, new_ve)
                        set_flash_success("✅ Entrada actualizada")
                        st.rerun()
        if lotes:
            rows = []
            for item in lotes:
                prod = item.get("productos") or {}
                rows.append({"Producto": prod.get("nombre", "Sin nombre"), "Lote": item.get("lote") or "-", "Cantidad actual": safe_int(item.get("cantidad_actual")), "Cantidad inicial": safe_int(item.get("cantidad_inicial")), "Costo unitario": format_bs(item.get("costo_unidad")), "Vencimiento": format_dt(item.get("fecha_vencimiento"), False), "Fecha ingreso": format_dt(item.get("fecha_ingreso"))})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # STOCK
    elif choice == "📦 Stock":
        st.header("Consulta de stock")
        lotes = fetch_inventario_lotes()
        stock_df = build_stock_summary(lotes)
        if not stock_df.empty:
            query = st.text_input("Buscar producto")
            suggestions = search_suggestions(stock_df, "Producto", query)
            view_df = stock_df.copy() if not query.strip() else suggestions.copy()
            st.dataframe(view_df[["Producto", "Unidad", "Stock actual", "Stock mínimo", "Estado"]], use_container_width=True, hide_index=True)

    # VENTAS
    elif choice == "🛒 Ventas":
        st.header("Punto de venta")
        productos = fetch_productos()
        clientes = fetch_clientes()
        lotes = fetch_inventario_lotes()
        stock_df = build_stock_summary(lotes)

        if not productos:
            st.info("Primero registra productos.")
        else:
            left, right = st.columns((1.1, 1.2))
            with left:
                st.subheader("Agregar producto al ticket")
                with st.expander("➕ Crear cliente rápido"):
                    with st.form("form_cliente_rapido"):
                        n_cliente = st.text_input("Nombre del cliente")
                        t_cliente = st.text_input("Teléfono")
                        ok_confirm = confirm_block("crear este cliente", "confirm_cliente_create")
                        submit = st.form_submit_button("Guardar cliente", use_container_width=True)
                        if submit and ok_confirm:
                            _, msg = create_cliente(n_cliente, t_cliente)
                            set_flash_success(f"✅ {msg}")
                            st.rerun()

                if not clientes:
                    st.warning("Debes crear al menos un cliente antes de vender.")
                else:
                    prods = {f"{p['nombre']} ({p.get('unidad_medida', 'Unidad')})": p for p in productos}
                    p_sel_name = st.selectbox("Producto", list(prods.keys()))
                    p_data = prods[p_sel_name]
                    metrics = compute_product_metrics(p_data["id"], lotes, p_data.get("precio_venta"))
                    unidad = p_data.get("unidad_medida", "Unidad")
                    precio_ref = safe_float(p_data.get("precio_venta"))

                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Stock", f"{metrics['stock_total']} {unidad}")
                    with m2:
                        st.metric("Unidad", unidad)
                    with m3:
                        st.metric("Costo promedio", format_bs(metrics["costo_promedio"]))
                    with m4:
                        st.metric("Precio ref.", format_bs(precio_ref))

                    with st.form("form_add_cart"):
                        cantidad = st.number_input(f"Cantidad ({unidad})", min_value=1, step=1)
                        precio_final = st.number_input("Precio unitario final", min_value=0.0, value=precio_ref, step=0.5)
                        calcular = st.checkbox("Calcular línea de venta")
                        if calcular:
                            subtotal = cantidad * precio_final
                            margen_pct = ((precio_final - metrics["costo_promedio"]) / precio_final) * 100 if precio_final > 0 else 0
                            utilidad = (precio_final - metrics["costo_promedio"]) * cantidad
                            r1, r2, r3 = st.columns(3)
                            with r1:
                                render_kpi_card("Subtotal", format_bs(subtotal), "Cantidad x precio")
                            with r2:
                                render_kpi_card("Margen", f"{margen_pct:.2f}%", "Según costo promedio")
                            with r3:
                                render_kpi_card("Utilidad", format_bs(utilidad), "Estimación")
                        submit_add = st.form_submit_button("Agregar al ticket", use_container_width=True)
                        if submit_add:
                            if cantidad <= 0 or precio_final <= 0:
                                st.warning("Cantidad y precio deben ser mayores a cero.")
                            elif metrics["stock_total"] < cantidad:
                                st.error(f"Stock insuficiente. Disponible: {metrics['stock_total']} {unidad}")
                            else:
                                subtotal = cantidad * precio_final
                                utilidad = (precio_final - metrics["costo_promedio"]) * cantidad
                                margen_pct = ((precio_final - metrics["costo_promedio"]) / precio_final) * 100 if precio_final > 0 else 0
                                st.session_state["cart_items"].append(
                                    {
                                        "producto_id": p_data["id"],
                                        "producto": p_data["nombre"],
                                        "unidad": unidad,
                                        "cantidad": cantidad,
                                        "precio_final": precio_final,
                                        "costo_promedio": metrics["costo_promedio"],
                                        "subtotal": subtotal,
                                        "margen_pct": margen_pct,
                                        "utilidad": utilidad,
                                    }
                                )
                                set_flash_success(f"✅ {p_data['nombre']} agregado al ticket")
                                st.rerun()

            with right:
                st.subheader("Ticket actual")
                cart_items = st.session_state.get("cart_items", [])
                if cart_items:
                    cart_df = pd.DataFrame(cart_items)
                    show_df = cart_df.copy()
                    show_df["precio_final"] = show_df["precio_final"].apply(format_bs)
                    show_df["costo_promedio"] = show_df["costo_promedio"].apply(format_bs)
                    show_df["subtotal"] = show_df["subtotal"].apply(format_bs)
                    show_df["utilidad"] = show_df["utilidad"].apply(format_bs)
                    show_df["margen_pct"] = show_df["margen_pct"].apply(lambda x: f"{x:.2f}%")
                    show_df = show_df.rename(columns={"producto": "Producto", "unidad": "Unidad", "cantidad": "Cantidad", "precio_final": "Precio", "costo_promedio": "Costo prom.", "subtotal": "Subtotal", "margen_pct": "Margen", "utilidad": "Utilidad"})
                    st.dataframe(show_df[["Producto", "Unidad", "Cantidad", "Precio", "Subtotal", "Margen", "Utilidad"]], use_container_width=True, hide_index=True)

                    total_general = sum(safe_float(i["subtotal"]) for i in cart_items)
                    utilidad_general = sum(safe_float(i["utilidad"]) for i in cart_items)
                    margen_general = (utilidad_general / total_general * 100) if total_general > 0 else 0
                    f1, f2, f3 = st.columns(3)
                    with f1:
                        render_kpi_card("Total ticket", format_bs(total_general), f"{len(cart_items)} línea(s)")
                    with f2:
                        render_kpi_card("Utilidad estimada", format_bs(utilidad_general), "Suma del ticket")
                    with f3:
                        render_kpi_card("Margen estimado", f"{margen_general:.2f}%", "Total ticket")

                    clientes = fetch_clientes()
                    client_map = {c['nombre']: c['id'] for c in clientes}
                    with st.form("form_finish_sale"):
                        cliente_sel = st.selectbox("Cliente", list(client_map.keys()))
                        met = st.selectbox("Método de pago", ["Efectivo", "QR", "Tarjeta", "Transferencia"])
                        observacion = st.text_input("Observación")
                        ok_confirm = confirm_block("finalizar esta venta", "confirm_sale_finish")
                        c1, c2 = st.columns(2)
                        with c1:
                            submit_finish = st.form_submit_button("Finalizar venta", use_container_width=True)
                        with c2:
                            submit_clear = st.form_submit_button("Vaciar ticket", use_container_width=True)
                        if submit_clear:
                            clear_cart()
                            set_flash_success("✅ Ticket vaciado")
                            st.rerun()
                        if submit_finish:
                            if not ok_confirm:
                                st.warning("Debes confirmar la acción.")
                            else:
                                ok, result = create_sale_with_cart(client_map[cliente_sel], met, observacion, cart_items, lotes)
                                if ok:
                                    clear_cart()
                                    set_flash_success(f"✅ Venta registrada correctamente. ID: {result}")
                                    st.rerun()
                                else:
                                    st.error(result)
                else:
                    st.info("Aún no agregaste productos al ticket.")

        st.markdown("### Historial de ventas")
        ventas = fetch_ventas(start_date, end_date)
        if ventas:
            rows = []
            for v in ventas:
                cliente = (v.get("clientes") or {}).get("nombre", "-")
                rows.append({"ID": v.get("id"), "Fecha": format_dt(v.get("fecha")), "Cliente": cliente, "Método": v.get("metodo_pago"), "Total": format_bs(v.get("total")), "Estado": v.get("estado"), "Observación": v.get("observacion") or ""})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            ventas_activas = [v for v in ventas if v.get("estado") != "ANULADA"]
            if ventas_activas:
                venta_opts = {f"{format_dt(v.get('fecha'))} | {(v.get('clientes') or {}).get('nombre', '-')} | {format_bs(v.get('total'))}": v['id'] for v in ventas_activas}
                venta_sel = st.selectbox("Selecciona la venta a anular", list(venta_opts.keys()))
                ok_confirm = st.checkbox("Confirmo que deseo anular esta venta", key="confirm_sale_cancel")
                if st.button("Anular venta seleccionada", use_container_width=True):
                    if not ok_confirm:
                        st.warning("Debes confirmar la acción.")
                    else:
                        ok, msg = anular_venta(venta_opts[venta_sel])
                        if ok:
                            set_flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(msg)

    # CAJA
    elif choice == "💰 Caja":
        st.header("Caja y movimientos")
        categorias_caja = fetch_categorias_caja()
        opciones_categorias = [c["nombre"] for c in categorias_caja] if categorias_caja else ["VENTA", "OTROS_INGRESOS", "COMPRA_INVENTARIO", "GASOLINA", "SERVICIOS", "ALQUILER", "SUELDOS", "RETIRO", "AJUSTE", "OTROS", "ANULACION_VENTA"]
        c1, c2 = st.columns((1, 1.3))
        with c1:
            with st.form("form_caja"):
                tipo = st.selectbox("Tipo", ["INGRESO", "EGRESO"])
                categoria = st.selectbox("Categoría", opciones_categorias)
                monto = st.number_input("Monto", min_value=0.0, step=0.5)
                fecha_mov = st.date_input("Fecha del movimiento", value=date.today())
                metodo_pago = st.selectbox("Método de pago", ["Efectivo", "QR", "Tarjeta", "Transferencia", "Otro"])
                motivo = st.text_input("Motivo")
                observacion = st.text_area("Observación")
                referencia = st.text_input("Referencia")
                ok_confirm = confirm_block("registrar este movimiento", "confirm_cash_create")
                submit = st.form_submit_button("Guardar movimiento", use_container_width=True)
                if submit and ok_confirm:
                    supabase.table("flujo_caja").insert({"tipo": tipo, "monto": monto, "motivo": motivo.strip(), "fecha": f"{fecha_mov.isoformat()}T12:00:00", "categoria": categoria, "metodo_pago": metodo_pago, "observacion": observacion.strip(), "referencia": referencia.strip()}).execute()
                    set_flash_success("✅ Movimiento registrado")
                    st.rerun()
        with c2:
            flujo = fetch_flujo_caja(start_date, end_date)
            ing = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "INGRESO")
            egr = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "EGRESO")
            k1, k2, k3 = st.columns(3)
            with k1:
                render_kpi_card("Ingresos", format_bs(ing), "Periodo")
            with k2:
                render_kpi_card("Egresos", format_bs(egr), "Periodo")
            with k3:
                render_kpi_card("Saldo neto", format_bs(ing - egr), "Ingresos - egresos")
        flujo = fetch_flujo_caja(start_date, end_date)
        if flujo:
            rows = []
            for x in flujo:
                rows.append({"Fecha": format_dt(x.get("fecha")), "Tipo": x.get("tipo"), "Categoría": x.get("categoria") or "-", "Motivo": x.get("motivo"), "Monto": format_bs(x.get("monto")), "Método": x.get("metodo_pago") or "-", "Observación": x.get("observacion") or ""})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # REPORTES
    elif choice == "📑 Reportes":
        st.header("Reportes")
        tab1, tab2, tab3, tab4 = st.tabs(["Ventas", "Ventas por cliente", "Caja", "Inventario"])
        with tab1:
            ventas = fetch_ventas(start_date, end_date)
            detalles = fetch_detalle_ventas_con_producto(start_date, end_date)
            total_ventas = sum(safe_float(v.get("total")) for v in ventas if v.get("estado") != "ANULADA")
            cantidad_ventas = len([v for v in ventas if v.get("estado") != "ANULADA"])
            ticket_promedio = total_ventas / cantidad_ventas if cantidad_ventas else 0
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total vendido", format_bs(total_ventas))
            with c2:
                st.metric("Cantidad de ventas", cantidad_ventas)
            with c3:
                st.metric("Ticket promedio", format_bs(ticket_promedio))
            rows = []
            for d in detalles:
                venta = d.get("ventas") or {}
                prod = d.get("productos") or {}
                cantidad = safe_int(d.get("cantidad"))
                precio = safe_float(d.get("precio_unitario_aplicado"))
                costo = safe_float(d.get("costo_unitario_lote"))
                rows.append({"Fecha": format_dt(venta.get("fecha")), "Producto": prod.get("nombre", "-"), "Cantidad": cantidad, "Precio unitario": format_bs(precio), "Ingreso": format_bs(cantidad * precio), "Costo": format_bs(cantidad * costo), "Utilidad bruta": format_bs((cantidad * precio) - (cantidad * costo)), "Método": venta.get("metodo_pago", "-"), "Estado": venta.get("estado", "-")})
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with tab2:
            ventas = fetch_ventas(start_date, end_date)
            rows = []
            for v in ventas:
                rows.append({"Cliente": (v.get("clientes") or {}).get("nombre", "-"), "Fecha": format_dt(v.get("fecha")), "Total": safe_float(v.get("total")), "Estado": v.get("estado")})
            cli_df = pd.DataFrame(rows)
            if not cli_df.empty:
                resumen = cli_df.groupby("Cliente", as_index=False).agg(Compras=("Total", "count"), Total=("Total", "sum"), Ticket_promedio=("Total", "mean"), Ultima_compra=("Fecha", "max")).sort_values(by="Total", ascending=False)
                resumen["Total"] = resumen["Total"].apply(format_bs)
                resumen["Ticket_promedio"] = resumen["Ticket_promedio"].apply(format_bs)
                st.dataframe(resumen, use_container_width=True, hide_index=True)
        with tab3:
            flujo = fetch_flujo_caja(start_date, end_date)
            if flujo:
                rows = []
                for x in flujo:
                    rows.append({"Fecha": format_dt(x.get("fecha")), "Tipo": x.get("tipo"), "Categoría": x.get("categoria") or "-", "Motivo": x.get("motivo"), "Monto": format_bs(x.get("monto"))})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with tab4:
            lotes = fetch_inventario_lotes()
            stock_df = build_stock_summary(lotes)
            if not stock_df.empty:
                st.dataframe(stock_df[["Producto", "Unidad", "Stock actual", "Stock mínimo", "Estado"]], use_container_width=True, hide_index=True)
