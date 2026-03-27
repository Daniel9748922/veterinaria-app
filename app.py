import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Configuración (Se mantiene igual)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="VetControl Pro", layout="wide")
st.title("🐾 VetControl: Gestión Veterinaria")

menu = ["Dashboard", "Categorías y Productos", "Entrada de Inventario (FEFO)", "Ventas Rápidas", "Flujo de Caja"]
choice = st.sidebar.selectbox("Menú", menu)

# --- CATEGORÍAS Y PRODUCTOS (Código anterior se mantiene) ---
if choice == "Categorías y Productos":
    st.header("Configuración de Productos")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Nueva Categoría")
        nueva_cat = st.text_input("Nombre de la Categoría")
        if st.button("Guardar Categoría"):
            supabase.table("categorias").insert({"nombre": nueva_cat}).execute()
            st.success("Categoría guardada")
    with col2:
        st.subheader("Nuevo Producto")
        res = supabase.table("categorias").select("*").execute()
        cats = {c['nombre']: c['id'] for c in res.data}
        cat_sel = st.selectbox("Selecciona Categoría", list(cats.keys()))
        nom_prod = st.text_input("Nombre del Producto")
        prec = st.number_input("Precio de Venta", min_value=0.0)
        if st.button("Guardar Producto"):
            supabase.table("productos").insert({"nombre": nom_prod, "categoria_id": cats[cat_sel], "precio_venta": prec}).execute()
            st.success("Producto guardado")

# --- NUEVA SECCIÓN: ENTRADA DE INVENTARIO (FEFO) ---
elif choice == "Entrada de Inventario (FEFO)":
    st.header("📥 Registro de Entradas (Lotes)")
    
    # Traemos productos para el selector
    res_p = supabase.table("productos").select("id, nombre").execute()
    prods = {p['nombre']: p['id'] for p in res_p.data}
    
    with st.form("form_inventario"):
        prod_sel = st.selectbox("Producto que ingresa", list(prods.keys()))
        col_a, col_b = st.columns(2)
        cantidad = col_a.number_input("Cantidad", min_value=1)
        costo = col_b.number_input("Costo Unitario de Compra", min_value=0.0)
        fecha_venc = st.date_input("Fecha de Vencimiento", min_value=datetime.now())
        
        if st.form_submit_button("Registrar Entrada"):
            # 1. Insertar en Lotes
            lote_data = {
                "producto_id": prods[prod_sel],
                "cantidad_actual": cantidad,
                "cantidad_inicial": cantidad,
                "costo_unitario": costo,
                "fecha_vencimiento": str(fecha_venc)
            }
            supabase.table("inventario_lotes").insert(lote_data).execute()
            
            # 2. Registrar en Flujo de Caja (EGRESO)
            egreso_data = {
                "tipo": "EGRESO",
                "monto": cantidad * costo,
                "motivo": f"Compra de stock: {prod_sel} ({cantidad} unidades)",
            }
            supabase.table("flujo_caja").insert(egreso_data).execute()
            
            st.success(f"Entrada registrada. Se descontó {cantidad * costo} del flujo de caja.")

# --- DASHBOARD ---
elif choice == "Dashboard":
    st.subheader("Inventario Actual (Resumen FEFO)")
    # Query compleja para ver qué hay
    res = supabase.table("inventario_lotes").select("*, productos(nombre)").order("fecha_vencimiento").execute()
    if res.data:
        st.table(res.data)
    else:
        st.info("No hay stock registrado.")
