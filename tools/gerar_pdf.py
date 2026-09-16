"""Converte o relatório Markdown em PDF usando o Chrome em modo headless.

Não faz parte da entrega: é ferramenta de build. Rodar da raiz do projeto:
    .venv/bin/python tools/gerar_pdf.py
"""

import subprocess
import tempfile
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parents[1]
ORIGEM = RAIZ / "entrega-fase1" / "docs" / "relatorio.md"
DESTINO = RAIZ / "entrega-fase1" / "docs" / "relatorio.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

ESTILO = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
       font-size: 10.5pt; line-height: 1.55; color: #16181d; }
h1 { font-size: 20pt; border-bottom: 2px solid #c8102e; padding-bottom: 6px; }
h2 { font-size: 15pt; margin-top: 26px; color: #c8102e; }
h3 { font-size: 12pt; margin-top: 18px; }
h2, h3 { page-break-after: avoid; }
code, pre { font-family: 'SF Mono', Menlo, monospace; font-size: 8.5pt; }
pre { background: #f5f6f8; border: 1px solid #e0e2e7; border-radius: 4px;
      padding: 10px; white-space: pre-wrap; word-wrap: break-word;
      page-break-inside: avoid; }
table { border-collapse: collapse; width: 100%; margin: 12px 0;
        page-break-inside: avoid; }
th, td { border: 1px solid #c9ccd2; padding: 5px 8px; text-align: left; }
th { background: #f0f1f4; }
blockquote { border-left: 3px solid #c8102e; margin-left: 0;
             padding-left: 14px; color: #4a4e57; }
"""


def main() -> None:
    texto = ORIGEM.read_text(encoding="utf-8")
    corpo = markdown.markdown(
        texto, extensions=["tables", "fenced_code", "toc", "sane_lists"]
    )
    html = (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
            f"<title>Relatório Aurora-1</title><style>{ESTILO}</style></head>"
            f"<body>{corpo}</body></html>")

    with tempfile.TemporaryDirectory() as tmp:
        caminho_html = Path(tmp) / "relatorio.html"
        caminho_html.write_text(html, encoding="utf-8")
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={DESTINO}", caminho_html.as_uri()],
            check=True, capture_output=True,
        )
    print(f"PDF gerado: {DESTINO} ({DESTINO.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
