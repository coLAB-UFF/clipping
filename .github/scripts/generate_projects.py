#!/usr/bin/env python3
"""
generate_projects.py <clippings.json> <output_dir>

Lê o JSON retornado pelo Apps Script doGet() e (re)gera todos os
arquivos Jekyll _projects/*.md com frontmatter YAML correto.

A pasta de saída é limpa antes da geração — _projects/ torna-se
um artefato de build, não mais editado manualmente.
"""

import json
import os
import re
import sys
from pathlib import Path

# ── Templates do corpo do MD ──────────────────────────────────

SHARE_DIV = (
    '<div class="post__share"><ul class="share__list list-reset">'
    'ACESSE A NOTÍCIA COMPLETA'
    '<li class="share__item" style="margin-left: 10px">'
    '<a class="share__link share__facebook" style="background: #fa5657" '
    'href="{link}" title="Link" rel="nofollow">'
    '<i class="fa-solid fa-link"></i></a></li></ul></div>'
)

GALLERY_COMMENT = (
    '<!-- <div class="gallery-box"><div class="gallery">'
    '<img src="/clipping/images/example-1.jpg" loading="lazy" alt="Project">'
    '<img src="/clipping/images/example-2.jpg" loading="lazy" alt="Project">'
    '</div><em>Gallery / '
    '<a href="https://www.freepik.com/" target="_blank">Freepic</a>'
    '</em></div> -->'
)

# ── YAML helpers ──────────────────────────────────────────────

# Chars que exigem quoting quando aparecem no início de um valor YAML
_YAML_SPECIAL_START = set(':#{}&*!|>\'"[]-@`')

# Palavras reservadas YAML que precisam de quoting
_YAML_RESERVED = {'true', 'false', 'null', 'yes', 'no', 'on', 'off', '~'}


def yaml_scalar(value: str) -> str:
    """
    Retorna uma representação YAML segura para um valor string.
    Aplica quoting somente quando necessário para minimizar diff ruidoso.
    """
    if not value:
        return ''

    needs_quoting = (
        value.lower() in _YAML_RESERVED
        or value[0] in _YAML_SPECIAL_START
        or value[-1] == ':'
        or ': ' in value
        or value.startswith('- ')
        or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value)  # chars de controle
    )

    if not needs_quoting:
        return value

    # Prefere aspas simples; se o valor contém aspas simples, usa duplas.
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    # Ambos os tipos: usa simples e escapa ' como ''
    return "'" + value.replace("'", "''") + "'"


def image_yaml(path: str) -> str:
    """
    URLs externas (http/https) ficam como scalar simples.
    Caminhos internos são sempre envolvidos em aspas simples —
    consistente com os arquivos existentes e necessário para nomes com espaço.
    """
    if not path:
        return "''"
    if path.startswith(('http://', 'https://')):
        return yaml_scalar(path)  # deixa yaml_scalar decidir o quoting
    return "'" + path.replace("'", "''") + "'"


# ── Geração do MD ─────────────────────────────────────────────

def build_md(row: dict) -> str:
    arquivo   = row.get('arquivo', '')
    titulo    = row.get('titulo', '').strip()
    categoria = row.get('categoria', '').strip()
    descricao = row.get('descricao', '').strip()
    fonte     = row.get('fonte', '').strip()
    pais      = row.get('pais', '').strip()
    autor     = row.get('autor', '').strip()
    data      = row.get('data', '').strip()
    imagem    = row.get('imagem', '').strip()
    link      = row.get('link', '').strip()
    trecho    = row.get('trecho', '').strip()
    tags      = row.get('tags', '').strip()

    lines = [
        '---',
        f'title: {yaml_scalar(titulo)}',
        f'subtitle: {yaml_scalar(categoria)}',
        f'summary: {yaml_scalar(descricao)}',
        f'client: {yaml_scalar(fonte)}',
        f'country: {yaml_scalar(pais)}',
        f'tools: {yaml_scalar(autor)}',
        f'date: {data}',
        f'tags: {yaml_scalar(tags)}',
        f'image: {image_yaml(imagem)}',
        f'link: {yaml_scalar(link)}',
        '---',
        '',
    ]

    if trecho:
        lines.append(trecho)
        lines.append('')

    if link:
        lines.append(SHARE_DIV.format(link=link))

    lines.append(GALLERY_COMMENT)
    lines.append('')

    return '\n'.join(lines)


# ── Main ──────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 3:
        print(f'Uso: {sys.argv[0]} <clippings.json> <pasta_destino>')
        sys.exit(1)

    json_path  = sys.argv[1]
    output_dir = Path(sys.argv[2])

    # Lê JSON
    with open(json_path, encoding='utf-8') as f:
        rows = json.load(f)

    if not isinstance(rows, list):
        print(f'ERRO: JSON deve ser uma lista, recebeu {type(rows).__name__}', file=sys.stderr)
        sys.exit(1)

    # Limpa arquivos MD existentes (agora são artefatos gerados)
    removed = 0
    for existing in output_dir.glob('*.md'):
        existing.unlink()
        removed += 1
    if removed:
        print(f'Removidos {removed} arquivos MD antigos.')

    # Gera novos arquivos
    generated = 0
    skipped   = 0
    for row in rows:
        arquivo = row.get('arquivo', '').strip()
        titulo  = row.get('titulo',  '').strip()

        if not arquivo:
            print(f'AVISO: linha sem "arquivo", ignorando ({titulo or "sem título"})')
            skipped += 1
            continue

        # Valida formato do nome de arquivo
        if not re.match(r'^clipping\d{5}$', arquivo):
            print(f'AVISO: formato inesperado "{arquivo}", ignorando')
            skipped += 1
            continue

        md_content = build_md(row)
        out_path   = output_dir / f'{arquivo}.md'
        out_path.write_text(md_content, encoding='utf-8')
        generated += 1

    print(f'Gerados {generated} arquivos MD em {output_dir}' +
          (f' ({skipped} ignorados)' if skipped else ''))


if __name__ == '__main__':
    main()
