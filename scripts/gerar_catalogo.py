"""Gera public/data/catalogo.json a partir de dados/fonte.json.

Uso: python3 scripts/gerar_catalogo.py
Cada entrada de "paginas" pode ser um caminho /manus-storage/... ou /midias/...
"""

import json
import unicodedata
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "dados" / "fonte.json"
SAIDA = RAIZ / "public" / "data" / "catalogo.json"

SECOES = [
    ("hinos", "Hinos", "Novo Cântico", "numero"),
    ("canticos", "Cânticos espirituais", "Ordem alfabética", "alfabeto"),
    ("salmos", "Salmos", "Livro dos Salmos", "numero"),
    ("palavra", "Palavra de Deus Cantada", "Passagens bíblicas cantadas", "alfabeto"),
    ("lavras", "Músicas Lavras", "Canções do retiro", "alfabeto"),
]


def sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def slug(texto: str) -> str:
    limpo = sem_acento(texto).lower()
    return "-".join("".join(c if c.isalnum() else " " for c in limpo).split())


def montar_item(secao: str, dado: dict) -> dict:
    num = dado.get("num")
    titulo = dado["titulo"].strip()
    if secao == "hinos":
        ident = f"hino-{num}"
        alt_base = f"Hino {num} — {titulo}"
    elif secao == "lavras":
        ident = f"lavras-{slug(titulo)}"
        alt_base = titulo
    elif secao == "palavra":
        ident = f"palavra-{slug(titulo)}"
        alt_base = titulo
    elif secao == "salmos":
        ident = dado.get("id") or f"salmo-{num}"
        alt_base = f"Salmo {num} — {titulo}"
    else:
        ident = f"cantico-{slug(titulo)}"
        alt_base = titulo

    paginas = []
    for i, pg in enumerate(dado.get("paginas", []), start=1):
        img = pg["img"] if isinstance(pg, dict) else pg
        tom = pg.get("tom") if isinstance(pg, dict) else None
        paginas.append(
            {
                "img": img,
                "alt": f"{alt_base} — página {i}",
                **({"tom": tom} if tom else {}),
            }
        )

    item = {"id": ident, "titulo": titulo, "paginas": paginas}
    if num is not None:
        item["num"] = int(num)
    if dado.get("versiculos"):
        item["versiculos"] = dado["versiculos"]
    if dado.get("rotulo"):
        item["rotulo"] = dado["rotulo"]
    if dado.get("tom"):
        item["tom"] = dado["tom"]
    if dado.get("obs"):
        item["obs"] = dado["obs"]
    return item


def main() -> None:
    fonte = json.loads(FONTE.read_text(encoding="utf-8"))
    secoes = []
    for chave, titulo, subtitulo, ordem in SECOES:
        itens = [montar_item(chave, d) for d in fonte.get(chave, [])]
        secoes.append(
            {
                "id": chave,
                "titulo": titulo,
                "subtitulo": subtitulo,
                "ordem": ordem,
                "itens": itens,
            }
        )
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(
            {"geradoEm": date.today().isoformat(), "secoes": secoes},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    resumo = ", ".join(f"{s['id']}: {len(s['itens'])}" for s in secoes)
    print(f"catálogo gerado ({resumo})")


if __name__ == "__main__":
    main()
