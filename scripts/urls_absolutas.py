"""Converte as imagens /manus-storage/... em URLs absolutas do site publicado,
para o app funcionar hospedado em outro lugar (GitHub Pages, Vercel etc.).

Uso: python3 scripts/urls_absolutas.py https://hinario-fql7afdj.manus.space
"""
import json
import sys
from pathlib import Path

dominio = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://hinario-fql7afdj.manus.space"
fonte = Path(__file__).resolve().parent.parent / "dados" / "fonte.json"
dados = json.loads(fonte.read_text(encoding="utf-8"))

trocadas = 0
for secao in dados.values():
    for item in secao:
        novas = []
        for pg in item.get("paginas", []):
            alvo = pg if isinstance(pg, str) else pg.get("img", "")
            if alvo.startswith("/"):
                novo = dominio + alvo
                trocadas += 1
                if isinstance(pg, str):
                    pg = novo
                else:
                    pg["img"] = novo
            novas.append(pg)
        item["paginas"] = novas

fonte.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{trocadas} imagens agora apontam para {dominio}")
