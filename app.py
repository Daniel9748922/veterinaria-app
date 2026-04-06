import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date, timedelta

# ==============================
# CONFIGURACION
# ==============================
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
            .main {
                background: #f6f8fb;
            }
            .block-container {
                padding-top: 1rem;
                padding-bottom: 2rem;
            }
            .hero-card {
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
                font-weight: 600;
                letter-spacing: 0.02em;
            }
            .kpi-value {
                font-size: 1.95rem;
                font-weight: 800;
                color: #0f172a;
                line-height: 1.05;
            }
            .kpi-delta {
                font-size: 0.88rem;
                color: #475569;
                margin-top: 8px;
            }
            .section-card {
                background: white;
                border-radius: 24px;
                padding: 18px;
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
                border: 1px solid rgba(226, 232, 240, 0.85);
                margin-bottom: 14px;
            }
            .small-muted {
                color: #64748b;
                font-size: 0.92rem;
            }
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
            .pill-ok {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 0.8rem;
                font-weight: 700;
                color: #065f46;
                background: #d1fae5;
            }
            .pill-warn {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 0.8rem;
                font-weight: 700;
                color: #92400e;
                background: #fef3c7;
            }
            .pill-danger {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 0.8rem;
                font-weight: 700;
                color: #991b1b;
                background: #fee2e2;
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
            dt = datetime.strptime(str(value)[:19], "%Y-%m-%dT%H:%M:%S")
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
    preset = st.sidebar.selectbox(
        "Rango",
        ["Hoy", "Últimos 7 días", "Este mes", "Mes pasado", "Personalizado"],
        index=0,
    )
    today = date.today()

    if preset == "Hoy":
        start_date = today
        end_date = today
    elif preset == "Últimos 7 días":
        start_date = today - timedelta(days=6)
        end_date = today
    elif preset == "Este mes":
        start_date = today.replace(day=1)
        end_date = today
    elif preset == "Mes pasado":
        first_this_month = today.replace(day=1)
        end_date = first_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    else:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Desde", value=today.replace(day=1), key="global_start")
        with col2:
            end_date = st.date_input("Hasta", value=today, key="global_end")

    if start_date > end_date:
        st.sidebar.error("La fecha inicial no puede ser mayor a la final")
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


def search_suggestions(df, column, query):
    if df.empty or not query.strip():
        return pd.DataFrame()
    mask = df[column].astype(str).str.contains(query.strip(), case=False, na=False)
    return df[mask].head(12)


# ==============================
# QUERIES
# ==============================
def fetch_clientes():
    try:
        res = supabase.table("clientes").select("id, nombre, telefono, puntos_lealtad").order("nombre").execute()
        return res.data or []
    except Exception:
        return []


def fetch_categorias():
    try:
        res = supabase.table("categorias").select("id, nombre").order("nombre").execute()
        return res.data or []
    except Exception:
        return []


def fetch_productos():
    try:
        res = (
            supabase.table("productos")
            .select("id, nombre, descripcion, precio_venta, unidad_medida, stock_minimo, categoria_id, categorias(nombre)")
            .order("nombre")
            .execute()
        )
        return res.data or []
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
        .select(
            "id, venta_id, producto_id, lote_id, cantidad, precio_unitario_aplicado, costo_unitario_lote, ventas(fecha, metodo_pago, total, estado), productos(nombre, unidad_medida)"
        )
        .order("id", desc=True)
    )
    if start_date and end_date:
        start_ts, end_ts = get_timestamp_range(start_date, end_date)
        query = query.gte("ventas.fecha", start_ts).lte("ventas.fecha", end_ts)
    return query.execute().data or []


