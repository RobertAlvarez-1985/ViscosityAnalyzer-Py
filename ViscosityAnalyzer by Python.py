import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- Configuración de la Página y Estilo ---
st.set_page_config(
    page_title="Análisis de Viscosidad por Walther",
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

# --- Funciones de Cálculo (Corregidas con Fórmula de Walther) ---

def calcular_constantes_walther(visc_40, visc_100):
    """Calcula las constantes A y B de la ecuación de Walther (ASTM D341)."""
    # Constante para la ecuación, comúnmente 0.7 para viscosidades > 1.5 cSt
    C = 0.7
    
    # Temperaturas en Kelvin
    T1_k = 40 + 273.15
    T2_k = 100 + 273.15
    
    # Transformación de viscosidad según la fórmula
    Z1 = np.log10(np.log10(visc_40 + C))
    Z2 = np.log10(np.log10(visc_100 + C))
    
    # Logaritmo de las temperaturas en Kelvin
    logT1 = np.log10(T1_k)
    logT2 = np.log10(T2_k)
    
    # Cálculo de la constante B (pendiente)
    B = (Z1 - Z2) / (logT2 - logT1)
    
    # Cálculo de la constante A (intercepto)
    A = Z1 + B * logT1
    
    return A, B, C

def calcular_viscosidad_walther(temperaturas_c, visc_40, visc_100):
    """
    Calcula la viscosidad en un rango de temperaturas usando la ecuación de Walther.
    Devuelve un array de viscosidades.
    """
    if visc_40 <= 0 or visc_100 <= 0 or visc_40 <= visc_100:
        return np.full_like(temperaturas_c, np.nan, dtype=float)

    A, B, C = calcular_constantes_walther(visc_40, visc_100)
    
    # Evitar log de cero o negativo para temperaturas muy bajas
    temps_k = np.array(temperaturas_c) + 273.15
    viscosidades = np.full_like(temps_k, np.nan, dtype=float)
    
    # Calcular solo para temperaturas válidas
    valid_indices = temps_k > 0
    logT_valid = np.log10(temps_k[valid_indices])
    
    Z_calc = A - B * logT_valid
    
    # El resultado de 10**Z_calc debe ser > 1 para que log10 tenga sentido,
    # y 10**(10**Z_calc) debe ser mayor que C
    viscosidades_calculadas = (10**(10**Z_calc)) - C
    viscosidades[valid_indices] = viscosidades_calculadas
    
    return viscosidades

def get_viscosidad_a_temp(temp_objetivo_c, visc_40, visc_100):
    """Obtiene la viscosidad para una temperatura específica usando Walther."""
    viscosidad_array = calcular_viscosidad_walther([temp_objetivo_c], visc_40, visc_100)
    return viscosidad_array[0] if viscosidad_array is not None else np.nan


# --- Inicialización del Estado de la Aplicación ---
if 'lubricantes' not in st.session_state:
    st.session_state.lubricantes = []

# --- Barra Lateral (Sidebar) para Entradas de Usuario ---
with st.sidebar:
    st.title("🔧 Controles")
    st.header("Añadir Lubricante")

    with st.form("nuevo_lubricante_form", clear_on_submit=True):
        nombre = st.text_input("Nombre del Lubricante", placeholder="Ej: Mobil 1 5W-30")
        visc_40 = st.number_input("Viscosidad a 40°C (cSt)", min_value=1.0, value=45.0, step=0.1, format="%.2f")
        visc_100 = st.number_input("Viscosidad a 100°C (cSt)", min_value=1.0, value=9.0, step=0.1, format="%.2f")
        
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
                }
                st.session_state.lubricantes.append(nuevo_lubricante)
                st.success(f"¡Lubricante '{nombre}' agregado!")

    st.header("📋 Lubricantes Agregados")
    if not st.session_state.lubricantes:
        st.info("Aún no se han agregado lubricantes.")
    else:
        for i, lub in enumerate(st.session_state.lubricantes):
            with st.expander(f"{lub['nombre']}"):
                st.write(f"Visc. 40°C: **{lub['visc_40']} cSt**")
                st.write(f"Visc. 100°C: **{lub['visc_100']} cSt**")
                if st.button(f"🗑️ Eliminar '{lub['nombre']}'", key=f"del_{i}"):
                    st.session_state.lubricantes.pop(i)
                    st.rerun()
    
    if st.session_state.lubricantes:
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            st.session_state.lubricantes = []
            st.rerun()

