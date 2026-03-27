import streamlit as st
from supabase import create_client, Client

# Configuración de Conexión
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="VetControl Pro", layout="wide")
st.title("🐾 VetControl: Gestión Veterinaria")

menu = ["Dashboard", "Categorías y Productos", "Inventario (Entradas)", "Ventas Rápidas", "Flujo de Caja"]
choice = st.sidebar.selectbox("Menú", menu)

# --- SECCIÓN: CATEGORÍAS Y PRODUCTOS ---
if choice == "Categorías y Productos":
    st.header("Configuración de Productos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Nueva Categoría")
        nueva_cat = st.text_input("Nombre de la Categoría (Ej: Alimentos, Medicinas)")
        if st.button("Guardar Categoría"):
            if nueva_cat:
                supabase.table("categorias").insert({"nombre": nueva_cat}).execute()
                st.success(f"Categoría '{nueva_cat}' guardada!")
            else:
                st.error("Escribe un nombre")

    with col2:
        st.subheader("Nuevo Producto")
        # Traemos las categorías para el selectbox
        res = supabase.table("categorias").select("*").execute()
        cats = {c['nombre']: c['id'] for c in res.data}
        
        cat_seleccionada = st.selectbox("Selecciona Categoría", list(cats.keys()))
        nombre_prod = st.text_input("Nombre del Producto")
        precio = st.number_input("Precio de Venta", min_value=0.0, step=0.1)
        
        if st.button("Guardar Producto"):
            if nombre_prod:
                data = {
                    "nombre": nombre_prod, 
                    "categoria_id": cats[cat_seleccionada],
                    "precio_venta": precio
                }
                supabase.table("productos").insert(data).execute()
                st.success(f"Producto '{nombre_prod}' registrado!")

# --- SECCIÓN: DASHBOARD (Resumen rápido) ---
elif choice == "Dashboard":
    st.subheader("Estado General")
    # Aquí luego sumaremos el total de la tabla flujo_caja
    st.info("Bienvenido. Empieza registrando categorías y productos en el menú de la izquierda.")
