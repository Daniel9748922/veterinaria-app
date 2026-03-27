import streamlit as st
from supabase import create_client, Client

# 1. Configuración de Conexión (Esto lo llenaremos en los "Secrets" de Streamlit)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="VetControl Pro", layout="wide")

# --- INTERFAZ PRINCIPAL ---
st.title("🐾 VetControl: Inventario & Ventas")

menu = ["Dashboard", "Inventario (FEFO)", "Ventas Rápidas", "Flujo de Caja", "Clientes"]
choice = st.sidebar.selectbox("Menú de Navegación", menu)

if choice == "Dashboard":
    st.subheader("Estado General del Negocio")
    col1, col2, col3 = st.columns(3)
    col1.metric("Ventas del Día", "$0.00")
    col2.metric("Productos por Vencer", "0")
    col3.metric("Caja Actual", "$0.00")

elif choice == "Inventario (FEFO)":
    st.subheader("📦 Control de Stock por Vencimiento")
    # Aquí programaremos la lógica para ver qué vence primero
    st.info("Aquí aparecerán los lotes ordenados por fecha de vencimiento.")

elif choice == "Ventas Rápidas":
    st.subheader("🛒 Nueva Venta")
    # Formulario de venta rápida
    with st.form("venta_form"):
        cliente = st.text_input("Nombre del Cliente (Opcional)")
        metodo = st.selectbox("Método de Pago", ["Efectivo", "QR", "Tarjeta"])
        submit = st.form_submit_button("Registrar Venta")
