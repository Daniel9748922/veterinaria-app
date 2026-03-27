import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date

# 1. Configuración de Conexión
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="VetControl Pro", layout="wide", page_icon="🐾")

# --- SISTEMA DE SEGURIDAD (LOGIN) ---
def check_password():
    """Retorna True si el usuario ingresó la contraseña correcta."""
    def password_entered():
        if st.session_state["username"] == st.secrets["LOGIN_USER"] and \
           st.session_state["password"] == st.secrets["LOGIN_PASS"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Eliminar contraseña de la memoria
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Acceso Restringido")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered)
        st.error("😕 Usuario o contraseña incorrectos")
        return False
    else:
        return True

if check_password():
    # --- SI EL LOGIN ES CORRECTO, MOSTRAR LA APP ---
    
    st.sidebar.write(f"Conectado como Administrador")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()

    st.markdown("""
        <style>
        .main { background-color: #f5f7f9; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        </style>
        """, unsafe_allow_html=True)

    st.title("🐾 VetControl Pro")

    menu = ["📊 Dashboard", "🔍 Buscador", "📦 Catálogo (Productos)", "📥 Entradas", "🛒 Ventas", "💰 Caja"]
    choice = st.sidebar.selectbox("Menú", menu)

    # --- DASHBOARD ---
    if choice == "📊 Dashboard":
        st.subheader("Estado de Inventario")
        res = supabase.table("inventario_lotes").select("cantidad_actual, fecha_vencimiento, productos(nombre, unidad_medida)").gt("cantidad_actual", 0).order("fecha_vencimiento").execute()
        
        if res.data:
            datos_tabla = []
            for item in res.data:
                f_venc = datetime.strptime(item['fecha_vencimiento'], '%Y-%m-%d').date()
                dias = (f_venc - date.today()).days
                estado = "✅ Ok"
                if dias <= 0: estado = "❌ VENCIDO"
                elif dias <= 30: estado = "⚠️ Crítico"
                
                datos_tabla.append({
                    "Producto": item['productos']['nombre'],
                    "Stock": f"{item['cantidad_actual']} {item['productos'].get('unidad_medida', 'Und')}",
                    "Vencimiento": item['fecha_vencimiento'],
                    "Días": dias,
                    "Estado": estado
                })
            st.dataframe(datos_tabla, use_container_width=True)
        else:
            st.info("No hay stock disponible.")

    # --- CATÁLOGO CON UNIDADES ---
    elif choice == "📦 Catálogo (Productos)":
        st.header("Gestión de Productos")
        col1, col2 = st.columns(2)
        with col1:
            n_cat = st.text_input("Nueva Categoría")
            if st.button("Crear Categoría"):
                supabase.table("categorias").insert({"nombre": n_cat}).execute()
                st.success("Guardado")
        with col2:
            res_c = supabase.table("categorias").select("*").execute()
            if res_c.data:
                cats = {c['nombre']: c['id'] for c in res_c.data}
                sel_c = st.selectbox("Categoría", list(cats.keys()))
                n_p = st.text_input("Nombre del Producto")
                u_m = st.selectbox("Unidad de Medida", ["Unidades", "Kg", "Gr", "Ml", "Lt", "Tabletas"])
                p_v = st.number_input("Precio Venta", min_value=0.0)
                if st.button("Crear Producto"):
                    supabase.table("productos").insert({
                        "nombre": n_p, 
                        "categoria_id": cats[sel_c], 
                        "precio_venta": p_v,
                        "unidad_medida": u_m
                    }).execute()
                    st.success("Producto creado con éxito")

    # --- VENTAS (Misma lógica corregida) ---
    elif choice == "🛒 Ventas":
        st.header("Punto de Venta")
        res_p = supabase.table("productos").select("id, nombre, precio_venta, unidad_medida").execute()
        if res_p.data:
            prods = {f"{p['nombre']} ({p['unidad_medida']})": p for p in res_p.data}
            with st.form("f_venta"):
                p_sel_name = st.selectbox("Producto", list(prods.keys()))
                c_venda = st.number_input("Cantidad", min_value=1)
                met = st.selectbox("Pago", ["Efectivo", "QR", "Tarjeta"])
                if st.form_submit_button("Finalizar Venta"):
                    p_data = prods[p_sel_name]
                    lotes = supabase.table("inventario_lotes").select("*").eq("producto_id", p_data['id']).gt("cantidad_actual", 0).order("fecha_vencimiento").execute()
                    
                    if lotes.data and sum(l['cantidad_actual'] for l in lotes.data) >= c_venda:
                        total_v = c_venda * p_data["precio_venta"]
                        supabase.table("ventas").insert({"total": total_v, "metodo_pago": met}).execute()
                        
                        pendiente = c_venda
                        for l in lotes.data:
                            if pendiente <= 0: break
                            quitar = min(l['cantidad_actual'], pendiente)
                            supabase.table("inventario_lotes").update({"cantidad_actual": l['cantidad_actual'] - quitar}).eq("id", l['id']).execute()
                            pendiente -= quitar
                        
                        supabase.table("flujo_caja").insert({"tipo": "INGRESO", "monto": total_v, "motivo": f"Venta: {p_sel_name}"}).execute()
                        st.success(f"Venta OK: ${total_v}")
                    else: st.error("Stock insuficiente")

    # (Las demás secciones como Entradas y Caja se mantienen igual que antes...)
    elif choice == "📥 Entradas":
        st.header("Entrada de Stock")
        res_p = supabase.table("productos").select("id, nombre, unidad_medida").execute()
        if res_p.data:
            prods = {f"{p['nombre']} ({p['unidad_medida']})": p['id'] for p in res_p.data}
            with st.form("f_ent"):
                p_id_sel = st.selectbox("Producto", list(prods.keys()))
                ca = st.number_input("Cantidad", min_value=1)
                co = st.number_input("Costo Unitario", min_value=0.0)
                ve = st.date_input("Vencimiento")
                if st.form_submit_button("Registrar"):
                    supabase.table("inventario_lotes").insert({"producto_id": prods[p_id_sel], "cantidad_actual": ca, "cantidad_inicial": ca, "costo_unidad": co, "fecha_vencimiento": str(ve)}).execute()
                    supabase.table("flujo_caja").insert({"tipo": "EGRESO", "monto": ca*co, "motivo": f"Compra: {p_id_sel}"}).execute()
                    st.success("Entrada registrada")

    elif choice == "💰 Caja":
        st.header("Flujo de Efectivo")
        res = supabase.table("flujo_caja").select("*").order("fecha", desc=True).execute()
        if res.data:
            ing = sum(x['monto'] for x in res.data if x['tipo'] == 'INGRESO')
            egr = sum(x['monto'] for x in res.data if x['tipo'] == 'EGRESO')
            st.metric("Saldo Neto", f"${ing - egr}", delta=f"Ingresos: ${ing}")
            st.dataframe(res.data)
