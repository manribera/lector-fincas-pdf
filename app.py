import io
import re
import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="Lector de Fincas PDF", layout="wide")

st.title("📄 Lector de Fincas en PDF")

st.write(
"""
Suba uno o varios **PDF del Registro de la Propiedad** para extraer información
y generar un archivo Excel automáticamente.
"""
)

st.info("La aplicación buscará: matrícula, provincia, finca, propietario, cédula, valor fiscal y más.")

# SUBIR ARCHIVOS
uploaded_files = st.file_uploader(
    "Cargar archivos PDF",
    type=["pdf"],
    accept_multiple_files=True
)

def leer_pdf(file):

    reader = PdfReader(file)
    texto_total = ""

    for page in reader.pages:
        texto = page.extract_text()

        if texto:
            texto_total += texto

    return texto_total


def buscar(texto, patron):

    resultado = re.search(patron, texto, re.IGNORECASE)

    if resultado:
        return resultado.group(1)

    return ""


def extraer_datos(texto, nombre_archivo):

    datos = {
        "Archivo": nombre_archivo,
        "Matricula": buscar(texto, r"Matr[ií]cula[: ]+([A-Z0-9\-\/]+)"),
        "Provincia": buscar(texto, r"Provincia[: ]+([A-Za-zÁÉÍÓÚñ ]+)"),
        "Finca": buscar(texto, r"Finca[: ]+([0-9\-\/]+)"),
        "Derechos": buscar(texto, r"Derechos[: ]+(.+?)Antecedentes"),
        "Antecedentes": buscar(texto, r"Antecedentes[: ]+(.+?)Valor Fiscal"),
        "Valor Fiscal": buscar(texto, r"Valor Fiscal[: ]+([₡0-9\., ]+)"),
        "Propietario": buscar(texto, r"Propietario[: ]+(.+?)C[eé]dula"),
        "Cedula": buscar(texto, r"C[eé]dula[: ]+([0-9\-\.]+)"),
        "Fecha Inscripcion": buscar(texto, r"Fecha de Inscripci[oó]n[: ]+([0-9\/\-]+)"),
        "Causa Adquisitiva": buscar(texto, r"Causa Adquisitiva[: ]+(.+)")
    }

    return datos


def generar_excel(df):

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    output.seek(0)

    return output


# PROCESAMIENTO

if uploaded_files:

    resultados = []

    for file in uploaded_files:

        try:

            texto = leer_pdf(file)

            if texto:

                datos = extraer_datos(texto, file.name)

                resultados.append(datos)

            else:

                st.warning(f"{file.name} no contiene texto seleccionable.")

        except Exception as e:

            st.error(f"Error leyendo {file.name}")

    if resultados:

        st.subheader("Vista previa de resultados")

        df = pd.DataFrame(resultados)

        st.dataframe(df)

        excel = generar_excel(df)

        st.download_button(
            label="⬇ Descargar Excel",
            data=excel,
            file_name="datos_fincas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:

    st.warning("Suba uno o más archivos PDF para comenzar.")
