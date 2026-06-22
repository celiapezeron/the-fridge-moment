#!/usr/bin/env python3
"""
Publication programmee pour The Fridge Moment.

Verifie chaque brouillon dans drafts/, et si sa publish_date est arrivee
(aujourd'hui ou avant), deplace le fichier vers articles/, l'ajoute
a la page d'accueil index.html, et ajoute son URL a sitemap.xml.

Ce script est lance automatiquement chaque jour par GitHub Actions.
"""

import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = ROOT / "drafts"
ARTICLES_DIR = ROOT / "articles"
INDEX_FILE = ROOT / "index.html"
SITEMAP_FILE = ROOT / "sitemap.xml"
SITE_BASE_URL = "https://celiapezeron.github.io/the-fridge-moment"

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

METADATA_BLOCK_RE = re.compile(r"<!--\s*(.*?)\s*-->", re.DOTALL)
FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)


def parse_metadata(text):
    match = METADATA_BLOCK_RE.search(text)
    if not match:
        return None
    fields = dict(FIELD_RE.findall(match.group(1)))
    return fields


def strip_metadata_block(text):
    return METADATA_BLOCK_RE.sub("", text, count=1).lstrip("\n")


def build_article_card(meta):
    return (
        f'    <a href="articles/{meta["filename"]}" class="article-card">\n'
        f'      <div class="article-meta">{meta["meta"]}</div>\n'
        f'      <h2>{meta["title"]}</h2>\n'
        f'      <p class="article-excerpt">{meta["excerpt"]}</p>\n'
        f"    </a>\n\n"
    )


def insert_card_into_index(card_html):
    index_text = INDEX_FILE.read_text(encoding="utf-8")
    marker = '<section class="article-list">\n'
    idx = index_text.find(marker)
    if idx == -1:
        raise RuntimeError("Marqueur <section class=\"article-list\"> introuvable dans index.html")
    insert_at = idx + len(marker) + 1
    new_text = index_text[:insert_at] + card_html + index_text[insert_at:]
    INDEX_FILE.write_text(new_text, encoding="utf-8")


def add_url_to_sitemap(filename):
    article_url = f"{SITE_BASE_URL}/articles/{filename}"

    ET.register_namespace("", SITEMAP_NS)
    tree = ET.parse(SITEMAP_FILE)
    root = tree.getroot()

    for existing_url in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc = existing_url.find(f"{{{SITEMAP_NS}}}loc")
        if loc is not None and loc.text == article_url:
            print(f"Deja present dans sitemap.xml : {article_url}")
            return

    new_url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
    loc = ET.SubElement(new_url, f"{{{SITEMAP_NS}}}loc")
    loc.text = article_url
    changefreq = ET.SubElement(new_url, f"{{{SITEMAP_NS}}}changefreq")
    changefreq.text = "monthly"
    priority = ET.SubElement(new_url, f"{{{SITEMAP_NS}}}priority")
    priority.text = "0.8"

    ET.indent(tree, space="  ")
    tree.write(SITEMAP_FILE, encoding="UTF-8", xml_declaration=True)
    print(f"Ajoute a sitemap.xml : {article_url}")


def publish_draft(draft_path, meta):
    text = draft_path.read_text(encoding="utf-8")
    cleaned = strip_metadata_block(text)
    target = ARTICLES_DIR / meta["filename"]
    target.write_text(cleaned, encoding="utf-8")
    draft_path.unlink()
    insert_card_into_index(build_article_card(meta))
    add_url_to_sitemap(meta["filename"])
    print(f"Publie : {meta['filename']} (programme pour le {meta['publish_date']})")


def main():
    if not DRAFTS_DIR.exists():
        print("Aucun dossier drafts/ trouve, rien a faire.")
        return

    today = date.today()
    published_count = 0

    for draft_path in sorted(DRAFTS_DIR.glob("*.html")):
        if draft_path.name.startswith("_"):
            continue

        text = draft_path.read_text(encoding="utf-8")
        meta = parse_metadata(text)

        if not meta or "publish_date" not in meta:
            print(f"Ignore (pas de metadonnees valides) : {draft_path.name}")
            continue

        try:
            publish_date = date.fromisoformat(meta["publish_date"].strip())
        except ValueError:
            print(f"Ignore (date invalide) : {draft_path.name}")
            continue

        if publish_date <= today:
            required_fields = {"title", "excerpt", "meta", "filename"}
            missing = required_fields - meta.keys()
            if missing:
                print(f"Ignore (champs manquants {missing}) : {draft_path.name}")
                continue
            publish_draft(draft_path, meta)
            published_count += 1
        else:
            print(f"Pas encore du : {draft_path.name} (prevu le {publish_date})")

    if published_count == 0:
        print("Aucun article a publier aujourd'hui.")
    else:
        print(f"{published_count} article(s) publie(s).")


if __name__ == "__main__":
    main()