# --- Área Principal de la Aplicación ---
st.title("📊 Analizador de Viscosidad de Lubricantes (Fórmula de Walther)")
st.write("Herramienta para comparar el comportamiento de la viscosidad de lubricantes frente a la temperatura.")

if not st.session_state.lubricantes:
    st.info("Agregue al menos un lubricante en la barra lateral para comenzar.")
else:
    # --- Controles para la Gráfica ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚙️ Opciones de Gráfica")
        # Selector para marcar puntos en la gráfica
        puntos_a_marcar = st.multiselect(
            "Seleccione hasta 3 temperaturas para resaltar en la gráfica:",
            options=list(range(0, 151, 5)),
            max_selections=3,
            default=[40, 100]
        )
    
    # --- Generación de la Gráfica Interactiva ---
    st.header("📉 Gráfica Comparativa de Viscosidad vs. Temperatura")

    fig = go.Figure()
    # Rango de temperaturas para una curva suave
    temperaturas_grafica = np.arange(0, 151, 1) 
    
    colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

    for i, lub in enumerate(st.session_state.lubricantes):
        viscosidades = calcular_viscosidad_walther(temperaturas_grafica, lub['visc_40'], lub['visc_100'])
        
        # Añadir la curva principal del lubricante
        fig.add_trace(go.Scatter(
            x=temperaturas_grafica,
            y=viscosidades,
            mode='lines',
            name=lub['nombre'],
            line=dict(color=colores[i % len(colores)], width=3),
            hovertemplate='<b>%{fullData.name}</b><br>Temperatura: %{x}°C<br>Viscosidad: %{y:.2f} cSt<extra></extra>'
        ))

        # Añadir marcadores para los puntos seleccionados por el usuario
        if puntos_a_marcar:
            visc_puntos = [get_viscosidad_a_temp(t, lub['visc_40'], lub['visc_100']) for t in puntos_a_marcar]
            fig.add_trace(go.Scatter(
                x=puntos_a_marcar,
                y=visc_puntos,
                mode='markers',
                marker=dict(size=12, color=colores[i % len(colores)], symbol='cross'),
                name=f"Puntos de {lub['nombre']}",
                showlegend=False,
                hovertemplate=f'<b>{lub["nombre"]}</b><br><b>Punto de Referencia</b><br>Temperatura: %{{x}}°C<br>Viscosidad: %{{y:.2f}} cSt<extra></extra>'
            ))

    # --- Actualización del Layout de la Gráfica ---
    fig.update_layout(
        xaxis_title="Temperatura (°C)",
        yaxis_title="Viscosidad Cinemática (cSt)",
        title=dict(text="Comportamiento de la Viscosidad", font=dict(size=20), x=0.5),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white',
        xaxis=dict(
            gridcolor='lightgrey',
            type='linear', # Eje X en escala lineal
            zeroline=False,
            fixedrange=False # Permite hacer zoom en el eje X
        ),
        yaxis=dict(
            gridcolor='lightgrey',
            type='linear', # Eje Y en escala lineal (Corrección principal)
            zeroline=False,
            fixedrange=False # Permite hacer zoom en el eje Y
        ),
        hovermode="x unified",
        dragmode='zoom' # Modo de interacción por defecto
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- Generación de la Tabla de Datos Comparativos ---
    st.header("🔢 Tabla de Datos Comparativos")

    opciones_temp_tabla = list(range(0, 151, 10))
    temps_seleccionadas = st.multiselect(
        "Seleccione temperaturas para mostrar en la tabla:",
        options=opciones_temp_tabla,
        default=[0, 20, 40, 60, 80, 100, 120, 140]
    )
    
    if temps_seleccionadas:
        temps_a_mostrar = sorted(list(set(temps_seleccionadas)))
        
        datos_tabla = {'Propiedad': [f"Viscosidad a {temp}°C (cSt)" for temp in temps_a_mostrar]}
        
        for lub in st.session_state.lubricantes:
            viscosidades_calculadas = [
                get_viscosidad_a_temp(temp, lub['visc_40'], lub['visc_100'])
                for temp in temps_a_mostrar
            ]
            datos_tabla[lub['nombre']] = viscosidades_calculadas

        df = pd.DataFrame(datos_tabla).set_index('Propiedad')
        
        st.dataframe(
            df.style.format("{:.2f}").background_gradient(cmap='viridis', axis=1),
            use_container_width=True
        )

# --- Pie de página ---
st.markdown("---")
st.write("Desarrollado con Python, Streamlit y Plotly. Implementación basada en la ecuación de Walther (ASTM D341).")

 