def fetch_detalles_por_venta(venta_id):
    try:
        res = (
            supabase.table("detalle_ventas")
            .select("id, venta_id, producto_id, lote_id, cantidad, precio_unitario_aplicado, costo_unitario_lote, productos(nombre, unidad_medida)")
            .eq("venta_id", venta_id)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def fetch_inventario_lotes():
    try:
        res = (
            supabase.table("inventario_lotes")
            .select(
                "id, producto_id, lote, cantidad_actual, cantidad_inicial, costo_unidad, fecha_vencimiento, fecha_ingreso, productos(nombre, unidad_medida, stock_minimo, precio_venta)"
            )
            .order("fecha_ingreso", desc=True)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def fetch_categorias_caja():
    try:
        res = (
            supabase.table("categorias_caja")
            .select("id, nombre, tipo, activo")
            .eq("activo", True)
            .order("nombre")
            .execute()
        )
        return res.data or []
    except Exception:
        return []


# ==============================
# NEGOCIO
# ==============================
def build_stock_summary(lotes_data):
    rows = []
    grouped = {}
    for item in lotes_data:
        prod = item.get("productos") or {}
        producto = prod.get("nombre", "Sin nombre")
        unidad = prod.get("unidad_medida", "Unidad")
        stock_minimo = safe_int(prod.get("stock_minimo", 0))
        cantidad_actual = safe_int(item.get("cantidad_actual", 0))
        producto_id = item.get("producto_id")
        precio_ref = safe_float(prod.get("precio_venta", 0))

        grouped.setdefault(
            producto_id,
            {
                "Producto ID": producto_id,
                "Producto": producto,
                "Unidad": unidad,
                "Precio referencial": precio_ref,
                "Stock actual": 0,
                "Stock mínimo": stock_minimo,
            },
        )
        grouped[producto_id]["Stock actual"] += cantidad_actual

    for _, row in grouped.items():
        stock_actual = safe_int(row["Stock actual"])
        stock_minimo = safe_int(row["Stock mínimo"])
        if stock_actual <= 0:
            estado = "Agotado"
        elif stock_actual <= stock_minimo:
            estado = "Bajo"
        else:
            estado = "OK"
        row["Estado"] = estado
        rows.append(row)
    return pd.DataFrame(rows)


def compute_product_metrics(producto_id, lotes_data, precio_referencia=None):
    lotes_prod = [l for l in lotes_data if l.get("producto_id") == producto_id and safe_int(l.get("cantidad_actual")) > 0]
    stock_total = sum(safe_int(l.get("cantidad_actual")) for l in lotes_prod)
    costo_total = sum(safe_int(l.get("cantidad_actual")) * safe_float(l.get("costo_unidad")) for l in lotes_prod)
    costo_promedio = costo_total / stock_total if stock_total > 0 else 0
    precio_ref = safe_float(precio_referencia)
    margen_pct_ref = ((precio_ref - costo_promedio) / precio_ref) * 100 if precio_ref > 0 else 0
    return {
        "stock_total": stock_total,
        "costo_promedio": costo_promedio,
        "margen_pct_ref": margen_pct_ref,
    }


def get_or_create_categoria(nombre):
    nombre = (nombre or "").strip()
    if not nombre:
        return None
    cats = fetch_categorias()
    for c in cats:
        if c["nombre"].strip().lower() == nombre.lower():
            return c["id"]
    res = supabase.table("categorias").insert({"nombre": nombre}).execute()
    data = res.data or []
    return data[0]["id"] if data else None


def get_or_create_producto(categoria_id, nombre, unidad_medida="Unidad", precio_venta=0):
    nombre = (nombre or "").strip()
    if not nombre:
        return None
    prods = fetch_productos()
    for p in prods:
        if p["nombre"].strip().lower() == nombre.lower():
            return p["id"]
    res = supabase.table("productos").insert(
        {
            "categoria_id": categoria_id,
            "nombre": nombre,
            "precio_venta": safe_float(precio_venta),
            "unidad_medida": unidad_medida or "Unidad",
            "stock_minimo": 0,
            "descripcion": "",
        }
    ).execute()
    data = res.data or []
    return data[0]["id"] if data else None


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
                return False, f"No se encontró el lote {lote_id} para restaurar stock."
            lote_actual = lote_rows[0]
            nuevo_stock = safe_int(lote_actual.get("cantidad_actual")) + cantidad
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
        return True, "Venta anulada correctamente. El stock fue restaurado y caja ajustada."
    except Exception as e:
        return False, f"No se pudo anular la venta: {e}"


def import_inventory_from_dataframe(df):
    created_rows = 0
    for _, row in df.iterrows():
        categoria = str(row.get("categoria", "")).strip()
        producto = str(row.get("producto", "")).strip()
        cantidad = safe_int(row.get("cantidad", 0))
        costo_unitario = safe_float(row.get("costo_unitario", 0))
        unidad_medida = str(row.get("unidad_medida", "Unidad") or "Unidad").strip()
        lote = str(row.get("lote", "") or "").strip()
        fecha_v = row.get("fecha_vencimiento", DEFAULT_EXPIRY_DATE)
        if pd.isna(fecha_v) or str(fecha_v).strip() == "":
            fecha_v = DEFAULT_EXPIRY_DATE
        else:
            try:
                fecha_v = pd.to_datetime(fecha_v).strftime("%Y-%m-%d")
            except Exception:
                fecha_v = DEFAULT_EXPIRY_DATE

        if not categoria or not producto or cantidad <= 0:
            continue

        categoria_id = get_or_create_categoria(categoria)
        producto_id = get_or_create_producto(categoria_id, producto, unidad_medida, 0)

        supabase.table("inventario_lotes").insert(
            {
                "producto_id": producto_id,
                "lote": lote or None,
                "cantidad_actual": cantidad,
                "cantidad_inicial": cantidad,
                "costo_unidad": costo_unitario,
                "fecha_vencimiento": fecha_v,
            }
        ).execute()
        created_rows += 1
    return created_rows


# ==============================
# APP
# ==============================
if check_password():
    inject_css()
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

    menu = [
        "📊 Dashboard",
        "📦 Catálogo",
        "📥 Entradas",
        "📦 Stock",
        "🛒 Ventas",
        "💰 Caja",
        "📑 Reportes",
        "📤 Importación masiva",
    ]
    choice = st.sidebar.selectbox("Menú", menu)

    # ==============================
    # DASHBOARD
    # ==============================
    if choice == "📊 Dashboard":
        ventas = fetch_ventas(start_date, end_date)
        flujo = fetch_flujo_caja(start_date, end_date)
        lotes = fetch_inventario_lotes()
        detalles = fetch_detalle_ventas_con_producto(start_date, end_date)

        ventas_ok = [v for v in ventas if v.get("estado") != "ANULADA"]
        ingresos = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "INGRESO")
        egresos = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "EGRESO")
        saldo_neto = ingresos - egresos
        total_ventas = sum(safe_float(v.get("total")) for v in ventas_ok)
        cantidad_ventas = len(ventas_ok)
        ticket_promedio = total_ventas / cantidad_ventas if cantidad_ventas else 0

        stock_df = build_stock_summary(lotes)
        stock_bajo = int((stock_df["Estado"] == "Bajo").sum()) if not stock_df.empty else 0
        agotados = int((stock_df["Estado"] == "Agotado").sum()) if not stock_df.empty else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            render_kpi_card("Ventas del periodo", format_bs(total_ventas), f"{cantidad_ventas} venta(s)")
        with k2:
            render_kpi_card("Ingresos", format_bs(ingresos), "Ventas y otros ingresos")
        with k3:
            render_kpi_card("Egresos", format_bs(egresos), "Compras y gastos")
        with k4:
            render_kpi_card("Saldo neto", format_bs(saldo_neto), f"Ticket promedio: {format_bs(ticket_promedio)}")

        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Stock bajo", stock_bajo)
        with s2:
            st.metric("Agotados", agotados)
        with s3:
            st.metric("Ventas anuladas", len([v for v in ventas if v.get('estado') == 'ANULADA']))

        c1, c2 = st.columns((1.2, 1))
        with c1:
            st.markdown("### Evolución de ventas")
            if ventas_ok:
                ventas_df = pd.DataFrame(ventas_ok)
                ventas_df["fecha"] = pd.to_datetime(ventas_df["fecha"])
                ventas_por_dia = ventas_df.groupby(ventas_df["fecha"].dt.date)["total"].sum().reset_index()
                ventas_por_dia.columns = ["Fecha", "Ventas"]
                st.line_chart(ventas_por_dia.set_index("Fecha"))
            else:
                st.info("No hay ventas en el rango seleccionado.")

        with c2:
            st.markdown("### Ventas por método de pago")
            if ventas_ok:
                ventas_metodo_df = pd.DataFrame(ventas_ok)
                ventas_metodo = ventas_metodo_df.groupby("metodo_pago")["total"].sum().reset_index()
                ventas_metodo.columns = ["Método de pago", "Ventas"]
                st.bar_chart(ventas_metodo.set_index("Método de pago"))
            else:
                st.info("No hay datos para mostrar.")

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("### Top productos vendidos")
            rows = []
            for d in detalles:
                venta = d.get("ventas") or {}
                if venta.get("estado") == "ANULADA":
                    continue
                prod = d.get("productos") or {}
                rows.append(
                    {
                        "Producto": prod.get("nombre", "Sin nombre"),
                        "Cantidad": safe_int(d.get("cantidad")),
                        "Ingreso": safe_int(d.get("cantidad")) * safe_float(d.get("precio_unitario_aplicado")),
                    }
                )
            if rows:
                top_df = pd.DataFrame(rows)
                top_df = top_df.groupby("Producto", as_index=False).agg({"Cantidad": "sum", "Ingreso": "sum"}).sort_values(by="Ingreso", ascending=False).head(8)
                top_df["Ingreso"] = top_df["Ingreso"].apply(format_bs)
                st.dataframe(top_df, use_container_width=True, hide_index=True)
            else:
                st.info("Sin ventas detalladas en este periodo.")

        with c4:
            st.markdown("### Alertas de stock")
            if not stock_df.empty:
                alertas = stock_df[stock_df["Estado"].isin(["Bajo", "Agotado"])][["Producto", "Unidad", "Stock actual", "Stock mínimo", "Estado"]]
                if alertas.empty:
                    st.success("No hay alertas relevantes.")
                else:
                    st.dataframe(alertas, use_container_width=True, hide_index=True)
            else:
                st.info("Sin datos de inventario.")

    # ==============================
    # CATALOGO
    # ==============================
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
                        try:
                            supabase.table("categorias").insert({"nombre": n_cat.strip()}).execute()
                            set_flash_success("✅ Categoría creada correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo crear la categoría: {e}")

        with tab2:
            if not categorias:
                st.info("No hay categorías para editar.")
            else:
                cat_map = {c["nombre"]: c for c in categorias}
                cat_name = st.selectbox("Categoría", list(cat_map.keys()))
                cat_item = cat_map[cat_name]
                with st.form("form_edit_categoria"):
                    nuevo_nombre = st.text_input("Nuevo nombre", value=cat_item["nombre"])
                    ok_confirm = confirm_block("guardar cambios de la categoría", "confirm_cat_edit")
                    submit = st.form_submit_button("Actualizar categoría", use_container_width=True)
                    if submit:
                        if not nuevo_nombre.strip():
                            st.warning("El nombre no puede estar vacío.")
                        elif not ok_confirm:
                            st.warning("Debes confirmar la acción.")
                        else:
                            try:
                                supabase.table("categorias").update({"nombre": nuevo_nombre.strip()}).eq("id", cat_item["id"]).execute()
                                set_flash_success("✅ Categoría actualizada")
                                st.rerun()
                            except Exception as e:
                                st.error(f"No se pudo editar la categoría: {e}")

        with tab3:
            if not categorias:
                st.info("Primero crea una categoría.")
            else:
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
                    if submit:
                        if not n_p.strip():
                            st.warning("Ingresa el nombre del producto.")
                        elif not ok_confirm:
                            st.warning("Debes confirmar la acción.")
                        else:
                            try:
                                supabase.table("productos").insert(
                                    {
                                        "nombre": n_p.strip(),
                                        "descripcion": desc_p.strip(),
                                        "categoria_id": cats[sel_c],
                                        "precio_venta": p_v,
                                        "unidad_medida": u_m,
                                        "stock_minimo": s_min,
                                    }
                                ).execute()
                                set_flash_success("✅ Producto creado correctamente")
                                st.rerun()
                            except Exception as e:
                                st.error(f"No se pudo crear el producto: {e}")

        with tab4:
            productos = fetch_productos()
            if not productos:
                st.info("No hay productos para editar.")
            else:
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
                    unidad_actual = prod_item.get("unidad_medida", "Unidad")
                    idx_unidad = unidades.index(unidad_actual) if unidad_actual in unidades else 0
                    new_unidad = st.selectbox("Unidad de medida", unidades, index=idx_unidad)
                    new_precio = st.number_input("Precio de venta referencial", min_value=0.0, value=safe_float(prod_item.get("precio_venta")), step=0.5)
                    new_stock_min = st.number_input("Stock mínimo", min_value=0, value=safe_int(prod_item.get("stock_minimo")), step=1)
                    ok_confirm = confirm_block("guardar cambios del producto", "confirm_prod_edit")
                    submit = st.form_submit_button("Actualizar producto", use_container_width=True)
                    if submit:
                        if not ok_confirm:
                            st.warning("Debes confirmar la acción.")
                        else:
                            try:
                                supabase.table("productos").update(
                                    {
                                        "categoria_id": cats[new_cat],
                                        "nombre": new_nombre.strip(),
                                        "descripcion": new_desc.strip(),
                                        "unidad_medida": new_unidad,
                                        "precio_venta": new_precio,
                                        "stock_minimo": new_stock_min,
                                    }
                                ).eq("id", prod_item["id"]).execute()
                                set_flash_success("✅ Producto actualizado")
                                st.rerun()
                            except Exception as e:
                                st.error(f"No se pudo editar el producto: {e}")

        st.markdown("### Catálogo actual")
        productos = fetch_productos()
        if productos:
            rows = []
            for p in productos:
                categoria = (p.get("categorias") or {}).get("nombre", "-")
                rows.append(
                    {
                        "Producto": p.get("nombre"),
                        "Categoría": categoria,
                        "Precio venta": format_bs(p.get("precio_venta")),
                        "Unidad": p.get("unidad_medida"),
                        "Stock mínimo": safe_int(p.get("stock_minimo")),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Todavía no hay productos registrados.")

    # ==============================
    # ENTRADAS
    # ==============================
    elif choice == "📥 Entradas":
        st.header("Entradas de inventario")
        productos = fetch_productos()
        lotes = fetch_inventario_lotes()

        tab1, tab2 = st.tabs(["Registrar entrada", "Editar entrada"])
        with tab1:
            if not productos:
                st.info("Primero registra productos.")
            else:
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
                    if submit:
                        if not ok_confirm:
                            st.warning("Debes confirmar la acción.")
                        else:
                            prod = prods[p_sel]
                            try:
                                supabase.table("inventario_lotes").insert(
                                    {
                                        "producto_id": prod["id"],
                                        "lote": lote_txt.strip() or None,
                                        "cantidad_actual": ca,
                                        "cantidad_inicial": ca,
                                        "costo_unidad": co,
                                        "fecha_vencimiento": str(ve),
                                    }
                                ).execute()
                                supabase.table("flujo_caja").insert(
                                    {
                                        "tipo": "EGRESO",
                                        "monto": ca * co,
                                        "motivo": f"Compra de inventario: {prod['nombre']}",
                                        "fecha": datetime.now().isoformat(),
                                        "categoria": "COMPRA_INVENTARIO",
                                        "metodo_pago": metodo_pago,
                                        "observacion": observacion,
                                    }
                                ).execute()
                                set_flash_success("✅ Entrada registrada correctamente")
                                st.rerun()
                            except Exception as e:
                                st.error(f"No se pudo registrar la entrada: {e}")

        with tab2:
            if not lotes:
                st.info("No hay entradas para editar.")
            else:
                rows = []
                for l in lotes:
                    prod = l.get("productos") or {}
                    rows.append(
                        {
                            "label": f"{prod.get('nombre', 'Sin nombre')} | Lote: {l.get('lote') or '-'} | Ingreso: {format_dt(l.get('fecha_ingreso'))}",
                            "id": l.get("id"),
                        }
                    )
                opts = {r["label"]: r["id"] for r in rows}
                selected_label = st.selectbox("Selecciona la entrada", list(opts.keys()))
                lote_sel = next((l for l in lotes if l.get("id") == opts[selected_label]), None)
                if lote_sel:
                    with st.form("form_edit_lote"):
                        prod = lote_sel.get("productos") or {}
                        st.caption(f"Producto: {prod.get('nombre', '-')}")
                        new_lote = st.text_input("Lote", value=lote_sel.get("lote") or "")
                        new_ca = st.number_input("Cantidad actual", min_value=0, value=safe_int(lote_sel.get("cantidad_actual")), step=1)
                        new_ci = st.number_input("Cantidad inicial", min_value=0, value=safe_int(lote_sel.get("cantidad_inicial")), step=1)
                        new_co = st.number_input("Costo unitario", min_value=0.0, value=safe_float(lote_sel.get("costo_unidad")), step=0.5)
                        fecha_v = parse_iso_to_date(lote_sel.get("fecha_vencimiento")) or date(2099, 12, 31)
                        new_ve = st.date_input("Fecha de vencimiento", value=fecha_v)
                        ok_confirm = confirm_block("guardar cambios de esta entrada", "confirm_entry_edit")
                        submit = st.form_submit_button("Actualizar entrada", use_container_width=True)
                        if submit:
                            if not ok_confirm:
                                st.warning("Debes confirmar la acción.")
                            else:
                                try:
                                    update_lote(lote_sel.get("id"), new_lote.strip(), new_ca, new_ci, new_co, new_ve)
                                    set_flash_success("✅ Entrada actualizada")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"No se pudo actualizar la entrada: {e}")

        st.markdown("### Historial de entradas")
        if lotes:
            rows = []
            for item in lotes:
                prod = item.get("productos") or {}
                rows.append(
                    {
                        "Producto": prod.get("nombre", "Sin nombre"),
                        "Lote": item.get("lote") or "-",
                        "Cantidad actual": safe_int(item.get("cantidad_actual")),
                        "Cantidad inicial": safe_int(item.get("cantidad_inicial")),
                        "Costo unitario": format_bs(item.get("costo_unidad")),
                        "Vencimiento": format_dt(item.get("fecha_vencimiento"), with_time=False),
                        "Fecha ingreso": format_dt(item.get("fecha_ingreso")),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No hay lotes registrados.")

    # ==============================
    # STOCK
    # ==============================
    elif choice == "📦 Stock":
        st.header("Consulta de stock")
        lotes = fetch_inventario_lotes()
        stock_df = build_stock_summary(lotes)

        if stock_df.empty:
            st.info("No hay stock registrado.")
        else:
            query = st.text_input("Buscar producto")
            suggestions = search_suggestions(stock_df, "Producto", query)
            if query.strip() and not suggestions.empty:
                st.caption("Sugerencias")
                st.dataframe(suggestions[["Producto", "Unidad", "Stock actual", "Estado"]], use_container_width=True, hide_index=True)

            view_df = stock_df.copy() if not query.strip() else suggestions.copy()
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Productos visibles", len(view_df))
            with c2:
                st.metric("Stock bajo", int((view_df["Estado"] == "Bajo").sum()) if not view_df.empty else 0)
            with c3:
                st.metric("Agotados", int((view_df["Estado"] == "Agotado").sum()) if not view_df.empty else 0)

            st.dataframe(view_df[["Producto", "Unidad", "Stock actual", "Stock mínimo", "Estado"]], use_container_width=True, hide_index=True)

            producto_options = view_df["Producto"].tolist() if not view_df.empty else []
            if producto_options:
                producto_sel = st.selectbox("Detalle del producto", producto_options)
                producto_row = view_df[view_df["Producto"] == producto_sel].iloc[0]
                producto_id = producto_row["Producto ID"]
                lotes_prod = [l for l in lotes if l.get("producto_id") == producto_id]
                ref_precio = safe_float(producto_row["Precio referencial"])
                metrics = compute_product_metrics(producto_id, lotes, ref_precio)

                d1, d2, d3, d4 = st.columns(4)
                with d1:
                    st.metric("Stock disponible", f"{metrics['stock_total']} {producto_row['Unidad']}")
                with d2:
                    st.metric("Costo promedio", format_bs(metrics["costo_promedio"]))
                with d3:
                    st.metric("Precio referencial", format_bs(ref_precio))
                with d4:
                    st.metric("Margen referencial", f"{metrics['margen_pct_ref']:.2f}%")

                detalle_lotes = []
                for item in lotes_prod:
                    detalle_lotes.append(
                        {
                            "Lote": item.get("lote") or "-",
                            "Cantidad actual": safe_int(item.get("cantidad_actual")),
                            "Costo unitario": format_bs(item.get("costo_unidad")),
                            "Vencimiento": format_dt(item.get("fecha_vencimiento"), with_time=False),
                            "Fecha ingreso": format_dt(item.get("fecha_ingreso")),
                        }
                    )
                if detalle_lotes:
                    st.dataframe(pd.DataFrame(detalle_lotes), use_container_width=True, hide_index=True)

    # ==============================
    # VENTAS
    # ==============================
    elif choice == "🛒 Ventas":
        st.header("Punto de venta")
        productos = fetch_productos()
        clientes = fetch_clientes()
        lotes = fetch_inventario_lotes()

        if not productos:
            st.info("Primero registra productos en el catálogo.")
        else:
            tab1, tab2 = st.tabs(["Nueva venta", "Ventas del periodo"])
            with tab1:
                cnew1, cnew2 = st.columns((1.4, 1))
                with cnew2:
                    with st.expander("➕ Crear cliente rápido"):
                        with st.form("form_cliente_rapido"):
                            n_cliente = st.text_input("Nombre del cliente")
                            t_cliente = st.text_input("Teléfono")
                            ok_confirm = confirm_block("crear este cliente", "confirm_cliente_create")
                            submit = st.form_submit_button("Guardar cliente", use_container_width=True)
                            if submit:
                                if not ok_confirm:
                                    st.warning("Debes confirmar la acción.")
                                else:
                                    try:
                                        _, msg = create_cliente(n_cliente, t_cliente)
                                        set_flash_success(f"✅ {msg}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"No se pudo crear el cliente: {e}")

                with cnew1:
                    prods = {f"{p['nombre']} ({p.get('unidad_medida', 'Unidad')})": p for p in productos}
                    clientes = fetch_clientes()
                    if not clientes:
                        st.warning("Debes crear al menos un cliente antes de vender.")
                    else:
                        client_map = {c['nombre']: c['id'] for c in clientes}
                        p_sel_name = st.selectbox("Producto", list(prods.keys()))
                        p_data = prods[p_sel_name]
                        metrics = compute_product_metrics(p_data["id"], lotes, p_data.get("precio_venta"))
                        unidad = p_data.get("unidad_medida", "Unidad")
                        precio_ref = safe_float(p_data.get("precio_venta"))

                        m1, m2, m3, m4 = st.columns(4)
                        with m1:
                            st.metric("Stock disponible", f"{metrics['stock_total']} {unidad}")
                        with m2:
                            st.metric("Unidad", unidad)
                        with m3:
                            st.metric("Costo promedio", format_bs(metrics["costo_promedio"]))
                        with m4:
                            st.metric("Precio referencial", format_bs(precio_ref))

                        with st.form("f_venta"):
                            cliente_sel = st.selectbox("Cliente", list(client_map.keys()))
                            cantidad = st.number_input(f"Cantidad ({unidad})", min_value=1, step=1)
                            precio_final = st.number_input("Precio unitario final", min_value=0.0, value=precio_ref, step=0.5)
                            met = st.selectbox("Método de pago", ["Efectivo", "QR", "Tarjeta", "Transferencia"])
                            observacion = st.text_input("Observación")

                            total_estimado = cantidad * precio_final
                            margen_pct_final = ((precio_final - metrics["costo_promedio"]) / precio_final) * 100 if precio_final > 0 else 0
                            utilidad_estimada = (precio_final - metrics["costo_promedio"]) * cantidad

                            r1, r2, r3 = st.columns(3)
                            with r1:
                                render_kpi_card("Total estimado", format_bs(total_estimado), "Cantidad x precio final")
                            with r2:
                                render_kpi_card("Margen estimado", f"{margen_pct_final:.2f}%", "Según costo promedio")
                            with r3:
                                render_kpi_card("Utilidad estimada", format_bs(utilidad_estimada), "Antes de confirmar")

                            ok_confirm = confirm_block("registrar esta venta", "confirm_sale_create")
                            submit_venta = st.form_submit_button("Finalizar venta", use_container_width=True)

                        if submit_venta:
                            try:
                                if not ok_confirm:
                                    st.warning("Debes confirmar la acción.")
                                else:
                                    lotes_data = [
                                        l for l in lotes if l.get("producto_id") == p_data["id"] and safe_int(l.get("cantidad_actual")) > 0
                                    ]
                                    lotes_data = sorted(lotes_data, key=lambda x: (str(x.get("fecha_vencimiento") or "9999-12-31"), str(x.get("fecha_ingreso") or "")))
                                    stock_total = sum(safe_int(l["cantidad_actual"]) for l in lotes_data)
                                    if stock_total < cantidad:
                                        st.error(f"Stock insuficiente. Solo hay {stock_total} {unidad} disponibles.")
                                    elif precio_final <= 0:
                                        st.error("El precio final debe ser mayor a cero.")
                                    else:
                                        cliente_id = client_map.get(cliente_sel)
                                        total_v = cantidad * safe_float(precio_final)
                                        venta_insert = supabase.table("ventas").insert(
                                            {
                                                "cliente_id": cliente_id,
                                                "total": total_v,
                                                "metodo_pago": met,
                                                "fecha": datetime.now().isoformat(),
                                                "observacion": observacion,
                                                "estado": "COMPLETADA",
                                            }
                                        ).execute()
                                        venta_data = venta_insert.data or []
                                        if not venta_data:
                                            st.error("No se pudo crear la venta.")
                                        else:
                                            venta_id = venta_data[0]["id"]
                                            pendiente = cantidad
                                            for lote in lotes_data:
                                                if pendiente <= 0:
                                                    break
                                                disponible = safe_int(lote.get("cantidad_actual"))
                                                if disponible <= 0:
                                                    continue
                                                quitar = min(disponible, pendiente)
                                                nuevo_stock = disponible - quitar
                                                supabase.table("detalle_ventas").insert(
                                                    {
                                                        "venta_id": venta_id,
                                                        "producto_id": p_data["id"],
                                                        "lote_id": lote["id"],
                                                        "cantidad": quitar,
                                                        "precio_unitario_aplicado": safe_float(precio_final),
                                                        "costo_unitario_lote": safe_float(lote.get("costo_unidad")),
                                                    }
                                                ).execute()
                                                supabase.table("inventario_lotes").update({"cantidad_actual": nuevo_stock}).eq("id", lote["id"]).execute()
                                                pendiente -= quitar
                                            supabase.table("flujo_caja").insert(
                                                {
                                                    "tipo": "INGRESO",
                                                    "monto": total_v,
                                                    "motivo": f"Venta de {p_data['nombre']}",
                                                    "fecha": datetime.now().isoformat(),
                                                    "categoria": "VENTA",
                                                    "metodo_pago": met,
                                                    "observacion": observacion,
                                                    "venta_id": venta_id,
                                                }
                                            ).execute()
                                            set_flash_success(f"✅ Venta registrada. Total: {format_bs(total_v)} | Cliente: {cliente_sel}")
                                            st.rerun()
                            except Exception as e:
                                st.error(f"No se pudo completar la venta: {e}")

            with tab2:
                ventas = fetch_ventas(start_date, end_date)
                if ventas:
                    rows = []
                    for v in ventas:
                        cliente = (v.get("clientes") or {}).get("nombre", "-")
                        rows.append(
                            {
                                "ID": v.get("id"),
                                "Fecha": format_dt(v.get("fecha")),
                                "Cliente": cliente,
                                "Método": v.get("metodo_pago"),
                                "Total": format_bs(v.get("total")),
                                "Estado": v.get("estado"),
                                "Observación": v.get("observacion") or "",
                            }
                        )
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    ventas_activas = [v for v in ventas if v.get("estado") != "ANULADA"]
                    if ventas_activas:
                        st.markdown("### Anular venta")
                        venta_opts = {}
                        for v in ventas_activas:
                            cliente = (v.get("clientes") or {}).get("nombre", "-")
                            etiqueta = f"{format_dt(v.get('fecha'))} | {cliente} | {format_bs(v.get('total'))}"
                            venta_opts[etiqueta] = v["id"]
                        venta_sel = st.selectbox("Selecciona la venta", list(venta_opts.keys()))
                        ok_confirm = st.checkbox("Confirmo que deseo anular esta venta", key="confirm_sale_cancel")
                        if st.button("Anular venta seleccionada", type="secondary", use_container_width=True):
                            if not ok_confirm:
                                st.warning("Debes confirmar la acción.")
                            else:
                                ok, msg = anular_venta(venta_opts[venta_sel])
                                if ok:
                                    set_flash_success(f"✅ {msg}")
                                    st.rerun()
                                else:
                                    st.error(msg)
                else:
                    st.info("No hay ventas en el rango seleccionado.")

    # ==============================
    # CAJA
    # ==============================
    elif choice == "💰 Caja":
        st.header("Caja y movimientos")
        categorias_caja = fetch_categorias_caja()
        opciones_categorias = [c["nombre"] for c in categorias_caja] if categorias_caja else [
            "VENTA", "OTROS_INGRESOS", "COMPRA_INVENTARIO", "GASOLINA", "SERVICIOS", "ALQUILER", "SUELDOS", "RETIRO", "AJUSTE", "OTROS", "ANULACION_VENTA"
        ]

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
                if submit:
                    if monto <= 0:
                        st.warning("El monto debe ser mayor a cero.")
                    elif not motivo.strip():
                        st.warning("Ingresa un motivo.")
                    elif not ok_confirm:
                        st.warning("Debes confirmar la acción.")
                    else:
                        try:
                            supabase.table("flujo_caja").insert(
                                {
                                    "tipo": tipo,
                                    "monto": monto,
                                    "motivo": motivo.strip(),
                                    "fecha": f"{fecha_mov.isoformat()}T12:00:00",
                                    "categoria": categoria,
                                    "metodo_pago": metodo_pago,
                                    "observacion": observacion.strip(),
                                    "referencia": referencia.strip(),
                                }
                            ).execute()
                            set_flash_success("✅ Movimiento registrado correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo registrar el movimiento: {e}")

        with c2:
            flujo = fetch_flujo_caja(start_date, end_date)
            ing = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "INGRESO")
            egr = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "EGRESO")
            saldo = ing - egr
            k1, k2, k3 = st.columns(3)
            with k1:
                render_kpi_card("Ingresos", format_bs(ing), "Periodo seleccionado")
            with k2:
                render_kpi_card("Egresos", format_bs(egr), "Periodo seleccionado")
            with k3:
                render_kpi_card("Saldo neto", format_bs(saldo), "Ingresos - egresos")

            if flujo:
                flujo_df = pd.DataFrame(flujo)
                resumen_categoria = flujo_df.groupby(["tipo", "categoria"], dropna=False)["monto"].sum().reset_index()
                resumen_categoria["monto"] = resumen_categoria["monto"].apply(format_bs)
                resumen_categoria.columns = ["Tipo", "Categoría", "Monto"]
                st.dataframe(resumen_categoria, use_container_width=True, hide_index=True)

        st.markdown("### Movimientos")
        flujo = fetch_flujo_caja(start_date, end_date)
        if flujo:
            rows = []
            for x in flujo:
                rows.append(
                    {
                        "Fecha": format_dt(x.get("fecha")),
                        "Tipo": x.get("tipo"),
                        "Categoría": x.get("categoria") or "-",
                        "Motivo": x.get("motivo"),
                        "Monto": format_bs(x.get("monto")),
                        "Método": x.get("metodo_pago") or "-",
                        "Observación": x.get("observacion") or "",
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No hay movimientos en el rango seleccionado.")

    # ==============================
    # REPORTES
    # ==============================
    elif choice == "📑 Reportes":
        st.header("Reportes")
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Ventas",
            "Ventas por cliente",
            "Ingresos por producto",
            "Caja",
            "Inventario",
        ])

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
                rows.append(
                    {
                        "Fecha": format_dt(venta.get("fecha")),
                        "Producto": prod.get("nombre", "Sin nombre"),
                        "Unidad": prod.get("unidad_medida", "Unidad"),
                        "Cantidad": cantidad,
                        "Precio unitario": precio,
                        "Ingreso": cantidad * precio,
                        "Costo": cantidad * costo,
                        "Utilidad bruta": (cantidad * precio) - (cantidad * costo),
                        "Método": venta.get("metodo_pago", "-"),
                        "Estado": venta.get("estado", "-"),
                    }
                )
            det_df = pd.DataFrame(rows)
            if not det_df.empty:
                resumen_prod = det_df.groupby(["Producto", "Unidad", "Estado"], as_index=False).agg({"Cantidad": "sum", "Ingreso": "sum", "Costo": "sum", "Utilidad bruta": "sum"})
                resumen_prod["Ingreso"] = resumen_prod["Ingreso"].apply(format_bs)
                resumen_prod["Costo"] = resumen_prod["Costo"].apply(format_bs)
                resumen_prod["Utilidad bruta"] = resumen_prod["Utilidad bruta"].apply(format_bs)
                st.dataframe(resumen_prod, use_container_width=True, hide_index=True)

                view_df = det_df.copy()
                for col in ["Precio unitario", "Ingreso", "Costo", "Utilidad bruta"]:
                    view_df[col] = view_df[col].apply(format_bs)
                st.markdown("### Detalle")
                st.dataframe(view_df, use_container_width=True, hide_index=True)
                st.download_button("Descargar ventas CSV", view_df.to_csv(index=False).encode("utf-8"), file_name=f"reporte_ventas_{start_date}_{end_date}.csv", mime="text/csv")
            else:
                st.info("No hay datos de ventas para este periodo.")

        with tab2:
            ventas = fetch_ventas(start_date, end_date)
            rows = []
            for v in ventas:
                cliente = (v.get("clientes") or {}).get("nombre", "-")
                rows.append(
                    {
                        "Cliente": cliente,
                        "Fecha": format_dt(v.get("fecha")),
                        "Total": safe_float(v.get("total")),
                        "Estado": v.get("estado"),
                    }
                )
            cli_df = pd.DataFrame(rows)
            if not cli_df.empty:
                resumen = cli_df.groupby("Cliente", as_index=False).agg(
                    Compras=("Total", "count"),
                    Total=("Total", "sum"),
                    Ticket_promedio=("Total", "mean"),
                    Ultima_compra=("Fecha", "max"),
                ).sort_values(by="Total", ascending=False)
                resumen["Total"] = resumen["Total"].apply(format_bs)
                resumen["Ticket_promedio"] = resumen["Ticket_promedio"].apply(format_bs)
                st.dataframe(resumen, use_container_width=True, hide_index=True)

                chart_df = cli_df.groupby("Cliente", as_index=False)["Total"].sum().sort_values(by="Total", ascending=False).head(10)
                chart_df.columns = ["Cliente", "Ventas"]
                st.bar_chart(chart_df.set_index("Cliente"))
            else:
                st.info("No hay ventas por cliente en el periodo.")

        with tab3:
            lotes = fetch_inventario_lotes()
            if lotes:
                prod_names = sorted(list({(l.get("productos") or {}).get("nombre", "-") for l in lotes}))
                prod_sel = st.selectbox("Producto", prod_names)
                rows = []
                for l in lotes:
                    prod = l.get("productos") or {}
                    if prod.get("nombre") != prod_sel:
                        continue
                    rows.append(
                        {
                            "Fecha ingreso": format_dt(l.get("fecha_ingreso")),
                            "Fecha eje": pd.to_datetime(parse_iso_to_date(l.get("fecha_ingreso")) or date.today()),
                            "Lote": l.get("lote") or "-",
                            "Cantidad inicial": safe_int(l.get("cantidad_inicial")),
                            "Cantidad actual": safe_int(l.get("cantidad_actual")),
                            "Costo unitario": safe_float(l.get("costo_unidad")),
                            "Vencimiento": format_dt(l.get("fecha_vencimiento"), with_time=False),
                        }
                    )
                ing_df = pd.DataFrame(rows)
                if not ing_df.empty:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Ingresos del producto", len(ing_df))
                    with c2:
                        st.metric("Cantidad ingresada total", int(ing_df["Cantidad inicial"].sum()))
                    with c3:
                        st.metric("Costo promedio ingresos", format_bs(ing_df["Costo unitario"].mean()))

                    trend_df = ing_df.sort_values(by="Fecha eje")[["Fecha eje", "Costo unitario"]].set_index("Fecha eje")
                    st.line_chart(trend_df)

                    view_df = ing_df.copy()
                    view_df["Costo unitario"] = view_df["Costo unitario"].apply(format_bs)
                    view_df = view_df.drop(columns=["Fecha eje"])
                    st.dataframe(view_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay ingresos para este producto.")
            else:
                st.info("No hay inventario registrado.")

        with tab4:
            flujo = fetch_flujo_caja(start_date, end_date)
            if flujo:
                flujo_df = pd.DataFrame(flujo)
                ingreso_total = flujo_df.loc[flujo_df["tipo"] == "INGRESO", "monto"].sum() if "tipo" in flujo_df.columns else 0
                egreso_total = flujo_df.loc[flujo_df["tipo"] == "EGRESO", "monto"].sum() if "tipo" in flujo_df.columns else 0
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Ingresos", format_bs(ingreso_total))
                with c2:
                    st.metric("Egresos", format_bs(egreso_total))
                with c3:
                    st.metric("Balance", format_bs(ingreso_total - egreso_total))
                resumen = flujo_df.groupby(["tipo", "categoria"], as_index=False)["monto"].sum()
                resumen["monto"] = resumen["monto"].apply(format_bs)
                resumen.columns = ["Tipo", "Categoría", "Monto"]
                st.dataframe(resumen, use_container_width=True, hide_index=True)
            else:
                st.info("No hay movimientos para este periodo.")

        with tab5:
            lotes = fetch_inventario_lotes()
            if lotes:
                stock_df = build_stock_summary(lotes)
                if not stock_df.empty:
                    st.dataframe(stock_df[["Producto", "Unidad", "Stock actual", "Stock mínimo", "Estado"]], use_container_width=True, hide_index=True)
                rows = []
                for item in lotes:
                    prod = item.get("productos") or {}
                    cantidad = safe_int(item.get("cantidad_actual"))
                    costo = safe_float(item.get("costo_unidad"))
                    rows.append(
                        {
                            "Producto": prod.get("nombre", "Sin nombre"),
                            "Lote": item.get("lote") or "-",
                            "Cantidad actual": cantidad,
                            "Costo unitario": format_bs(costo),
                            "Valor stock": format_bs(cantidad * costo),
                            "Vencimiento": format_dt(item.get("fecha_vencimiento"), with_time=False),
                        }
                    )
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No hay inventario registrado.")

    # ==============================
    # IMPORTACION MASIVA
    # ==============================
    elif choice == "📤 Importación masiva":
        st.header("Importación masiva de inventario")
        st.caption("Columnas recomendadas: categoria, producto, cantidad, costo_unitario, unidad_medida, lote, fecha_vencimiento")
        st.info(f"Si falta fecha_vencimiento, el sistema usará {DEFAULT_EXPIRY_DATE} de forma provisional.")
        archivo = st.file_uploader("Sube tu Excel o CSV", type=["xlsx", "csv"])
        if archivo is not None:
            try:
                if archivo.name.lower().endswith(".csv"):
                    df = pd.read_csv(archivo)
                else:
                    df = pd.read_excel(archivo)
                df.columns = [str(c).strip().lower() for c in df.columns]
                required = {"categoria", "producto", "cantidad"}
                missing = required - set(df.columns)
                if missing:
                    st.error(f"Faltan columnas obligatorias: {', '.join(sorted(missing))}")
                else:
                    for col in ["costo_unitario", "unidad_medida", "lote", "fecha_vencimiento"]:
                        if col not in df.columns:
                            df[col] = "" if col in ["unidad_medida", "lote", "fecha_vencimiento"] else 0
                    preview = df.copy()
                    preview["unidad_medida"] = preview["unidad_medida"].replace("", "Unidad")
                    preview["fecha_vencimiento"] = preview["fecha_vencimiento"].replace("", DEFAULT_EXPIRY_DATE)
                    preview["costo_unitario"] = preview["costo_unitario"].fillna(0)
                    st.markdown("### Vista previa")
                    st.dataframe(preview, use_container_width=True, hide_index=True)
                    st.caption(f"Filas detectadas: {len(preview)}")
                    ok_confirm = st.checkbox("Confirmo que deseo importar este archivo", key="confirm_mass_import")
                    if st.button("Importar inventario", use_container_width=True):
                        if not ok_confirm:
                            st.warning("Debes confirmar la importación.")
                        else:
                            created = import_inventory_from_dataframe(preview)
                            set_flash_success(f"✅ Importación completada. Filas procesadas: {created}")
                            st.rerun()
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")
