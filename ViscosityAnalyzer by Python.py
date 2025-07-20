import streamlit as st
import pandas as pd
import numpy as np
from bokeh.plotting import figure
from bokeh.models import HoverTool
from streamlit_bokeh import streamlit_bokeh

# --- Configuración de la Página y Estilo ---
st.set_page_config(
    page_title="Análisis de Viscosidad con Bokeh",
    page_icon="🟠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS para un diseño más pulido
st.markdown("""
<style>
    .stApp { background: #F0F2F6; }
    .st-emotion-cache-1jicfl2 {
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 10px 10px 10px 20px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    h1, h2 { color: #1E3A8A; }
    .stButton>button {
        border-radius: 8px; border: 2px solid #1E3A8A;
        background-color: #1E3A8A; color: white;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { background-color: white; color: #1E3A8A; }
</style>
""", unsafe_allow_html=True)

# --- Funciones de Cálculo (Fórmula de Walther - ASTM D341) ---
def calcular_constantes_walther(visc_40, visc_100):
    C = 0.7
    T1_k, T2_k = 40 + 273.15, 100 + 273.15
    try:
        Z1 = np.log10(np.log10(visc_40 + C))
        Z2 = np.log10(np.log10(visc_100 + C))
        logT1, logT2 = np.log10(T1_k), np.log10(T2_k)
        B = (Z1 - Z2) / (logT2 - logT1)
        A = Z1 + B * logT1
    except (ValueError, TypeError):
        return None, None, None
    return A, B, C

def calcular_viscosidad_walther(temperaturas_c, visc_40, visc_100):
    if visc_40 <= 0 or visc_100 <= 0 or visc_40 <= visc_100:
        return np.full_like(np.array(temperaturas_c, dtype=float), np.nan)
    A, B, C = calcular_constantes_walther(visc_40, visc_100)
    if A is None:
        return np.full_like(np.array(temperaturas_c, dtype=float), np.nan)
    
    temps_k = np.array(temperaturas_c) + 273.15
    viscosidades = np.full_like(temps_k, np.nan, dtype=float)
    valid_indices = temps_k > 0
    with np.errstate(invalid='ignore', over='ignore'):
        logT_valid = np.log10(temps_k[valid_indices])
        Z_calc = A - B * logT_valid
        visc_calc = (10**(10**Z_calc)) - C
        viscosidades[valid_indices] = visc_calc
    return viscosidades

def get_viscosidad_a_temp(temp_objetivo_c, visc_40, visc_100):
    viscosidad_array = calcular_viscosidad_walther([temp_objetivo_c], visc_40, visc_100)
    return viscosidad_array[0] if viscosidad_array is not None else np.nan

# --- Estado de la Aplicación ---
if 'lubricantes' not in st.session_state:
    st.session_state.lubricantes = []

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.title("🔧 Controles")
    st.header("Añadir Lubricante")
    with st.form("nuevo_lubricante_form", clear_on_submit=True):
        nombre = st.text_input("Nombre del Lubricante", placeholder="Ej: Mobil 1 5W-30")
        visc_40 = st.number_input("Viscosidad a 40°C (cSt)", min_value=1.0, value=45.0, step=0.1, format="%.2f")
        visc_100 = st.number_input("Viscosidad a 100°C (cSt)", min_value=1.0, value=9.0, step=0.1, format="%.2f")
        
        if st.form_submit_button("📈 Agregar Lubricante"):
            if not nombre:
                st.warning("Por favor, ingrese un nombre para el lubricante.")
            elif visc_40 <= visc_100:
                st.error("La viscosidad a 40°C debe ser mayor que a 100°C.")
            else:
                st.session_state.lubricantes.append({"nombre": nombre, "visc_40": visc_40, "visc_100": visc_100})
                st.success(f"¡Lubricante '{nombre}' agregado!")

    st.header("📋 Lubricantes Agregados")
    for lub in st.session_state.lubricantes[:]:
        with st.expander(f"{lub['nombre']}"):
            st.write(f"Visc. 40°C: **{lub['visc_40']} cSt**")
            st.write(f"Visc. 100°C: **{lub['visc_100']} cSt**")
            if st.button(f"🗑️ Eliminar '{lub['nombre']}'", key=f"del_{lub['nombre']}"):
                st.session_state.lubricantes.remove(lub)
                st.rerun()

    if st.session_state.lubricantes and st.button("🗑️ Limpiar Todo", use_container_width=True):
        st.session_state.lubricantes = []
        st.rerun()

# --- Área Principal ---
st.title("📊 Analizador de Viscosidad de Lubricantes")

if not st.session_state.lubricantes:
    st.info("Agregue al menos un lubricante en la barra lateral para comenzar.")
else:
    # --- Opciones y Gráfica ---
    st.subheader("⚙️ Opciones de Gráfica")
    puntos_a_marcar = st.multiselect(
        "Seleccione hasta 3 temperaturas para resaltar:",
        options=list(range(0, 151, 5)), 
        max_selections=3,
        default=[40, 100]
    )
    
    st.header("📉 Gráfica Comparativa de Viscosidad (con Bokeh)")
    hover = HoverTool(
        tooltips=[("Lubricante", "$name"), ("Temperatura", "@x{0.0}°C"), ("Viscosidad", "@y{0.2f} cSt")],
        mode='vline'
    )
    p = figure(
        height=500, sizing_mode="stretch_width", tools=[hover, "pan,wheel_zoom,box_zoom,reset,save"],
        x_axis_label="Temperatura (°C)", y_axis_label="Viscosidad Cinemática (cSt)",
        title="Comportamiento de la Viscosidad"
    )
    temperaturas_grafica = np.arange(0, 151, 1)
    colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, lub in enumerate(st.session_state.lubricantes):
        color_actual = colores[i % len(colores)]
        viscosidades = calcular_viscosidad_walther(temperaturas_grafica, lub['visc_40'], lub['visc_100'])
        p.line(x=temperaturas_grafica, y=viscosidades, legend_label=lub['nombre'], color=color_actual, line_width=3, name=lub['nombre'])
        if puntos_a_marcar:
            visc_puntos = [get_viscosidad_a_temp(t, lub['visc_40'], lub['visc_100']) for t in puntos_a_marcar]
            p.scatter(x=puntos_a_marcar, y=visc_puntos, marker='cross', color=color_actual, size=12, line_width=2, name=lub['nombre'])
    
    # --- MODIFICACIÓN CLAVE: AJUSTE DEL EJE Y BASADO EN visc_40 ---
    # Busca el valor más alto de visc_40 entre todos los lubricantes agregados.
    lista_visc_40 = [lub['visc_40'] for lub in st.session_state.lubricantes]
    if lista_visc_40:
        # Establece el límite del eje Y como 1.1 veces ese valor máximo.
        y_max = max(lista_visc_40) * 1.1
        p.y_range.start = 0
        p.y_range.end = y_max
    
    p.legend.location = "top_right"
    p.legend.click_policy = "hide"
    p.title.align = "center"
    
    streamlit_bokeh(p, use_container_width=True)

    # --- Tabla de Datos ---
    st.header("🔢 Tabla de Datos Comparativos")
    temps_seleccionadas = st.multiselect("Temperaturas para la tabla:", options=list(range(0, 151, 10)), default=[0, 40, 100, 120])
    
    if temps_seleccionadas:
        datos_tabla = {'Propiedad': [f"Viscosidad a {temp}°C (cSt)" for temp in sorted(temps_seleccionadas)]}
        for lub in st.session_state.lubricantes:
            datos_tabla[lub['nombre']] = [get_viscosidad_a_temp(temp, lub['visc_40'], lub['visc_100']) for temp in sorted(temps_seleccionadas)]
        
        df = pd.DataFrame(datos_tabla).set_index('Propiedad')
        
        st.dataframe(
            df.style.format("{:.2f}", na_rep="-").bar(
                subset=list(df.columns),
                align='zero', 
                color='#AEC6CF'
            ),
            use_container_width=True
        )
    else:
        st.warning("Seleccione al menos una temperatura para generar la tabla.", icon="⚠️")

# --- Pie de página ---
st.markdown("---")
st.write("Desarrollado con Python, Streamlit y Bokeh.")
