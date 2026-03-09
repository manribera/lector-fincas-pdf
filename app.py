import io
import re
import pandas as pd
import streamlit as st
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="Lector de Fincas PDF", layout="wide")

st.title("📄 Lector de Fincas del Registro")
st.write(
    "Suba uno o varios PDFs del Registro de la Propiedad. "
    "La app extraerá la información y generará un archivo Excel automáticamente."
)

uploaded_files = st.file_uploader(
    "Cargar archivos PDF",
    type=["pdf"],
    accept_multiple_files=True
)


def leer_pdf_texto(file) -> str:
    reader = PdfReader(file)
    texto = ""

    for page in reader.pages:
        contenido = page.extract_text()
        if contenido:
            texto += contenido + "\n"

    return texto.strip()


def leer_pdf_ocr(file) -> str:
    imagenes = convert_from_bytes(file.read())
    texto = ""

    for img in imagenes:
        texto += pytesseract.image_to_string(img, lang="eng") + "\n"

    return texto.strip()


def limpiar_texto(texto: str) -> str:
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n+", "\n", texto)
    return texto.strip()


def buscar(texto: str, patron: str) -> str:
    r = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
    if r:
        return r.group(1).strip()
    return ""


def extraer_datos(texto: str, nombre: str) -> dict:
    texto = limpiar_texto(texto)

    matricula = buscar(texto, r"MATRICULA:\s*([0-9\-]+)")
    provincia = buscar(texto, r"PROVINCIA:\s*([A-ZÁÉÍÓÚÑ]+)\s+FINCA:")
    finca = buscar(texto, r"FINCA:\s*([0-9]+)")
    derechos = buscar(texto, r"DERECHO:\s*([0-9]+)")

    antecedentes = buscar(
        texto,
        r"ANTECEDENTES DOMINIO DE LA FINCA:\s*(.+?)\s*VALOR FISCAL:"
    )

    propietario = buscar(
        texto,
        r"PROPIETARIO:\s*(.+?)\s*CEDULA"
    )

    cedula = buscar(
        texto,
        r"CEDULA\s+IDENTIDAD\s*([0-9\-]+)"
    )

    valor_fiscal = buscar(
        texto,
        r"VALOR FISCAL:\s*([0-9\.,]+)\s*COLONES"
    )

    causa_adquisitiva = buscar(
        texto,
        r"CAUSA ADQUISITIVA:\s*(.+?)\s*FECHA DE INSCRIPCI"
    )

    fecha_inscripcion = buscar(
        texto,
        r"FECHA DE INSCRIPCI[ÓO]N:\s*([0-9A-Z\-]+)"
    )

    return {
        "archivo": nombre,
        "matricula": matricula,
        "provincia": provincia,
        "finca": finca,
        "derechos": derechos,
        "antecedentes": antecedentes,
        "valor_fiscal": valor_fiscal,
        "propietario": propietario,
        "cedula": cedula,
        "fecha_inscripcion": fecha_inscripcion,
        "causa_adquisitiva": causa_adquisitiva,
    }


def generar_excel(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultados")

    buffer.seek(0)
    return buffer


if uploaded_files:
    resultados = []

    for file in uploaded_files:
        st.write(f"Procesando {file.name}")

        try:
            file.seek(0)
            texto = leer_pdf_texto(file)

            if not texto:
                st.warning("No se detectó texto. Aplicando OCR...")
                file.seek(0)
                texto = leer_pdf_ocr(file)

            datos = extraer_datos(texto, file.name)
            resultados.append(datos)

        except Exception as e:
            st.error(f"Error procesando {file.name}: {e}")

    if resultados:
        df = pd.DataFrame(resultados)

        st.subheader("Vista previa")
        st.dataframe(df, use_container_width=True)

        excel = generar_excel(df)

        st.download_button(
            label="Descargar Excel",
            data=excel,
            file_name="fincas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("Suba uno o varios archivos PDF para comenzar.")
