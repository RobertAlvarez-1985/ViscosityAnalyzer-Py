import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- Configuración de la Página y Estilo ---
st.set_page_config(
    page_title="Análisis de Viscosidad",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS para un diseño más pulido y profesional
st.markdown("""
<style>
    /* Estilo general */
    .stApp {
        background: #F0F2F6;
    }
    /* Mejora de la apariencia de los expanders en la sidebar */
    .st-emotion-cache-1jicfl2 {
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 10px 10px 10px 20px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Títulos y cabeceras */
    h1, h2 {
        color: #1E3A8A; /* Azul oscuro */
    }
    /* Estilo de los botones */
    .stButton>button {
        border-radius: 8px;
        border: 2px solid #1E3A8A;
        background-color: #1E3A8A;
        color: white;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: white;
        color: #1E3A8A;
    }
</style>
""", unsafe_allow_html=True)

# --- Funciones de Cálculo ---

def calcular_viscosidad(temperaturas, visc_40, visc_100):
    """
    Calcula la viscosidad en un rango de temperaturas usando una aproximación
    basada en la ecuación de Andrade.
    """
    # Evita la división por cero si visc_40 es menor o igual a visc_100
    if visc_40 <= 0 or visc_100 <= 0 or visc_40 <= visc_100:
        return np.full_like(temperaturas, np.nan, dtype=float)

    # Constante B calculada a partir de los dos puntos de viscosidad conocidos
    B = (np.log(visc_40) - np.log(visc_100)) / (100 - 40)
    # Ecuación para calcular la viscosidad en cualquier temperatura T
    return np.exp(np.log(visc_40) - B * (temperaturas - 40))

def get_viscosidad_a_temp(temp_objetivo, visc_40, visc_100):
    """Obtiene la viscosidad para una temperatura específica."""
    if visc_40 <= 0 or visc_100 <= 0 or visc_40 <= visc_100:
        return np.nan
    B = (np.log(visc_40) - np.log(visc_100)) / (100 - 40)
    return np.exp(np.log(visc_40) - B * (temp_objetivo - 40))

# --- Inicialización del Estado de la Aplicación ---
if 'lubricantes' not in st.session_state:
    st.session_state.lubricantes = []

# --- Barra Lateral (Sidebar) para Entradas de Usuario ---
with st.sidebar:
    st.title("🔧 Controles")
    st.header("Añadir Lubricante")

    # Formulario para agregar un nuevo lubricante
    with st.form("nuevo_lubricante_form", clear_on_submit=True):
        nombre = st.text_input("Nombre del Lubricante", placeholder="Ej: Mobil 1 5W-30")
        visc_40 = st.number_input("Viscosidad a 40°C (cSt)", min_value=0.1, step=0.1, format="%.1f")
        visc_100 = st.number_input("Viscosidad a 100°C (cSt)", min_value=0.1, step=0.1, format="%.1f")
        iv = st.number_input("Índice de Viscosidad (IV)", min_value=0, step=1)
        
        submitted = st.form_submit_button("📈 Agregar Lubricante")
        
        if submitted:
            if not nombre:
                st.warning("Por favor, ingrese un nombre para el lubricante.")
            elif visc_40 <= visc_100:
                st.error("La viscosidad a 40°C debe ser mayor que a 100°C.")
            else:
                nuevo_lubricante = {
                    "nombre": nombre,
                    "visc_40": visc_40,
                    "visc_100": visc_100,
                    "iv": iv
                }
                st.session_state.lubricantes.append(nuevo_lubricante)
                st.success(f"¡Lubricante '{nombre}' agregado!")

    st.header("📋 Lubricantes Agregados")
    if not st.session_state.lubricantes:
        st.info("Aún no se han agregado lubricantes.")
    else:
        # Mostrar lubricantes agregados con opción para eliminarlos
        for i, lub in enumerate(st.session_state.lubricantes):
            with st.expander(f"{lub['nombre']} (IV: {lub['iv']})"):
                st.write(f"Visc. 40°C: **{lub['visc_40']} cSt**")
                st.write(f"Visc. 100°C: **{lub['visc_100']} cSt**")
                if st.button(f"🗑️ Eliminar '{lub['nombre']}'", key=f"del_{i}"):
                    st.session_state.lubricantes.pop(i)
                    st.rerun()
    
    # Botón para limpiar todos los datos
    if st.session_state.lubricantes:
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            st.session_state.lubricantes = []
            st.rerun()

# --- Área Principal de la Aplicación ---
st.title("📊 Analizador de Viscosidad de Lubricantes")
st.write("Herramienta profesional para el análisis y comparación del comportamiento térmico de lubricantes.")

if not st.session_state.lubricantes:
    st.info("Agregue al menos un lubricante en la barra lateral para generar la gráfica y la tabla de datos.")
else:
    # --- Generación de la Gráfica Interactiva ---
    st.header("📉 Gráfica Comparativa de Viscosidad vs. Temperatura")

    fig = go.Figure()
    temperaturas_grafica = np.arange(0, 151, 1) # Rango de 0 a 150°C
    
    # Paleta de colores profesional
    colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

    for i, lub in enumerate(st.session_state.lubricantes):
        viscosidades = calcular_viscosidad(temperaturas_grafica, lub['visc_40'], lub['visc_100'])
        fig.add_trace(go.Scatter(
            x=temperaturas_grafica,
            y=viscosidades,
            mode='lines',
            name=f"{lub['nombre']} (IV: {lub['iv']})",
            line=dict(color=colores[i % len(colores)], width=3),
            hovertemplate='<b>%{fullData.name}</b><br>Temperatura: %{x}°C<br>Viscosidad: %{y:.2f} cSt<extra></extra>'
        ))

    fig.update_layout(
        xaxis_title="Temperatura (°C)",
        yaxis_title="Viscosidad Cinemática (cSt)",
        title=dict(text="Comportamiento de la Viscosidad", font=dict(size=20), x=0.5),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white',
        xaxis=dict(gridcolor='lightgrey'),
        yaxis=dict(gridcolor='lightgrey', type='log'), # Eje logarítmico para mejor visualización
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- Generación de la Tabla de Datos Comparativos ---
    st.header("🔢 Tabla de Datos Comparativos")

    # Selección de temperaturas para la tabla
    opciones_temp = list(range(10, 151, 10))
    temps_seleccionadas = st.multiselect(
        "Seleccione temperaturas específicas para comparar en la tabla:",
        options=opciones_temp,
        default=[40, 100]
    )
    
    if temps_seleccionadas:
        # Ordenar temperaturas seleccionadas
        temps_a_mostrar = sorted(list(set(temps_seleccionadas)))
        
        datos_tabla = {'Temperatura (°C)': temps_a_mostrar}
        for lub in st.session_state.lubricantes:
            viscosidades_calculadas = [
                get_viscosidad_a_temp(temp, lub['visc_40'], lub['visc_100'])
                for temp in temps_a_mostrar
            ]
            datos_tabla[lub['nombre']] = viscosidades_calculadas

        df = pd.DataFrame(datos_tabla)
        
        # Formateo del DataFrame para una mejor visualización
        st.dataframe(
            df.set_index('Temperatura (°C)').T.style.format("{:.2f}").background_gradient(cmap='viridis', axis=1),
            use_container_width=True
        )

# --- Pie de página ---
st.markdown("---")
st.write("Desarrollado con Python, Streamlit y Plotly. Una versión moderna del analizador de viscosidad.")
