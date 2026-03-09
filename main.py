"""
pdf_splitter.py — Extrae y consolida páginas de todos los PDFs de una carpeta.

Los rangos/páginas indicados se extraen de cada PDF y se unen en UN SOLO PDF
de salida por archivo. El orden de las páginas en el output respeta el orden
en que se pasan los rangos.

Uso:
    python pdf_splitter.py <carpeta_entrada> <carpeta_salida> <rango1> [rango2] ...

Argumentos:
    carpeta_entrada   Carpeta con los archivos .pdf a procesar.
    carpeta_salida    Carpeta donde se guardarán los PDFs resultantes.
    rangos            Páginas o rangos a incluir. Formato:  N  o  N-M

Ejemplos:
    # Extrae páginas 1-5 y 11-20 de cada PDF (un solo PDF de salida por archivo)
    python pdf_splitter.py ./documentos ./output 1-5 11-20

    # Páginas sueltas
    python pdf_splitter.py ./documentos ./output 1 3 5 7

    # Mezcla libre
    python pdf_splitter.py ./documentos ./output 1-3 7 10-12
"""

import sys
import os
import glob
from pypdf import PdfReader, PdfWriter


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
        print(f"    ⚠️  Rango '{range_str}' excede las {total_pages} páginas — omitido.")
        return None

    return list(range(start - 1, end))  # 0-based


def extract_pages(input_path: str, output_dir: str, ranges: list[str]) -> bool:
    """
    Extrae las páginas indicadas por los rangos y las consolida en UN solo PDF.
    Retorna True si se generó el archivo, False si no hubo páginas válidas.
    """
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    print(f"\n  📄 {os.path.basename(input_path)}  ({total_pages} pág.)")

    writer = PdfWriter()
    included = []

    for range_str in ranges:
        try:
            page_indices = parse_range(range_str, total_pages)
        except ValueError as e:
            print(f"    ❌ {e}")
            continue

        if page_indices is None:
            continue

        for idx in page_indices:
            writer.add_page(reader.pages[idx])
            included.append(idx + 1)  # 1-based para el log

    if not included:
        print(f"    ⚠️  Ninguna página válida — archivo omitido.")
        return False

    out_path = os.path.join(output_dir, f"{base_name}_recortado.pdf")
    with open(out_path, "wb") as f:
        writer.write(f)

    pages_summary = ", ".join(str(p) for p in included)
    print(f"    ✅ {len(included)} página(s) incluida(s): [{pages_summary}]")
    print(f"       → {os.path.basename(out_path)}")
    return True


def process_folder(input_folder: str, output_folder: str, ranges: list[str]) -> None:
    if not os.path.isdir(input_folder):
        raise NotADirectoryError(f"La carpeta de entrada no existe: {input_folder}")

    pdf_files = sorted(glob.glob(os.path.join(input_folder, "*.pdf")))

    if not pdf_files:
        print(f"⚠️  No se encontraron archivos .pdf en: {input_folder}")
        return

    os.makedirs(output_folder, exist_ok=True)

    print(f"📂 Entrada  : {os.path.abspath(input_folder)}")
    print(f"📂 Salida   : {os.path.abspath(output_folder)}")
    print(f"📋 Selección: {' | '.join(ranges)}")
    print(f"🗂️  PDFs     : {len(pdf_files)}")

    generated = sum(
        extract_pages(pdf_path, output_folder, ranges)
        for pdf_path in pdf_files
    )

    print(f"\n🎉 {generated}/{len(pdf_files)} PDF(s) generado(s) en: {os.path.abspath(output_folder)}")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    input_folder  = sys.argv[1]
    output_folder = sys.argv[2]
    ranges        = sys.argv[3:]

    try:
        process_folder(input_folder, output_folder, ranges)
    except (NotADirectoryError, ValueError) as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()