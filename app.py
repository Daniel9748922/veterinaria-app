import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# 1. Configuración de Conexión (Asegúrate de tener estos nombres en Streamlit Secrets)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="VetControl Pro", layout="wide")
st.title("🐾 VetControl: Gestión Veterinaria Integral")

# Menú Lateral
menu = ["Dashboard", "Categorías y Productos", "Entrada de Inventario (FEFO)", "Ventas Rápidas", "Flujo de Caja"]
choice = st.sidebar.selectbox("Menú de Navegación", menu)

# --- MÓDULO 1: DASHBOARD ---
if choice == "Dashboard":
    st.subheader("📦 Estado Actual del Inventario (Orden FEFO)")
    
    # Consulta combinada: Lotes + Nombre del Producto
    res = supabase.table("inventario_lotes").select("cantidad_actual, fecha_vencimiento, productos(nombre)").gt("cantidad_actual", 0).order("fecha_vencimiento").execute()
    
    if res.data:
        datos_vista = []
        for item in res.data:
            datos_vista.append({
                "Producto": item['productos']['nombre'],
                "Stock Disponible": item['cantidad_actual'],
                "Vence el": item['fecha_vencimiento']
            })
        st.table(datos_vista)
    else:
        st.info("No hay stock disponible. Registra una entrada en el menú.")

# --- MÓDULO 2: CATEGORÍAS Y PRODUCTOS ---
elif choice == "Categorías y Productos":
    st.header("⚙️ Configuración de Base")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Nueva Categoría")
        nueva_cat = st.text_input("Nombre (ej: Vacunas, Alimento)")
        if st.button("Guardar Categoría"):
            if nueva_cat:
                supabase.table("categorias").insert({"nombre": nueva_cat}).execute()
                st.success("Categoría creada")
                st.rerun()

    with col2:
        st.subheader("Nuevo Producto")
        res_cat = supabase.table("categorias").select("*").execute()
        if res_cat.data:
            cats = {c['nombre']: c['id'] for c in res_cat.data}
            cat_sel = st.selectbox("Categoría", list(cats.keys()))
            nom_prod = st.text_input("Nombre del Producto")
            prec = st.number_input("Precio de Venta", min_value=0.0)
            if st.button("Guardar Producto"):
                supabase.table("productos").insert({"nombre": nom_prod, "categoria_id": cats[cat_sel], "precio_venta": prec}).execute()
                st.success("Producto creado")
        else:
            st.warning("Crea una categoría primero")

# --- MÓDULO 3: ENTRADA DE INVENTARIO (ENTRADAS) ---
elif choice == "Entrada de Inventario (FEFO)":
    st.header("📥 Ingreso de Mercancía (Lotes)")
    
    res_p = supabase.table("productos").select("id, nombre").execute()
    if res_p.data:
        prods = {p['nombre']: p['id'] for p in res_p.data}
        
        with st.form("form_lotes"):
            prod_sel = st.selectbox("Seleccionar Producto", list(prods.keys()))
            c1, c2 = st.columns(2)
            cant = c1.number_input("Cantidad que ingresa", min_value=1)
            costo = c2.number_input("Costo Unitario", min_value=0.0)
            f_venc = st.date_input("Fecha de Vencimiento")
            
            if st.form_submit_button("Registrar Entrada"):
                # Insertar Lote
                supabase.table("inventario_lotes").insert({
                    "producto_id": prods[prod_sel],
                    "cantidad_actual": cant,
                    "cantidad_inicial": cant,
                    "costo_unidad": costo,
                    "fecha_vencimiento": str(f_venc)
                }).execute()
                
                # Registrar Egreso en Caja
                supabase.table("flujo_caja").insert({
                    "tipo": "EGRESO",
                    "monto": cant * costo,
                    "motivo": f"Compra Stock: {prod_sel}"
                }).execute()
                st.success("Entrada y Egreso registrados")
                st.balloons()
    else:
        st.error("No hay productos creados.")

# --- MÓDULO 4: VENTAS RÁPIDAS (SALIDAS CON LÓGICA FEFO) ---
elif choice == "Ventas Rápidas":
    st.header("🛒 Punto de Venta")
    
    res_p = supabase.table("productos").select("id, nombre, precio_venta").execute()
    prods = {p['nombre']: {"id": p['id'], "precio": p['precio_venta']} for p in res_p.data}
    
    with st.form("venta_rapida"):
        prod_venda = st.selectbox("Producto a vender", list(prods.keys()))
        cant_venda = st.number_input("Cantidad", min_value=1)
        metodo = st.selectbox("Método de Pago", ["Efectivo", "QR", "Transferencia"])
        cliente = st.text_input("Cliente (Opcional)")
        
        if st.form_submit_button("Finalizar Venta"):
            id_p = prods[prod_venda]["id"]
            # BUSCAR LOTES DISPONIBLES ORDENADOS POR VENCIMIENTO (FEFO)
            lotes = supabase.table("inventario_lotes").select("*").eq("producto_id", id_p).gt("cantidad_actual", 0).order("fecha_vencimiento").execute()
            
            if lotes.data:
                total_disponible = sum(l['cantidad_actual'] for l in lotes.data)
                if total_disponible >= cant_venda:
                    # Registrar la Venta Cabecera
                    venta_total = cant_venda * prods[prod_venda]["precio"]
                    res_v = supabase.table("ventas").insert({"total": venta_total, "cliente_nombre": cliente, "metodo_pago": metodo}).execute()
                    id_v = res_v.data[0]['id']
                    
                    # Descontar de lotes uno por uno (Lógica FEFO)
                    por_descontar = cant_venda
                    for lote in lotes.data:
                        if por_descontar <= 0: break
                        
                        can_en_lote = lote['cantidad_actual']
                        if can_en_lote <= por_descontar:
                            desc = can_en_lote
                            por_descontar -= can_en_lote
                        else:
                            desc = por_descontar
                            por_descontar = 0
                            
                        # Actualizar Lote
                        supabase.table("inventario_lotes").update({"cantidad_actual": can_en_lote - desc}).eq("id", lote['id']).execute()
                    
                    # Registrar Ingreso en Caja
                    supabase.table("flujo_caja").insert({"tipo": "INGRESO", "monto": venta_total, "motivo": f"Venta: {prod_venda}"}).execute()
                    st.success(f"Venta realizada por ${venta_total}")
                else:
                    st.error(f"Stock insuficiente. Solo tienes {total_disponible} unidades.")
            else:
                st.error("No hay lotes con stock para este producto.")

# --- MÓDULO 5: FLUJO DE CAJA ---
elif choice == "Flujo de Caja":
    st.header("💰 Movimientos de Caja")
    res_caja = supabase.table("flujo_caja").select("*").order("fecha", desc=True).execute()
    
    if res_caja.data:
        total_ingresos = sum(f['monto'] for f in res_caja.data if f['tipo'] == 'INGRESO')
        total_egresos = sum(f['monto'] for f in res_caja.data if f['tipo'] == 'EGRESO')
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingresos", f"${total_ingresos}")
        c2.metric("Total Egresos", f"${total_egresos}")
        c3.metric("Saldo Neto", f"${total_ingresos - total_egresos}")
        
        st.dataframe(res_caja.data)
    else:
        st.info("Aún no hay movimientos de dinero.")
