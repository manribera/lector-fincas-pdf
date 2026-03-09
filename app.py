import io
import re
import pandas as pd
import streamlit as st
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

st.set_page_config(page_title="Lector de Fincas PDF", layout="wide")

st.title("📄 Lector de Fincas del Registro")

st.write(
"""
Suba uno o varios PDFs del Registro de la Propiedad.
La app extraerá la información y generará un Excel automáticamente.
"""
)

uploaded_files = st.file_uploader(
    "Cargar archivos PDF",
    type=["pdf"],
    accept_multiple_files=True
)

def leer_pdf_texto(file):

    reader = PdfReader(file)
    texto = ""

    for page in reader.pages:
        contenido = page.extract_text()
        if contenido:
            texto += contenido

    return texto


def leer_pdf_ocr(file):

    imagenes = convert_from_bytes(file.read())

    texto = ""

    for img in imagenes:
        texto += pytesseract.image_to_string(img)

    return texto


def buscar(texto, patron):

    r = re.search(patron, texto, re.IGNORECASE)

    if r:
        return r.group(1)

    return ""


def extraer_datos(texto, nombre):

    datos = {
        "archivo": nombre,
        "matricula": buscar(texto, r"Matr[ií]cula[: ]+([A-Z0-9\-\/]+)"),
        "provincia": buscar(texto, r"Provincia[: ]+([A-Za-zÁÉÍÓÚ ]+)"),
        "finca": buscar(texto, r"Finca[: ]+([0-9\-\/]+)"),
        "propietario": buscar(texto, r"Propietario[: ]+(.+?)C[eé]dula"),
        "cedula": buscar(texto, r"C[eé]dula[: ]+([0-9\-\.]+)"),
        "valor_fiscal": buscar(texto, r"Valor Fiscal[: ]+([₡0-9\., ]+)"),
    }

    return datos


def generar_excel(df):

    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    buffer.seek(0)

    return buffer


if uploaded_files:

    resultados = []

    for file in uploaded_files:

        st.write(f"Procesando {file.name}")

        texto = leer_pdf_texto(file)

        if not texto:

            st.warning("No se detectó texto. Aplicando OCR...")

            file.seek(0)

            texto = leer_pdf_ocr(file)

        datos = extraer_datos(texto, file.name)

        resultados.append(datos)

    df = pd.DataFrame(resultados)

    st.subheader("Vista previa")

    st.dataframe(df)

    excel = generar_excel(df)

    st.download_button(
        "Descargar Excel",
        data=excel,
        file_name="fincas.xlsx"
    )
