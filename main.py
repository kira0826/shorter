"""
main.py — Consolida N carpetas de PDFs en un único PDF final con cortes por rango.

Antes de los PDFs de cada carpeta inserta una página de portada con el nombre
de la carpeta. De cada PDF solo se extraen las páginas indicadas por los rangos,
consolidadas en orden en el PDF final.

Si NO se pasan rangos, se incluyen TODAS las páginas de cada PDF.

Uso:
    python main.py <carpeta_raiz> <archivo_salida.pdf> [rango1] [rango2] ...

Argumentos:
    carpeta_raiz        Carpeta que contiene las subcarpetas con PDFs.
    archivo_salida.pdf  Ruta del PDF final consolidado.
    rangos              (Opcional) Páginas o rangos a extraer. Formato: N o N-M

Ejemplos:
    # Sin rangos: incluye todas las páginas
    python main.py ./data/zona01 ./salida.pdf

    # Con rangos: solo extrae esas páginas de cada PDF
    python main.py ./data/zona01 ./salida.pdf 1-5 6-10
    python main.py ./data/zona01 ./salida.pdf 1 3 5
    python main.py ./data/zona01 ./salida.pdf 1-3 7 10-12
"""

import sys
import os
import io
import glob
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def make_cover_page(folder_name: str) -> PdfReader:
    buffer = io.BytesIO()
    width, height = letter

    c = canvas.Canvas(buffer, pagesize=letter)

    # Fondo oscuro
    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # Franja lateral izquierda
    c.setFillColor(colors.HexColor("#e94560"))
    c.rect(0, 0, 12, height, fill=True, stroke=False)

    # Líneas decorativas
    c.setFillColor(colors.HexColor("#e94560"))
    c.rect(40, height - 80, width - 80, 3, fill=True, stroke=False)
    c.rect(40, 80, width - 80, 3, fill=True, stroke=False)

    # Etiqueta
    c.setFillColor(colors.HexColor("#e94560"))
    c.setFont("Helvetica", 11)
    c.drawString(40, height - 110, "SECCIÓN")

    # Nombre de carpeta (título)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 36)

    max_width = width - 80
    words = folder_name.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if c.stringWidth(test, "Helvetica-Bold", 36) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_height = 44
    total_text_height = len(lines) * line_height
    y_start = (height / 2) + (total_text_height / 2)

    for i, line in enumerate(lines):
        c.drawString(40, y_start - i * line_height, line)

    # Pie
    c.setFillColor(colors.HexColor("#aaaaaa"))
    c.setFont("Helvetica", 9)
    c.drawString(40, 55, folder_name)

    c.save()
    buffer.seek(0)
    return PdfReader(buffer)


def parse_range(range_str: str, total_pages: int) -> list[int] | None:
    """Convierte 'N' o 'N-M' a lista de índices 0-based. None si está fuera de rango."""
    range_str = range_str.strip()
    if "-" in range_str:
        parts = range_str.split("-")
        if len(parts) != 2:
            raise ValueError(f"Rango inválido: '{range_str}'. Usa el formato N o N-M.")
        start, end = int(parts[0]), int(parts[1])
    else:
        start = end = int(range_str)

    if start < 1 or start > end:
        raise ValueError(f"Rango inválido: '{range_str}'.")

    if end > total_pages:
        print(f"       ⚠️  Rango '{range_str}' excede las {total_pages} páginas — omitido.")
        return None

    return list(range(start - 1, end))


def get_page_indices(reader: PdfReader, ranges: list[str]) -> list[int]:
    """
    Retorna los índices 0-based de las páginas a incluir.
    Si no hay rangos, retorna todas las páginas.
    """
    total = len(reader.pages)
    if not ranges:
        return list(range(total))

    indices = []
    for r in ranges:
        result = parse_range(r, total)
        if result:
            indices.extend(result)
    return indices


def consolidate(root_folder: str, output_path: str, ranges: list[str]) -> None:
    if not os.path.isdir(root_folder):
        raise NotADirectoryError(f"La carpeta raíz no existe: {root_folder}")

    subfolders = sorted([
        f for f in os.scandir(root_folder) if f.is_dir()
    ], key=lambda f: f.name.lower())

    if not subfolders:
        print(f"⚠️  No se encontraron subcarpetas en: {root_folder}")
        return

    writer = PdfWriter()
    total_pdfs = 0
    total_pages = 0

    range_label = " | ".join(ranges) if ranges else "todas las páginas"
    print(f"📂 Carpeta raíz : {os.path.abspath(root_folder)}")
    print(f"📄 Salida       : {os.path.abspath(output_path)}")
    print(f"📋 Cortes       : {range_label}")
    print(f"🗂️  Subcarpetas  : {len(subfolders)}\n")

    for folder in subfolders:
        pdf_files = sorted(glob.glob(os.path.join(folder.path, "*.pdf")))
        print(f"  📁 {folder.name}  ({len(pdf_files)} PDF(s))")

        # Portada de sección
        cover = make_cover_page(folder.name)
        writer.add_page(cover.pages[0])
        total_pages += 1

        for pdf_path in pdf_files:
            try:
                reader = PdfReader(pdf_path)
                indices = get_page_indices(reader, ranges)

                if not indices:
                    print(f"     ⚠️  {os.path.basename(pdf_path)} — ninguna página válida, omitido.")
                    continue

                for idx in indices:
                    writer.add_page(reader.pages[idx])

                total_pdfs += 1
                total_pages += len(indices)
                pages_info = f"{len(indices)} pág." if ranges else f"{len(reader.pages)} pág."
                print(f"     ✅ {os.path.basename(pdf_path)}  ({pages_info})")

            except Exception as e:
                print(f"     ❌ {os.path.basename(pdf_path)} — {e}")

        print()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"🎉 Consolidado listo.")
    print(f"   {len(subfolders)} sección(es)  |  {total_pdfs} PDF(s)  |  {total_pages} página(s) en total")
    print(f"   → {os.path.abspath(output_path)}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    root_folder = sys.argv[1]
    output_path = sys.argv[2]
    ranges      = sys.argv[3:]  # opcional

    try:
        consolidate(root_folder, output_path, ranges)
    except (NotADirectoryError, ValueError) as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()