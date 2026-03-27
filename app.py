import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date

# 1. Configuración de Conexión
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="VetControl Pro", layout="wide", page_icon="🐾")

# Estilo CSS corregido
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🐾 VetControl: Gestión Veterinaria")

# Menú Lateral
menu = ["📊 Dashboard Interactivo", "🔍 Buscador de Stock", "📦 Categorías y Productos", "📥 Entrada (Lotes/FEFO)", "🛒 Ventas Rápidas", "💰 Flujo de Caja"]
choice = st.sidebar.selectbox("Menú de Navegación", menu)

# --- MÓDULO 1: DASHBOARD INTERACTIVO ---
if choice == "📊 Dashboard Interactivo":
    st.subheader("Estado Crítico de Inventario")
    res = supabase.table("inventario_lotes").select("cantidad_actual, fecha_vencimiento, productos(nombre)").gt("cantidad_actual", 0).order("fecha_vencimiento").execute()
    
    if res.data:
        hoy = date.today()
        proximos_vencer = 0
        stock_total = 0
        datos_tabla = []
        for item in res.data:
            f_venc = datetime.strptime(item['fecha_vencimiento'], '%Y-%m-%d').date()
            dias_restantes = (f_venc - hoy).days
            stock_total += item['cantidad_actual']
            estado = "✅ Ok"
            if dias_restantes <= 0:
                estado = "❌ VENCIDO"
                proximos_vencer += 1
            elif dias_restantes <= 30:
                estado = "⚠️ Vence pronto"
                proximos_vencer += 1
            datos_tabla.append({
                "Producto": item['productos']['nombre'],
                "Cantidad": item['cantidad_actual'],
                "Vencimiento": item['fecha_vencimiento'],
                "Días restantes": dias_restantes,
                "Estado": estado
            })
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Unidades en Stock", stock_total)
        c2.metric("Alertas de Vencimiento", proximos_vencer)
        c3.metric("Lotes Activos", len(res.data))
        st.write("---")
        st.dataframe(datos_tabla, use_container_width=True)
    else:
        st.info("No hay stock registrado.")

# --- MÓDULO 2: BUSCADOR DE PRODUCTOS ---
elif choice == "🔍 Buscador de Stock":
    st.header("Buscador de Productos")
    busqueda = st.text_input("Escribe el nombre del producto...")
    if busqueda:
        res = supabase.table("inventario_lotes").select("cantidad_actual, fecha_vencimiento, productos!inner(nombre, precio_venta)").ilike("productos.nombre", f"%{busqueda}%").gt("cantidad_actual", 0).execute()
        if res.data:
            for r in res.data:
                with st.expander(f"📦 {r['productos']['nombre']} - Stock: {r['cantidad_actual']}"):
                    st.write(f"**Precio:** ${r['productos']['precio_venta']} | **Vence:** {r['fecha_vencimiento']}")
        else:
            st.warning("No se encontraron coincidencias.")

# --- MÓDULO 3: CATEGORÍAS Y PRODUCTOS ---
elif choice == "📦 Categorías y Productos":
    st.header("Configuración de Catálogo")
    c1, c2 = st.columns(2)
    with c1:
        n_cat = st.text_input("Nueva Categoría")
        if st.button("Crear Categoría"):
            supabase.table("categorias").insert({"nombre": n_cat}).execute()
            st.success("Guardado")
            st.rerun()
    with c2:
        res_c = supabase.table("categorias").select("*").execute()
        if res_c.data:
            cats = {c['nombre']: c['id'] for c in res_c.data}
            sel_c = st.selectbox("Categoría", list(cats.keys()))
            n_p = st.text_input("Nombre del Producto")
            p_v = st.number_input("Precio Venta", min_value=0.0)
            if st.button("Crear Producto"):
                supabase.table("productos").insert({"nombre": n_p, "categoria_id": cats[sel_c], "precio_venta": p_v}).execute()
                st.success("Creado")
        else: st.info("Crea una categoría primero")

# --- MÓDULO 4: ENTRADA DE INVENTARIO ---
elif choice == "📥 Entrada (Lotes/FEFO)":
    st.header("Registro de Compras")
    res_p = supabase.table("productos").select("id, nombre").execute()
    if res_p.data:
        prods = {p['nombre']: p['id'] for p in res_p.data}
        with st.form("f_entrada"):
            p_sel = st.selectbox("Producto", list(prods.keys()))
            cant = st.number_input("Cantidad", min_value=1)
            cost = st.number_input("Costo Unitario", min_value=0.0)
            venc = st.date_input("Fecha de Vencimiento")
            if st.form_submit_button("Guardar Entrada"):
                supabase.table("inventario_lotes").insert({"producto_id": prods[p_sel], "cantidad_actual": cant, "cantidad_inicial": cant, "costo_unidad": cost, "fecha_vencimiento": str(venc)}).execute()
                supabase.table("flujo_caja").insert({"tipo": "EGRESO", "monto": cant*cost, "motivo": f"Compra: {p_sel}"}).execute()
                st.success("Entrada registrada")
                st.balloons()

# --- MÓDULO 5: VENTAS RÁPIDAS ---
elif choice == "🛒 Ventas Rápidas":
    st.header("Punto de Venta")
    res_p = supabase.table("productos").select("id, nombre, precio_venta").execute()
    if res_p.data:
        prods = {p['nombre']: {"id": p['id'], "precio": p['precio_venta']} for p in res_p.data}
        with st.form("f_venta"):
            p_venda = st.selectbox("Producto", list(prods.keys()))
            c_venda = st.number_input("Cantidad", min_value=1)
            met = st.selectbox("Pago", ["Efectivo", "QR", "Tarjeta"])
            if st.form_submit_button("Vender"):
                id_p = prods[p_venda]["id"]
                lotes = supabase.table("inventario_lotes").select("*").eq("producto_id", id_p).gt("cantidad_actual", 0).order("fecha_vencimiento").execute()
                if lotes.data and sum(l['cantidad_actual'] for l in lotes.data) >= c_venda:
                    total_v = c_venda * prods[p_venda]["precio"]
                    supabase.table("ventas").insert({"total": total_v, "metodo_pago": met}).execute()
                    pendiente = c_venda
                    for l in lotes.data:
                        if pendiente <= 0: break
                        quitar = min(l['cantidad_actual'], pendiente)
                        supabase.table("inventario_lotes").update({"cantidad_actual": l['cantidad_actual'] - quitar}).eq("id", l['id']).execute()
                        pendiente -= quitar
                    supabase.table("flujo_caja").insert({"tipo": "INGRESO", "monto": total_v, "motivo": f"Venta: {p_venda}"}).execute()
                    st.success(f"Venta realizada: ${total_v}")
                else: st.error("Stock insuficiente")

# --- MÓDULO 6: FLUJO DE CAJA ---
elif choice == "💰 Flujo de Caja":
    st.header("Caja")
    res = supabase.table("flujo_caja").select("*").order("fecha", desc=True).execute()
    if res.data:
        ing = sum(x['monto'] for x in res.data if x['tipo'] == 'INGRESO')
        egr = sum(x['monto'] for x in res.data if x['tipo'] == 'EGRESO')
        st.metric("Saldo Neto", f"${ing - egr}", delta=f"Ingresos: ${ing}")
        st.dataframe(res.data, use_container_width=True)
