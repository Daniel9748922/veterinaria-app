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
            .section-card {
                background: white;
                border-radius: 18px;
                padding: 18px;
                box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
                border: 1px solid rgba(226, 232, 240, 0.8);
                margin-bottom: 14px;
            }
            .small-muted {
                color: #64748b;
                font-size: 0.9rem;
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


def fetch_categorias():
    res = supabase.table("categorias").select("id, nombre").order("nombre").execute()
    return res.data or []


def fetch_productos():
    res = (
        supabase.table("productos")
        .select("id, nombre, precio_venta, unidad_medida, stock_minimo, categoria_id")
        .order("nombre")
        .execute()
    )
    return res.data or []


def fetch_ventas(start_date=None, end_date=None):
    query = supabase.table("ventas").select("*").order("fecha", desc=True)
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


def fetch_inventario_lotes():
    res = (
        supabase.table("inventario_lotes")
        .select(
            "id, producto_id, cantidad_actual, cantidad_inicial, costo_unidad, fecha_vencimiento, fecha_ingreso, productos(nombre, unidad_medida, stock_minimo)"
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


def build_stock_summary(lotes_data):
    rows = []
    grouped = {}

    for item in lotes_data:
        prod = item.get("productos") or {}
        producto = prod.get("nombre", "Sin nombre")
        unidad = prod.get("unidad_medida", "Unidad")
        stock_minimo = safe_int(prod.get("stock_minimo", 0))
        cantidad_actual = safe_int(item.get("cantidad_actual", 0))
        grouped.setdefault(
            producto,
            {
                "Producto": producto,
                "Unidad": unidad,
                "Stock actual": 0,
                "Stock mínimo": stock_minimo,
            },
        )
        grouped[producto]["Stock actual"] += cantidad_actual

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


# ==============================
# APP PRINCIPAL
# ==============================
if check_password():
    inject_css()

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
        total_ventas = sum(safe_float(v.get("total")) for v in ventas)
        cantidad_ventas = len(ventas)
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
                        "Lote": item.get("id"),
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
            render_kpi_card("Ingresos", format_bs(ingresos), f"Incluye ventas y otros ingresos")
        with c3:
            render_kpi_card("Egresos", format_bs(egresos), f"Compras y gastos operativos")
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
            if ventas:
                ventas_df = pd.DataFrame(ventas)
                ventas_df["fecha"] = pd.to_datetime(ventas_df["fecha"])
                ventas_por_dia = ventas_df.groupby(ventas_df["fecha"].dt.date)["total"].sum().reset_index()
                ventas_por_dia.columns = ["Fecha", "Ventas"]
                st.line_chart(ventas_por_dia.set_index("Fecha"))
            else:
                st.info("No hay ventas en el rango seleccionado.")

        with right:
            st.markdown("### Ventas por método de pago")
            if ventas:
                ventas_metodo_df = pd.DataFrame(ventas)
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
                    st.dataframe(alertas_df, use_container_width=True, hide_index=True)
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
        st.header("Gestión de productos")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Nueva categoría")
            with st.form("form_categoria", clear_on_submit=True):
                n_cat = st.text_input("Nombre de la categoría")
                submit_cat = st.form_submit_button("Crear categoría", use_container_width=True)
                if submit_cat:
                    if not n_cat.strip():
                        st.warning("Ingresa un nombre de categoría.")
                    else:
                        try:
                            supabase.table("categorias").insert({"nombre": n_cat.strip()}).execute()
                            st.success("Categoría creada correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo crear la categoría: {e}")

        with col2:
            st.subheader("Nuevo producto")
            categorias = fetch_categorias()
            if not categorias:
                st.info("Primero crea al menos una categoría.")
            else:
                cats = {c["nombre"]: c["id"] for c in categorias}
                with st.form("form_producto", clear_on_submit=True):
                    sel_c = st.selectbox("Categoría", list(cats.keys()))
                    n_p = st.text_input("Nombre del producto")
                    desc_p = st.text_area("Descripción")
                    u_m = st.selectbox("Unidad de medida", ["Unidad", "Kg", "Gr", "Ml", "Lt", "Tabletas", "Caja", "Frasco"])
                    p_v = st.number_input("Precio de venta", min_value=0.0, step=0.5)
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
                                st.success("Producto creado con éxito.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"No se pudo crear el producto: {e}")

        st.markdown("### Catálogo actual")
        productos = fetch_productos()
        if productos:
            df_prod = pd.DataFrame(productos)
            df_prod["precio_venta"] = df_prod["precio_venta"].apply(format_bs)
            df_prod = df_prod.rename(
                columns={
                    "nombre": "Producto",
                    "precio_venta": "Precio venta",
                    "unidad_medida": "Unidad",
                    "stock_minimo": "Stock mínimo",
                }
            )
            st.dataframe(df_prod[["Producto", "Precio venta", "Unidad", "Stock mínimo"]], use_container_width=True, hide_index=True)
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

                        st.success("Entrada registrada correctamente.")
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
    # VENTAS
    # ==============================
    elif choice == "🛒 Ventas":
        st.header("Punto de venta")
        productos = fetch_productos()

        if not productos:
            st.info("Primero registra productos en el catálogo.")
        else:
            prods = {f"{p['nombre']} ({p.get('unidad_medida', 'Unidad')})": p for p in productos}

            with st.form("f_venta"):
                p_sel_name = st.selectbox("Producto", list(prods.keys()))
                c_venda = st.number_input("Cantidad", min_value=1, step=1)
                met = st.selectbox("Método de pago", ["Efectivo", "QR", "Tarjeta", "Transferencia"])
                observacion = st.text_input("Observación")
                submit_venta = st.form_submit_button("Finalizar venta", use_container_width=True)

            if submit_venta:
                p_data = prods[p_sel_name]
                try:
                    lotes = (
                        supabase.table("inventario_lotes")
                        .select("id, cantidad_actual, costo_unidad, fecha_vencimiento")
                        .eq("producto_id", p_data["id"])
                        .gt("cantidad_actual", 0)
                        .order("fecha_vencimiento")
                        .execute()
                    )
                    lotes_data = lotes.data or []
                    stock_total = sum(safe_int(l["cantidad_actual"]) for l in lotes_data)

                    if not lotes_data or stock_total < c_venda:
                        st.error("Stock insuficiente para completar la venta.")
                    else:
                        total_v = c_venda * safe_float(p_data["precio_venta"])

                        venta_insert = supabase.table("ventas").insert(
                            {
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
                                        "precio_unitario_aplicado": safe_float(p_data["precio_venta"]),
                                        "costo_unitario_lote": safe_float(lote.get("costo_unidad")),
                                    }
                                ).execute()

                                supabase.table("inventario_lotes").update(
                                    {"cantidad_actual": nuevo_stock}
                                ).eq("id", lote["id"]).execute()

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

                            st.success(
                                f"Venta registrada correctamente. Total: {format_bs(total_v)} | Detalles generados: {detalles_insertados}"
                            )

                except Exception as e:
                    st.error(f"No se pudo completar la venta: {e}")

        st.markdown("### Últimas ventas")
        ventas = fetch_ventas(start_date, end_date)
        if ventas:
            ventas_df = pd.DataFrame(ventas)
            ventas_df["total"] = ventas_df["total"].apply(format_bs)
            ventas_df = ventas_df.rename(
                columns={
                    "fecha": "Fecha",
                    "metodo_pago": "Método de pago",
                    "total": "Total",
                    "estado": "Estado",
                    "observacion": "Observación",
                }
            )
            cols = [c for c in ["Fecha", "Método de pago", "Total", "Estado", "Observación"] if c in ventas_df.columns]
            st.dataframe(ventas_df[cols], use_container_width=True, hide_index=True)
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
                            st.success("Movimiento registrado correctamente.")
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
            if "monto" in flujo_df.columns:
                flujo_df["monto"] = flujo_df["monto"].apply(format_bs)
            rename_map = {
                "fecha": "Fecha",
                "tipo": "Tipo",
                "categoria": "Categoría",
                "motivo": "Motivo",
                "monto": "Monto",
                "metodo_pago": "Método de pago",
                "observacion": "Observación",
                "referencia": "Referencia",
            }
            flujo_df = flujo_df.rename(columns=rename_map)
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
                    prod = d.get("productos") or {}
                    venta = d.get("ventas") or {}
                    cantidad = safe_int(d.get("cantidad"))
                    precio = safe_float(d.get("precio_unitario_aplicado"))
                    costo = safe_float(d.get("costo_unitario_lote"))
                    rows.append(
                        {
                            "Fecha": venta.get("fecha"),
                            "Producto": prod.get("nombre", "Sin nombre"),
                            "Cantidad": cantidad,
                            "Precio unitario": precio,
                            "Ingreso": cantidad * precio,
                            "Costo": cantidad * costo,
                            "Utilidad bruta": (cantidad * precio) - (cantidad * costo),
                            "Método de pago": venta.get("metodo_pago", "-"),
                        }
                    )
                det_df = pd.DataFrame(rows)

                st.markdown("#### Resumen por producto")
                resumen_prod = (
                    det_df.groupby("Producto", as_index=False)
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
                    st.dataframe(stock_df, use_container_width=True, hide_index=True)

                rows = []
                for item in lotes:
                    prod = item.get("productos") or {}
                    cantidad = safe_int(item.get("cantidad_actual"))
                    costo = safe_float(item.get("costo_unidad"))
                    rows.append(
                        {
                            "Producto": prod.get("nombre", "Sin nombre"),
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
