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


def normalizar_texto(texto: str) -> str:
    texto = texto.replace("\r", "\n")
    texto = texto.replace("|", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n+", "\n", texto)
    return texto.strip()


def normalizar_para_busqueda(texto: str) -> str:
    t = texto.upper()
    t = t.replace("\r", "\n")
    t = t.replace("|", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n+", "\n", t)

    reemplazos = {
        "INSCRIPCION": "INSCRIPCIÓN",
        "CEDULA": "CÉDULA",
        "ADQUISITIVA": "ADQUISITIVA",
        "ANTECEDENTES DOMINIO DE LA FINCA": "ANTECEDENTES DOMINIO DE LA FINCA",
    }

    for a, b in reemplazos.items():
        t = t.replace(a, b)

    return t.strip()


def limpiar_valor(valor: str) -> str:
    if not valor:
        return ""
    valor = re.sub(r"\s+", " ", valor)
    return valor.strip(" :-\n\t")


def buscar(texto: str, patron: str) -> str:
    m = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
    if m:
        return limpiar_valor(m.group(1))
    return ""


def buscar_primero(texto: str, patrones: list[str]) -> str:
    for patron in patrones:
        valor = buscar(texto, patron)
        if valor:
            return valor
    return ""


def extraer_bloque(texto: str, etiquetas_inicio: list[str], etiquetas_fin: list[str]) -> str:
    inicio_regex = r"(?:%s)" % "|".join(re.escape(e) for e in etiquetas_inicio)
    fin_regex = r"(?:%s)" % "|".join(re.escape(e) for e in etiquetas_fin)

    patron = rf"{inicio_regex}\s*:?\s*(.+?)(?=\s*{fin_regex}|\Z)"
    return buscar(texto, patron)


def extraer_bloque_anotaciones(texto: str) -> str:
    patrones = [
        r"ANOTACIONES\s*:?\s*(.+)",
        r"ANOTACION(?:ES)?\s*:?\s*(.+)",
    ]

    for patron in patrones:
        valor = buscar(texto, patron)
        if valor:
            return valor

    return ""


def detectar_hipoteca(texto: str, anotaciones: str) -> tuple[str, str]:
    texto_total = f"{texto}\n{anotaciones}"

    if re.search(r"\bH\s*I\s*P\s*O\s*T\s*E\s*C\s*A\b", texto_total, re.IGNORECASE):
        detalle = buscar(
            texto_total,
            r"(HIPOTECA.+?)(?=\n[A-ZÁÉÍÓÚÑ ]{4,}:|\Z)"
        )
        if not detalle:
            detalle = "Se detectó referencia a hipoteca."
        return "SI", detalle

    return "NO", ""


def extraer_cedula(texto: str) -> str:
    patrones = [
        r"CÉDULA\s+IDENTIDAD\s*:?\s*([0-9]{1,2}[- ][0-9]{4}[- ][0-9]{4})",
        r"CÉDULA\s+JUR[IÍ]DICA\s*:?\s*([0-9]{1,3}[- ][0-9]{3}[- ][0-9]{6})",
        r"CÉDULA\s*:?\s*([0-9]{1,3}[- ][0-9]{3,4}[- ][0-9]{4,6})",
        r"IDENTIDAD\s*:?\s*([0-9]{1,3}[- ][0-9]{3,4}[- ][0-9]{4,6})",
    ]

    valor = buscar_primero(texto, patrones)
    return valor.replace(" ", "-") if valor else ""


def extraer_datos(texto_original: str, nombre: str) -> dict:
    texto = normalizar_texto(texto_original)
    texto_busqueda = normalizar_para_busqueda(texto_original)

    matricula = buscar_primero(texto_busqueda, [
        r"MATRICULA\s*:?\s*([0-9]{1,10}\s*[-–—]+\s*[0-9]{1,5})",
        r"MATR[IÍ]CULA\s*:?\s*([0-9\-]+)",
    ])

    provincia = buscar_primero(texto_busqueda, [
        r"PROVINCIA\s*:?\s*([A-ZÁÉÍÓÚÑ]+)\s+FINCA\s*:?",
        r"PROVINCIA\s*:?\s*([A-ZÁÉÍÓÚÑ]+)",
    ])

    finca = buscar_primero(texto_busqueda, [
        r"FINCA\s*:?\s*([0-9]+)",
    ])

    derechos = buscar_primero(texto_busqueda, [
        r"DERECHO[S]?\s*:?\s*([0-9]+)",
        r"DERECHO\s*:?\s*([0-9]+)",
    ])

    antecedentes = extraer_bloque(
        texto_busqueda,
        etiquetas_inicio=[
            "ANTECEDENTES DOMINIO DE LA FINCA",
            "ANTECEDENTES DE LA FINCA",
            "ANTECEDENTES"
        ],
        etiquetas_fin=[
            "VALOR FISCAL",
            "PROPIETARIO",
            "CÉDULA",
            "CAUSA ADQUISITIVA",
            "FECHA DE INSCRIPCIÓN",
            "ANOTACIONES",
            "GRAVÁMENES",
            "OBSERVACIONES"
        ]
    )

    valor_fiscal = buscar_primero(texto_busqueda, [
        r"VALOR FISCAL\s*:?\s*([0-9\.,]+)\s*COLONES",
        r"VALOR FISCAL\s*:?\s*₡?\s*([0-9\.,]+)",
    ])

    propietario = extraer_bloque(
        texto_busqueda,
        etiquetas_inicio=["PROPIETARIO", "PROPIETARIA"],
        etiquetas_fin=[
            "CÉDULA",
            "CAUSA ADQUISITIVA",
            "FECHA DE INSCRIPCIÓN",
            "ESTADO CIVIL",
            "NACIONALIDAD",
            "DOMICILIO",
            "ANOTACIONES",
            "GRAVÁMENES"
        ]
    )

    cedula = extraer_cedula(texto_busqueda)

    causa_adquisitiva = extraer_bloque(
        texto_busqueda,
        etiquetas_inicio=["CAUSA ADQUISITIVA"],
        etiquetas_fin=[
            "FECHA DE INSCRIPCIÓN",
            "TOMO",
            "ASIENTO",
            "PRESENTACIÓN",
            "ANOTACIONES",
            "GRAVÁMENES",
            "OBSERVACIONES"
        ]
    )

    fecha_inscripcion = buscar_primero(texto_busqueda, [
        r"FECHA DE INSCRIPCI[ÓO]N\s*:?\s*([0-9]{1,2}[-/][A-Z]{3}[-/][0-9]{4})",
        r"FECHA DE INSCRIPCI[ÓO]N\s*:?\s*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})",
        r"FECHA DE INSCRIPCI[ÓO]N\s*:?\s*([0-9A-Z\-\/]+)",
    ])

    anotaciones = extraer_bloque_anotaciones(texto_busqueda)
    tiene_hipoteca, detalle_hipoteca = detectar_hipoteca(texto_busqueda, anotaciones)

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
        "anotaciones": anotaciones,
        "tiene_hipoteca": tiene_hipoteca,
        "detalle_hipoteca": detalle_hipoteca,
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
