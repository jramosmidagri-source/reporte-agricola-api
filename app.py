from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse
import pandas as pd
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime
import os

app = FastAPI(title="Generador de Reportes Agrícolas")

# ===========================
# 🖥️ INTERFAZ WEB PRINCIPAL
# ===========================
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Generador de Reportes Agrícolas</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f6f8;
                text-align: center;
                padding: 40px;
            }
            h1 {
                color: #2b4b6f;
            }
            button {
                background-color: #2b4b6f;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 18px;
                cursor: pointer;
                margin-top: 20px;
            }
            button:hover {
                background-color: #1e354f;
            }
            img {
                margin-top: 30px;
                max-width: 90%;
                border: 1px solid #ccc;
                border-radius: 10px;
                box-shadow: 0px 3px 8px rgba(0,0,0,0.15);
            }
        </style>
    </head>
    <body>
        <h1>📄 Generador de Reportes Agrícolas</h1>
        <p>Presiona el botón para generar el reporte más reciente desde Google Sheets.</p>
        <button onclick="generarReporte()">Generar Reporte</button>
        <div id="resultado"></div>

        <script>
            async function generarReporte() {
                document.getElementById('resultado').innerHTML = "<p>⏳ Generando reporte...</p>";
                try {
                    const res = await fetch('/generar');
                    if (!res.ok) throw new Error('Error al generar el reporte');
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    document.getElementById('resultado').innerHTML = `<img src="${url}" alt="Reporte generado">`;
                } catch (e) {
                    document.getElementById('resultado').innerHTML = "<p style='color:red;'>⚠️ Error al generar el reporte.</p>";
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ===========================
# ⚙️ ENDPOINT: GENERAR REPORTE
# ===========================
@app.get("/generar")
def generar_reporte():
    try:
        # === 1. Leer datos ===
        sheet_id = "1N2ZviQnjLIdTPARD2ksI47Wt-0Jzyjmndu4wtYqvc0k"
        sheet_name = "formulario de prueba"
        sheet_name_encoded = quote(sheet_name)
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_encoded}"
        df = pd.read_csv(url, encoding="utf-8")

        df = df.dropna(how="all")
        if "Marca temporal" in df.columns:
            df = df.drop(columns=["Marca temporal"])

        ultimo_registro = df.iloc[-1].to_dict()

        # === 2. Formato texto ===
        valor_raw = ultimo_registro.get("Número de Reporte (Sólo número correlativo)", "")
        try:
            numero_reporte_valor = int(float(str(valor_raw).strip()))
        except ValueError:
            numero_reporte_valor = 0

        anio_actual = datetime.now().year
        titulo_lineas = [
            f"REPORTE RÁPIDO N° {numero_reporte_valor}-{anio_actual}-",
            "SG-ODNGRD-COESMIDAGRI"
        ]

        fecha_valor = str(ultimo_registro.get("Fecha", "")).strip()
        hora_valor = str(ultimo_registro.get("Hora", "")).strip()
        fecha_hora_combinada = f"{fecha_valor} - {hora_valor} horas"

        # === Limpieza y formato de campos ===
        def formatear_valor(valor):
            """Convierte valores numéricos en texto legible y evita mostrar 'nan'."""
            if pd.isna(valor) or str(valor).strip().lower() in ["nan", "none", ""]:
                return ""  # evita mostrar 'nan' o espacios vacíos

            valor_str = str(valor).strip()

            # Si es un número (ej. 123456.0) → convertirlo a entero sin .0
            try:
                if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                    if float(valor).is_integer():
                        return str(int(valor))
                    else:
                        return str(valor)
                # Si el string representa un número entero, limpiar el .0
                elif valor_str.replace(".", "", 1).isdigit():
                    if valor_str.endswith(".0"):
                        return valor_str[:-2]
                    return valor_str
                else:
                    return valor_str  # texto (ej. "En proceso")
            except Exception:
                return valor_str
        campos_texto = {
            "Tipo de evento": formatear_valor(ultimo_registro.get("Tipo de evento", "")),
            "Fecha y Hora": formatear_valor(fecha_hora_combinada),
            "Lugar": formatear_valor(ultimo_registro.get("Lugar (Departamento/Provincia/Distrito/Centro Poblado-caserío-etc)", "")),
            "Afectación Preliminar": formatear_valor(ultimo_registro.get("Afectación Preliminar", "")),
            "Acción Local": formatear_valor(ultimo_registro.get("Acción Local", "")),
            "Acción Sectorial": formatear_valor(ultimo_registro.get("Acción Sectorial", "")),
            "Código SINPAD": formatear_valor(ultimo_registro.get("Código SINPAD", "")),
            "Fuente": formatear_valor(ultimo_registro.get("Fuente", ""))
        }
            
        texto_final = ""
        for i, (titulo, valor) in enumerate(campos_texto.items(), start=1):
            texto_final += f"{i}. {titulo}:\n{valor}\n\n"

        # === 3. Imagen base ===
        drive_link = "https://drive.google.com/file/d/1NfH4W8DiOtVnaz2pSf11goWHEpiKmFlH/view?usp=sharing"  # nuevo enlace
        file_id = drive_link.split("/d/")[1].split("/")[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        img = Image.open(BytesIO(response.content)).convert("RGB")
        draw = ImageDraw.Draw(img)


        # === 4. Fuentes personalizadas ===
        base_path = os.path.dirname(os.path.abspath(__file__))
        font_regular_path = os.path.join(base_path, "fonts", "Poppins-Regular.ttf")
        font_bold_path = os.path.join(base_path, "fonts", "Poppins-Bold.ttf")

        def safe_font(path, size):
            try:
                return ImageFont.truetype(path, size, encoding="utf-8")
            except Exception:
                return ImageFont.load_default()

        font_title = safe_font(font_bold_path, 22)
        font_body = safe_font(font_regular_path, 22)
        font_bold = safe_font(font_bold_path, 21)

        # === 5. Configuración del texto ===
        x0, y0 = 280, 250
        x1, y1 = 810, 480
        max_width = x1 - x0
        line_spacing = 8

        def get_text_width(draw, text, font):
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0, 0), text, font=font)
                return bbox[2] - bbox[0]
            else:
                w, _ = draw.textsize(text, font=font)
                return w

        def wrap_text(draw, text, font, max_width):
            lines = []
            for paragraph in text.split("\n"):
                words = paragraph.split(" ")
                line = ""
                for word in words:
                    test_line = line + word + " "
                    w = get_text_width(draw, test_line, font)
                    if w <= max_width:
                        line = test_line
                    else:
                        lines.append(line.strip())
                        line = word + " "
                lines.append(line.strip())
            return lines

        # === 6. NUEVA FUNCIÓN corregida ===
        def draw_wrapped_report(draw, text, x, y, font_normal, font_bold, fill, max_width, line_spacing):
            """Dibuja bloques con título en negrita y valores normales, incluso si están vacíos o son texto."""
            for bloque in text.strip().split("\n\n"):
                if not bloque.strip():
                    continue

                lineas = bloque.split("\n", 1)
                titulo_linea = lineas[0]
                valor_linea = lineas[1] if len(lineas) > 1 else ""

                # Título en negrita
                wrapped_title = wrap_text(draw, titulo_linea, font_bold, max_width)
                for line in wrapped_title:
                    draw.text((x, y), line, font=font_bold, fill=fill)
                    y += font_bold.getbbox(line)[3] + line_spacing

                # Valor normal (si existe)
                if valor_linea.strip():
                    wrapped_value = wrap_text(draw, valor_linea, font_normal, max_width)
                    for line in wrapped_value:
                        draw.text((x, y), line, font=font_normal, fill=fill)
                        y += font_normal.getbbox(line)[3] + line_spacing

                y += line_spacing
            return y

        # === 7. Dibuja título centrado ===
        y_text = y0 + 10
        for linea in titulo_lineas:
            linea_width = get_text_width(draw, linea, font_title)
            linea_x = x0 + (max_width - linea_width) / 2 - 5
            draw.text((linea_x, y_text), linea, font=font_title, fill="black")
            y_text += font_title.getbbox(linea)[3] + 4

        # === 8. Dibuja cuerpo ===
        draw_wrapped_report(draw, texto_final, x0 + 15, y_text + 30, font_body, font_bold, "black", max_width - 30, line_spacing)

        # === 9. Retornar imagen ===
        output_buffer = BytesIO()
        img.save(output_buffer, format="PNG")
        return Response(content=output_buffer.getvalue(), media_type="image/png")

    except Exception as e:
        return HTMLResponse(content=f"<h3 style='color:red;'>⚠️ Error: {e}</h3>")
