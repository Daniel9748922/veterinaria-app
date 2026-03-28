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
                padding-top: 1.2rem;
                padding-bottom: 2rem;
            }
            .kpi-card {
                background: white;
                border-radius: 18px;
                padding: 18px 18px 14px 18px;
                box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
                border: 1px solid rgba(226, 232, 240, 0.8);
                margin-bottom: 10px;
            }
            .kpi-label {
                font-size: 0.9rem;
                color: #64748b;
                margin-bottom: 8px;
            }
            .kpi-value {
                font-size: 1.8rem;
                font-weight: 700;
                color: #0f172a;
                line-height: 1.1;
            }
            .kpi-delta {
                font-size: 0.85rem;
                color: #475569;
                margin-top: 8px;
            }
            .stMetric {
                background: white;
                border: 1px solid rgba(226, 232, 240, 0.8);
                padding: 10px;
                border-radius: 14px;
                box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
            }
            div[data-testid="stDataFrame"] {
                border-radius: 14px;
                overflow: hidden;
                border: 1px solid rgba(226, 232, 240, 0.8);
            }
            .small-muted {
                color: #64748b;
                font-size: 0.92rem;
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
    start_ts = f"{start_date.isoformat()}T00:00:00"
    end_ts = f"{end_date.isoformat()}T23:59:59"
    return start_ts, end_ts


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
    res = supabase.table("categorias").select("id, nombre").order("nombre").execute()
    return res.data or []


def fetch_productos():
    res = (
        supabase.table("productos")
        .select("id, nombre, descripcion, precio_venta, unidad_medida, stock_minimo, categoria_id, categorias(nombre)")
        .order("nombre")
        .execute()
    )
    return res.data or []


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
            "id, venta_id, producto_id, lote_id, cantidad, precio_unitario_aplicado, costo_unitario_lote, ventas(fecha, metodo_pago, total), productos(nombre, unidad_medida)"
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
    res = (
        supabase.table("inventario_lotes")
        .select(
            "id, producto_id, lote, cantidad_actual, cantidad_inicial, costo_unidad, fecha_vencimiento, fecha_ingreso, productos(nombre, unidad_medida, stock_minimo, precio_venta)"
        )
        .order("fecha_vencimiento")
        .execute()
    )
    return res.data or []


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

        grouped.setdefault(
            producto_id,
            {
                "Producto ID": producto_id,
                "Producto": producto,
                "Unidad": unidad,
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

    if stock_total > 0:
        costo_total = sum(safe_int(l.get("cantidad_actual")) * safe_float(l.get("costo_unidad")) for l in lotes_prod)
        costo_promedio = costo_total / stock_total
    else:
        costo_promedio = 0

    margen_pct_ref = 0
    precio_ref = safe_float(precio_referencia)
    if precio_ref > 0:
        margen_pct_ref = ((precio_ref - costo_promedio) / precio_ref) * 100 if precio_ref else 0

    return {
        "stock_total": stock_total,
        "costo_promedio": costo_promedio,
        "margen_pct_ref": margen_pct_ref,
    }


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

    st.title("🐾 VetControl Pro")
    st.caption("Control de ventas, inventario, caja y reportes en una sola vista")

    menu = [
        "📊 Dashboard",
        "📦 Catálogo",
        "📥 Entradas",
        "📦 Stock",
        "🛒 Ventas",
        "💰 Caja",
        "📑 Reportes",
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

        ingresos = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "INGRESO")
        egresos = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "EGRESO")
        saldo_neto = ingresos - egresos
        total_ventas = sum(safe_float(v.get("total")) for v in ventas if v.get("estado") != "ANULADA")
        cantidad_ventas = len([v for v in ventas if v.get("estado") != "ANULADA"])
        ticket_promedio = total_ventas / cantidad_ventas if cantidad_ventas else 0

        stock_df = build_stock_summary(lotes)
        stock_bajo = 0
        agotados = 0
        if not stock_df.empty:
            stock_bajo = int((stock_df["Estado"] == "Bajo").sum())
            agotados = int((stock_df["Estado"] == "Agotado").sum())

        por_vencer = []
        for item in lotes:
            prod = item.get("productos") or {}
            venc = parse_iso_to_date(item.get("fecha_vencimiento"))
            if not venc:
                continue
            dias = (venc - date.today()).days
            if safe_int(item.get("cantidad_actual")) > 0 and dias <= 30:
                por_vencer.append(
                    {
                        "Producto": prod.get("nombre", "Sin nombre"),
                        "Lote": item.get("lote") or "-",
                        "Stock": safe_int(item.get("cantidad_actual")),
                        "Vence": venc,
                        "Días": dias,
                    }
                )
        por_vencer_df = pd.DataFrame(por_vencer).sort_values(by="Días") if por_vencer else pd.DataFrame()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_kpi_card("Ventas del periodo", format_bs(total_ventas), f"{cantidad_ventas} venta(s)")
        with c2:
            render_kpi_card("Ingresos", format_bs(ingresos), "Incluye ventas y otros ingresos")
        with c3:
            render_kpi_card("Egresos", format_bs(egresos), "Compras y gastos operativos")
        with c4:
            render_kpi_card("Saldo neto", format_bs(saldo_neto), f"Ticket promedio: {format_bs(ticket_promedio)}")

        c5, c6, c7 = st.columns(3)
        with c5:
            st.metric("Productos con stock bajo", stock_bajo)
        with c6:
            st.metric("Productos agotados", agotados)
        with c7:
            st.metric("Lotes por vencer (30 días)", len(por_vencer))

        left, right = st.columns((1.4, 1))
        with left:
            st.markdown("### Evolución de ventas")
            ventas_validas = [v for v in ventas if v.get("estado") != "ANULADA"]
            if ventas_validas:
                ventas_df = pd.DataFrame(ventas_validas)
                ventas_df["fecha"] = pd.to_datetime(ventas_df["fecha"])
                ventas_por_dia = ventas_df.groupby(ventas_df["fecha"].dt.date)["total"].sum().reset_index()
                ventas_por_dia.columns = ["Fecha", "Ventas"]
                st.line_chart(ventas_por_dia.set_index("Fecha"))
            else:
                st.info("No hay ventas en el rango seleccionado.")

        with right:
            st.markdown("### Ventas por método de pago")
            ventas_validas = [v for v in ventas if v.get("estado") != "ANULADA"]
            if ventas_validas:
                ventas_metodo_df = pd.DataFrame(ventas_validas)
                ventas_metodo = ventas_metodo_df.groupby("metodo_pago")["total"].sum().reset_index()
                ventas_metodo.columns = ["Método de pago", "Ventas"]
                st.bar_chart(ventas_metodo.set_index("Método de pago"))
            else:
                st.info("No hay datos para mostrar.")

        a1, a2 = st.columns(2)
        with a1:
            st.markdown("### Top productos vendidos")
            if detalles:
                rows = []
                for d in detalles:
                    prod = d.get("productos") or {}
                    rows.append(
                        {
                            "Producto": prod.get("nombre", "Sin nombre"),
                            "Cantidad": safe_int(d.get("cantidad")),
                            "Ingreso": safe_int(d.get("cantidad")) * safe_float(d.get("precio_unitario_aplicado")),
                        }
                    )
                top_df = pd.DataFrame(rows)
                top_df = (
                    top_df.groupby("Producto", as_index=False)
                    .agg({"Cantidad": "sum", "Ingreso": "sum"})
                    .sort_values(by="Ingreso", ascending=False)
                    .head(10)
                )
                top_df["Ingreso"] = top_df["Ingreso"].apply(format_bs)
                st.dataframe(top_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aún no hay detalle de ventas para este rango.")

        with a2:
            st.markdown("### Alertas de inventario")
            if not stock_df.empty:
                alertas_df = stock_df[stock_df["Estado"].isin(["Bajo", "Agotado"])].copy()
                if alertas_df.empty:
                    st.success("No hay alertas de stock en este momento.")
                else:
                    st.dataframe(alertas_df[["Producto", "Unidad", "Stock actual", "Stock mínimo", "Estado"]], use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos de inventario.")

        st.markdown("### Productos por vencer")
        if not por_vencer_df.empty:
            st.dataframe(por_vencer_df, use_container_width=True, hide_index=True)
        else:
            st.success("No hay productos por vencer en los próximos 30 días.")

    # ==============================
    # CATALOGO
    # ==============================
    elif choice == "📦 Catálogo":
        st.header("Gestión de categorías y productos")
        tab1, tab2, tab3, tab4 = st.tabs(["Crear categoría", "Editar categoría", "Crear producto", "Editar producto"])

        categorias = fetch_categorias()

        with tab1:
            with st.form("form_categoria", clear_on_submit=True):
                n_cat = st.text_input("Nombre de la categoría")
                submit_cat = st.form_submit_button("Crear categoría", use_container_width=True)
                if submit_cat:
                    if not n_cat.strip():
                        st.warning("Ingresa un nombre de categoría.")
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
                cat_name = st.selectbox("Categoría a editar", list(cat_map.keys()))
                cat_item = cat_map[cat_name]
                nuevo_nombre = st.text_input("Nuevo nombre", value=cat_item["nombre"], key="edit_cat_name")
                if st.button("Guardar cambios categoría", use_container_width=True):
                    if not nuevo_nombre.strip():
                        st.warning("El nombre no puede estar vacío.")
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
                with st.form("form_producto", clear_on_submit=True):
                    sel_c = st.selectbox("Categoría", list(cats.keys()))
                    n_p = st.text_input("Nombre del producto")
                    desc_p = st.text_area("Descripción")
                    u_m = st.selectbox("Unidad de medida", ["Unidad", "Kg", "Gr", "Ml", "Lt", "Tabletas", "Caja", "Frasco"])
                    p_v = st.number_input("Precio de venta referencial", min_value=0.0, step=0.5)
                    s_min = st.number_input("Stock mínimo", min_value=0, value=5, step=1)
                    submit_prod = st.form_submit_button("Crear producto", use_container_width=True)
                    if submit_prod:
                        if not n_p.strip():
                            st.warning("Ingresa el nombre del producto.")
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
                prod_name = st.selectbox("Producto a editar", list(prod_map.keys()))
                prod_item = prod_map[prod_name]
                categorias = fetch_categorias()
                cats = {c["nombre"]: c["id"] for c in categorias}
                categoria_actual = None
                for nombre_cat, id_cat in cats.items():
                    if id_cat == prod_item.get("categoria_id"):
                        categoria_actual = nombre_cat
                        break
                idx_cat = list(cats.keys()).index(categoria_actual) if categoria_actual in cats else 0

                with st.form("form_edit_producto"):
                    new_cat = st.selectbox("Categoría", list(cats.keys()), index=idx_cat)
                    new_nombre = st.text_input("Nombre", value=prod_item.get("nombre", ""))
                    new_desc = st.text_area("Descripción", value=prod_item.get("descripcion", ""))
                    unidades = ["Unidad", "Kg", "Gr", "Ml", "Lt", "Tabletas", "Caja", "Frasco"]
                    unidad_actual = prod_item.get("unidad_medida", "Unidad")
                    idx_unidad = unidades.index(unidad_actual) if unidad_actual in unidades else 0
                    new_unidad = st.selectbox("Unidad de medida", unidades, index=idx_unidad)
                    new_precio = st.number_input("Precio de venta referencial", min_value=0.0, value=safe_float(prod_item.get("precio_venta")), step=0.5)
                    new_stock_min = st.number_input("Stock mínimo", min_value=0, value=safe_int(prod_item.get("stock_minimo")), step=1)
                    submit_edit = st.form_submit_button("Guardar cambios producto", use_container_width=True)
                    if submit_edit:
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
        st.header("Entrada de stock")
        productos = fetch_productos()
        if not productos:
            st.info("Primero registra productos.")
        else:
            prods = {f"{p['nombre']} ({p.get('unidad_medida', 'Unidad')})": p for p in productos}
            with st.form("f_ent", clear_on_submit=True):
                p_sel = st.selectbox("Producto", list(prods.keys()))
                lote_txt = st.text_input("Lote")
                ca = st.number_input("Cantidad", min_value=1, step=1)
                co = st.number_input("Costo unitario", min_value=0.0, step=0.5)
                ve = st.date_input("Fecha de vencimiento")
                metodo_pago = st.selectbox("Método de pago", ["Efectivo", "QR", "Tarjeta", "Transferencia", "Otro"])
                observacion = st.text_input("Observación")
                submit_ent = st.form_submit_button("Registrar entrada", use_container_width=True)

                if submit_ent:
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

        st.markdown("### Lotes registrados")
        lotes = fetch_inventario_lotes()
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
                        "Vencimiento": item.get("fecha_vencimiento"),
                        "Ingreso": item.get("fecha_ingreso"),
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
            buscador = st.text_input("Buscar producto")
            view_df = stock_df.copy()
            if buscador.strip():
                mask = view_df["Producto"].str.contains(buscador.strip(), case=False, na=False)
                view_df = view_df[mask]

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Productos con stock", len(view_df))
            with c2:
                st.metric("Stock bajo", int((view_df["Estado"] == "Bajo").sum()))
            with c3:
                st.metric("Agotados", int((view_df["Estado"] == "Agotado").sum()))

            st.dataframe(view_df[["Producto", "Unidad", "Stock actual", "Stock mínimo", "Estado"]], use_container_width=True, hide_index=True)

            producto_options = view_df["Producto"].tolist()
            if producto_options:
                producto_sel = st.selectbox("Ver detalle de producto", producto_options)
                producto_row = view_df[view_df["Producto"] == producto_sel].iloc[0]
                producto_id = producto_row["Producto ID"]
                lotes_prod = [l for l in lotes if l.get("producto_id") == producto_id]
                ref_precio = 0
                for l in lotes_prod:
                    prod = l.get("productos") or {}
                    ref_precio = safe_float(prod.get("precio_venta"))
                    if ref_precio > 0:
                        break
                metrics = compute_product_metrics(producto_id, lotes, ref_precio)
                st.markdown("### Detalle del producto")
                d1, d2, d3, d4 = st.columns(4)
                with d1:
                    st.metric("Stock disponible", f"{metrics['stock_total']} {producto_row['Unidad']}")
                with d2:
                    st.metric("Costo promedio ponderado", format_bs(metrics["costo_promedio"]))
                with d3:
                    st.metric("Precio venta referencial", format_bs(ref_precio))
                with d4:
                    st.metric("Margen referencial", f"{metrics['margen_pct_ref']:.2f}%")

                detalle_lotes = []
                for item in lotes_prod:
                    detalle_lotes.append(
                        {
                            "Lote": item.get("lote") or "-",
                            "Cantidad actual": safe_int(item.get("cantidad_actual")),
                            "Costo unitario": format_bs(item.get("costo_unidad")),
                            "Vencimiento": item.get("fecha_vencimiento"),
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
            prods = {f"{p['nombre']} ({p.get('unidad_medida', 'Unidad')})": p for p in productos}
            client_map = {c['nombre']: c['id'] for c in clientes} if clientes else {}
            client_names = ["Venta rápida / Sin cliente"] + list(client_map.keys())

            p_sel_name = st.selectbox("Producto", list(prods.keys()))
            p_data = prods[p_sel_name]
            metrics = compute_product_metrics(p_data["id"], lotes, p_data.get("precio_venta"))
            unidad = p_data.get("unidad_medida", "Unidad")
            precio_ref = safe_float(p_data.get("precio_venta"))

            cinfo1, cinfo2, cinfo3, cinfo4 = st.columns(4)
            with cinfo1:
                st.metric("Stock disponible", f"{metrics['stock_total']} {unidad}")
            with cinfo2:
                st.metric("Unidad", unidad)
            with cinfo3:
                st.metric("Costo promedio", format_bs(metrics["costo_promedio"]))
            with cinfo4:
                st.metric("Precio referencial", format_bs(precio_ref))

            with st.form("f_venta"):
                cliente_sel = st.selectbox("Cliente", client_names)
                c_venda = st.number_input(f"Cantidad ({unidad})", min_value=1, step=1)
                precio_final = st.number_input("Precio unitario final", min_value=0.0, value=precio_ref, step=0.5)
                met = st.selectbox("Método de pago", ["Efectivo", "QR", "Tarjeta", "Transferencia"])
                observacion = st.text_input("Observación")

                total_estimado = c_venda * precio_final
                margen_pct_final = ((precio_final - metrics["costo_promedio"]) / precio_final) * 100 if precio_final > 0 else 0
                utilidad_estimada = (precio_final - metrics["costo_promedio"]) * c_venda

                st.markdown(f"**Total estimado:** {format_bs(total_estimado)}")
                st.markdown(f"**Margen estimado:** {margen_pct_final:.2f}%")
                st.markdown(f"**Utilidad estimada:** {format_bs(utilidad_estimada)}")

                submit_venta = st.form_submit_button("Finalizar venta", use_container_width=True)

            if submit_venta:
                try:
                    lotes_data = [
                        l for l in lotes
                        if l.get("producto_id") == p_data["id"] and safe_int(l.get("cantidad_actual")) > 0
                    ]
                    lotes_data = sorted(lotes_data, key=lambda x: (str(x.get("fecha_vencimiento") or "9999-12-31"), str(x.get("fecha_ingreso") or "")))
                    stock_total = sum(safe_int(l["cantidad_actual"]) for l in lotes_data)

                    if stock_total < c_venda:
                        st.error(f"Stock insuficiente. Solo hay {stock_total} {unidad} disponibles.")
                    elif precio_final <= 0:
                        st.error("El precio final debe ser mayor a cero.")
                    else:
                        cliente_id = None if cliente_sel == "Venta rápida / Sin cliente" else client_map.get(cliente_sel)
                        total_v = c_venda * safe_float(precio_final)

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
                            pendiente = c_venda
                            detalles_insertados = 0

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
                                detalles_insertados += 1
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

                            set_flash_success(
                                f"✅ Venta registrada. Total: {format_bs(total_v)} | Cliente: {cliente_sel} | Detalles: {detalles_insertados}"
                            )
                            st.rerun()

                except Exception as e:
                    st.error(f"No se pudo completar la venta: {e}")

        st.markdown("### Historial de ventas")
        ventas = fetch_ventas(start_date, end_date)
        if ventas:
            rows = []
            for v in ventas:
                cliente = (v.get("clientes") or {}).get("nombre", "Venta rápida")
                rows.append(
                    {
                        "ID": v.get("id"),
                        "Fecha": v.get("fecha"),
                        "Cliente": cliente,
                        "Método de pago": v.get("metodo_pago"),
                        "Total": format_bs(v.get("total")),
                        "Estado": v.get("estado"),
                        "Observación": v.get("observacion") or "",
                    }
                )
            ventas_df = pd.DataFrame(rows)
            st.dataframe(ventas_df, use_container_width=True, hide_index=True)

            st.markdown("### Anular venta")
            ventas_activas = [v for v in ventas if v.get("estado") != "ANULADA"]
            if ventas_activas:
                venta_opts = {}
                for v in ventas_activas:
                    cliente = (v.get("clientes") or {}).get("nombre", "Venta rápida")
                    etiqueta = f"{str(v.get('fecha'))[:19]} | {cliente} | {format_bs(v.get('total'))}"
                    venta_opts[etiqueta] = v["id"]
                venta_sel = st.selectbox("Selecciona la venta a anular", list(venta_opts.keys()))
                if st.button("Anular venta seleccionada", type="secondary", use_container_width=True):
                    ok, msg = anular_venta(venta_opts[venta_sel])
                    if ok:
                        set_flash_success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.info("No hay ventas activas para anular en el rango seleccionado.")
        else:
            st.info("No hay ventas en el rango seleccionado.")

    # ==============================
    # CAJA
    # ==============================
    elif choice == "💰 Caja":
        st.header("Caja y movimientos")

        categorias_caja = fetch_categorias_caja()
        opciones_categorias = [c["nombre"] for c in categorias_caja] if categorias_caja else [
            "VENTA",
            "OTROS_INGRESOS",
            "COMPRA_INVENTARIO",
            "GASOLINA",
            "SERVICIOS",
            "ALQUILER",
            "SUELDOS",
            "RETIRO",
            "AJUSTE",
            "OTROS",
            "ANULACION_VENTA",
        ]

        c1, c2 = st.columns((1, 1.4))
        with c1:
            st.subheader("Registrar movimiento")
            with st.form("form_caja", clear_on_submit=True):
                tipo = st.selectbox("Tipo", ["INGRESO", "EGRESO"])
                categoria = st.selectbox("Categoría", opciones_categorias)
                monto = st.number_input("Monto", min_value=0.0, step=0.5)
                fecha_mov = st.date_input("Fecha del movimiento", value=date.today())
                metodo_pago = st.selectbox("Método de pago", ["Efectivo", "QR", "Tarjeta", "Transferencia", "Otro"])
                motivo = st.text_input("Motivo")
                observacion = st.text_area("Observación")
                referencia = st.text_input("Referencia")
                submit_mov = st.form_submit_button("Guardar movimiento", use_container_width=True)

                if submit_mov:
                    if monto <= 0:
                        st.warning("El monto debe ser mayor a cero.")
                    elif not motivo.strip():
                        st.warning("Ingresa un motivo para el movimiento.")
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
            st.subheader("Resumen del periodo")
            flujo = fetch_flujo_caja(start_date, end_date)
            ing = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "INGRESO")
            egr = sum(safe_float(x.get("monto")) for x in flujo if x.get("tipo") == "EGRESO")
            saldo = ing - egr

            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Ingresos", format_bs(ing))
            with k2:
                st.metric("Egresos", format_bs(egr))
            with k3:
                st.metric("Saldo neto", format_bs(saldo))

            if flujo:
                flujo_df = pd.DataFrame(flujo)
                if "categoria" in flujo_df.columns:
                    st.markdown("#### Resumen por categoría")
                    resumen_categoria = flujo_df.groupby(["tipo", "categoria"], dropna=False)["monto"].sum().reset_index()
                    resumen_categoria["monto"] = resumen_categoria["monto"].apply(format_bs)
                    resumen_categoria.columns = ["Tipo", "Categoría", "Monto"]
                    st.dataframe(resumen_categoria, use_container_width=True, hide_index=True)
            else:
                st.info("No hay movimientos en el rango seleccionado.")

        st.markdown("### Movimientos")
        flujo = fetch_flujo_caja(start_date, end_date)
        if flujo:
            flujo_df = pd.DataFrame(flujo)
            flujo_df["monto"] = flujo_df["monto"].apply(format_bs)
            flujo_df = flujo_df.rename(
                columns={
                    "fecha": "Fecha",
                    "tipo": "Tipo",
                    "categoria": "Categoría",
                    "motivo": "Motivo",
                    "monto": "Monto",
                    "metodo_pago": "Método de pago",
                    "observacion": "Observación",
                    "referencia": "Referencia",
                }
            )
            cols = [c for c in ["Fecha", "Tipo", "Categoría", "Motivo", "Monto", "Método de pago", "Observación", "Referencia"] if c in flujo_df.columns]
            st.dataframe(flujo_df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No hay movimientos registrados.")

    # ==============================
    # REPORTES
    # ==============================
    elif choice == "📑 Reportes":
        st.header("Reportes")
        tab1, tab2, tab3 = st.tabs(["Ventas", "Caja", "Inventario"])

        with tab1:
            ventas = fetch_ventas(start_date, end_date)
            ventas = [v for v in ventas if v.get("estado") != "ANULADA"]
            detalles = fetch_detalle_ventas_con_producto(start_date, end_date)

            total_ventas = sum(safe_float(v.get("total")) for v in ventas)
            cantidad_ventas = len(ventas)
            ticket_promedio = total_ventas / cantidad_ventas if cantidad_ventas else 0

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total vendido", format_bs(total_ventas))
            with c2:
                st.metric("Cantidad de ventas", cantidad_ventas)
            with c3:
                st.metric("Ticket promedio", format_bs(ticket_promedio))

            if detalles:
                rows = []
                for d in detalles:
                    venta = d.get("ventas") or {}
                    if venta and venta.get("total") is None:
                        continue
                    prod = d.get("productos") or {}
                    cantidad = safe_int(d.get("cantidad"))
                    precio = safe_float(d.get("precio_unitario_aplicado"))
                    costo = safe_float(d.get("costo_unitario_lote"))
                    rows.append(
                        {
                            "Fecha": venta.get("fecha"),
                            "Producto": prod.get("nombre", "Sin nombre"),
                            "Unidad": prod.get("unidad_medida", "Unidad"),
                            "Cantidad": cantidad,
                            "Precio unitario": precio,
                            "Ingreso": cantidad * precio,
                            "Costo": cantidad * costo,
                            "Utilidad bruta": (cantidad * precio) - (cantidad * costo),
                            "Método de pago": venta.get("metodo_pago", "-"),
                        }
                    )
                det_df = pd.DataFrame(rows)
                if not det_df.empty:
                    st.markdown("#### Resumen por producto")
                    resumen_prod = (
                        det_df.groupby(["Producto", "Unidad"], as_index=False)
                        .agg({"Cantidad": "sum", "Ingreso": "sum", "Costo": "sum", "Utilidad bruta": "sum"})
                        .sort_values(by="Ingreso", ascending=False)
                    )
                    resumen_prod["Ingreso"] = resumen_prod["Ingreso"].apply(format_bs)
                    resumen_prod["Costo"] = resumen_prod["Costo"].apply(format_bs)
                    resumen_prod["Utilidad bruta"] = resumen_prod["Utilidad bruta"].apply(format_bs)
                    st.dataframe(resumen_prod, use_container_width=True, hide_index=True)

                    st.markdown("#### Detalle de ventas")
                    view_df = det_df.copy()
                    for col in ["Precio unitario", "Ingreso", "Costo", "Utilidad bruta"]:
                        view_df[col] = view_df[col].apply(format_bs)
                    st.dataframe(view_df, use_container_width=True, hide_index=True)

                    csv = view_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Descargar reporte de ventas (CSV)",
                        data=csv,
                        file_name=f"reporte_ventas_{start_date}_{end_date}.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No hay detalle de ventas para este periodo.")
            else:
                st.info("No hay datos de ventas para este periodo.")

        with tab2:
            flujo = fetch_flujo_caja(start_date, end_date)
            if flujo:
                flujo_df = pd.DataFrame(flujo)
                ingreso_total = flujo_df.loc[flujo_df["tipo"] == "INGRESO", "monto"].sum() if "tipo" in flujo_df.columns else 0
                egreso_total = flujo_df.loc[flujo_df["tipo"] == "EGRESO", "monto"].sum() if "tipo" in flujo_df.columns else 0
                balance = ingreso_total - egreso_total

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Ingresos", format_bs(ingreso_total))
                with c2:
                    st.metric("Egresos", format_bs(egreso_total))
                with c3:
                    st.metric("Balance", format_bs(balance))

                if "categoria" in flujo_df.columns:
                    st.markdown("#### Agrupado por categoría")
                    resumen = flujo_df.groupby(["tipo", "categoria"], as_index=False)["monto"].sum()
                    resumen["monto"] = resumen["monto"].apply(format_bs)
                    resumen.columns = ["Tipo", "Categoría", "Monto"]
                    st.dataframe(resumen, use_container_width=True, hide_index=True)

                st.markdown("#### Detalle de movimientos")
                det_mov = flujo_df.copy()
                det_mov["monto"] = det_mov["monto"].apply(format_bs)
                st.dataframe(det_mov, use_container_width=True, hide_index=True)

                csv = det_mov.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Descargar reporte de caja (CSV)",
                    data=csv,
                    file_name=f"reporte_caja_{start_date}_{end_date}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No hay movimientos para este periodo.")

        with tab3:
            lotes = fetch_inventario_lotes()
            if lotes:
                stock_df = build_stock_summary(lotes)
                if not stock_df.empty:
                    st.markdown("#### Stock consolidado")
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
                            "Vencimiento": item.get("fecha_vencimiento"),
                        }
                    )
                st.markdown("#### Detalle por lotes")
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No hay inventario registrado.")
