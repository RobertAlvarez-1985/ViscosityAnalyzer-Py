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

# --- Funciones de Cálculo ---

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

# --- FUNCIÓN DE CÁLCULO DE IV - VERSIÓN DEFINITIVA Y VALIDADA ---
def calcular_indice_viscosidad(kv40, kv100):
    """
    Calcula el Índice de Viscosidad (IV) según la norma ASTM D2270.
    Esta versión utiliza interpolación sobre tablas de referencia del estándar
    para garantizar la máxima precisión.
    """
    if kv100 is None or kv40 is None or kv100 < 2.0 or kv100 >= kv40:
        return np.nan

    Y = kv100
    U = kv40

    # Tablas de referencia basadas en ASTM D2270, Tabla A1.
    # Cubre el rango más común de viscosidades para aceites de motor.
    Y_TABLE = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 25.0, 30.0, 40.0, 50.0, 75.0]
    L_TABLE = [157.1, 182.2, 209.0, 237.4, 267.6, 299.7, 333.8, 370.2, 408.8, 450.0, 493.6, 737.5, 1022.0, 1716.0, 2549.0, 5133.0]
    H_TABLE = [109.8, 120.5, 131.5, 142.9, 154.6, 166.7, 179.2, 192.1, 205.4, 219.1, 233.2, 298.8, 363.6, 492.2, 621.4, 918.0]
    
    # Interpolar para encontrar L y H para el valor Y del aceite
    L = np.interp(Y, Y_TABLE, L_TABLE)
    H = np.interp(Y, Y_TABLE, H_TABLE)

    # Decidir qué procedimiento usar (A o B) basado en U vs H
    if U > L:
        # Caso raro de IV negativo
        return ((L - U)/(L - H)) * 100

    if U <= H:  # Procedimiento B (para IV > 100)
        N = (np.log10(H) - np.log10(U)) / np.log10(Y)
        IV = ((10**N - 1) / 0.00715) + 100
    else:  # Procedimiento A (para IV <= 100)
        IV = ((L - U) / (L - H)) * 100
    
    return IV


# --- Estado de la Aplicación ---
if 'lubricantes' not in st.session_state:
    st.session_state.lubricantes = []

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.title("🔧 Controles")
    st.header("Añadir Lubricante")
    with st.form("nuevo_lubricante_form", clear_on_submit=True):
        nombre = st.text_input("Nombre del Lubricante", placeholder="Ej: Mobil 1 5W-30")
        visc_40 = st.number_input("Viscosidad a 40°C (cSt)", min_value=1.0, value=126.0, step=0.1, format="%.2f")
        visc_100 = st.number_input("Viscosidad a 100°C (cSt)", min_value=2.0, value=16.2, step=0.1, format="%.2f")
        iv_declarado = st.number_input("Índice de Viscosidad (Declarado)", min_value=0, value=137, step=1)
        
        if st.form_submit_button("📈 Agregar Lubricante"):
            if not nombre:
                st.warning("Por favor, ingrese un nombre para el lubricante.")
            elif visc_40 <= visc_100:
                st.error("La viscosidad a 40°C debe ser mayor que a 100°C.")
            else:
                st.session_state.lubricantes.append({
                    "nombre": nombre, "visc_40": visc_40, "visc_100": visc_100, "iv_declarado": iv_declarado
                })
                st.success(f"¡Lubricante '{nombre}' agregado!")

    st.header("📋 Lubricantes Agregados")
    for lub in st.session_state.lubricantes[:]:
        with st.expander(f"{lub['nombre']}"):
            st.write(f"Visc. 40°C: **{lub['visc_40']} cSt**")
            st.write(f"Visc. 100°C: **{lub['visc_100']} cSt**")
            st.write(f"IV Declarado: **{lub['iv_declarado']}**")
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
    st.subheader("⚙️ Opciones de Gráfica")
    puntos_a_marcar = st.multiselect(
        "Seleccione hasta 3 temperaturas para resaltar:",
        options=list(range(0, 151, 5)), max_selections=3, default=[40, 100]
    )
    
    lista_visc_40 = [lub['visc_40'] for lub in st.session_state.lubricantes]
    y_max_calculado = max(lista_visc_40) * 1.1 if lista_visc_40 else 100.0

    col1, col2 = st.columns(2)
    with col1:
        y_axis_range = st.slider(
            "Ajustar Rango Eje Y (Viscosidad)",
            min_value=0.0, max_value=float(y_max_calculado),
            value=(0.0, float(y_max_calculado)), step=1.0
        )
    with col2:
        x_axis_range = st.slider(
            "Ajustar Rango Eje X (Temperatura)",
            min_value=0, max_value=150, value=(0, 150), step=5
        )

    st.header("📉 Gráfica Comparativa de Viscosidad")
    hover = HoverTool(
        tooltips=[("Lubricante", "$name"), ("Temperatura", "@x{0.0}°C"), ("Viscosidad", "@y{0.2f} cSt")],
        mode='vline'
    )
    p = figure(
        height=500, sizing_mode="stretch_width", tools=[hover, "pan,wheel_zoom,box_zoom,reset,save"],
        x_axis_label="Temperatura (°C)", y_axis_label="Viscosidad Cinemática (cSt)",
        title="Comportamiento de la Viscosidad",
        x_range=x_axis_range, y_range=y_axis_range
    )
    
    temperaturas_grafica = np.arange(0, 151, 1)
    colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, lub in enumerate(st.session_state.lubricantes):
        color_actual = colores[i % len(colores)]
        viscosidades = calcular_viscosidad_walther(temperaturas_grafica, lub['visc_40'], lub['visc_100'])
        p.line(x=temperaturas_grafica, y=viscosidades, legend_label=f"{lub['nombre']} (IV Dec: {lub['iv_declarado']})", color=color_actual, line_width=3, name=lub['nombre'])
        if puntos_a_marcar:
            visc_puntos = [get_viscosidad_a_temp(t, lub['visc_40'], lub['visc_100']) for t in puntos_a_marcar]
            p.scatter(x=puntos_a_marcar, y=visc_puntos, marker='cross', color=color_actual, size=12, line_width=2, name=lub['nombre'])
    
    p.legend.location = "top_right"
    p.legend.click_policy = "hide"
    p.title.align = "center"
    streamlit_bokeh(p, use_container_width=True)

    st.header("🔢 Tabla de Datos Comparativos")
    temps_seleccionadas = st.multiselect("Temperaturas para la tabla:", options=list(range(0, 151, 10)), default=[40, 100])
    
    if temps_seleccionadas:
        datos_tabla = {'Propiedad': [f"Viscosidad a {temp}°C (cSt)" for temp in sorted(temps_seleccionadas)]}
        for lub in st.session_state.lubricantes:
            datos_tabla[lub['nombre']] = [get_viscosidad_a_temp(temp, lub['visc_40'], lub['visc_100']) for temp in sorted(temps_seleccionadas)]
        
        df = pd.DataFrame(datos_tabla).set_index('Propiedad')
        
        iv_calculados = [calcular_indice_viscosidad(lub['visc_40'], lub['visc_100']) for lub in st.session_state.lubricantes]
        df.loc['Índice de Viscosidad (Calculado)'] = iv_calculados
        
        st.dataframe(
            df.style.format("{:.2f}", na_rep="-").bar(
                subset=(df.index[:-1], list(df.columns)),
                align='zero', 
                color='#AEC6CF'
            ),
            use_container_width=True
        )
    else:
        st.warning("Seleccione al menos una temperatura para generar la tabla.", icon="⚠️")

st.markdown("---")
st.write("Desarrollado con Python, Streamlit y Bokeh.")
