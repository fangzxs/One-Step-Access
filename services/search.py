from __future__ import annotations

import re
from urllib.parse import urlparse

from services.catalog import category_name_map, site_category_slugs
from utils.converters import to_int

def normalize_search_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def domain_from_url(site_url: str) -> str:
    parsed = urlparse(site_url if "://" in site_url else f"https://{site_url}")
    return parsed.netloc or parsed.path


def acronym(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value)
    if len(words) >= 2:
        return "".join(word[0] for word in words).lower()
    return "".join(words).lower()


def search_score(site: dict, terms: list[str], categories_by_slug: dict[str, str]) -> int:
    """按匹配位置给搜索结果打分，分数越高越靠前。"""
    name = normalize_search_text(site.get("name"))
    description = normalize_search_text(site.get("description"))
    category_name = normalize_search_text(
        " ".join(categories_by_slug.get(slug, slug) for slug in site_category_slugs(site))
    )
    tags = [normalize_search_text(tag) for tag in site.get("tags", [])]
    domain = normalize_search_text(domain_from_url(str(site.get("url", ""))))
    name_acronym = acronym(str(site.get("name", "")))

    score = 0
    for term in terms:
        if not term:
            continue
        # 名称匹配最能代表用户意图，因此权重最高；缩写匹配用于支持如
        # "ps" 搜到 Photoshop 这类输入。
        if term == name:
            score += 120
        elif name.startswith(term):
            score += 90
        elif term in name:
            score += 70
        elif term and name_acronym.startswith(term):
            score += 60

        if term in category_name:
            score += 45
        if any(term in tag for tag in tags):
            score += 35
        if term in domain:
            score += 30
        if term in description:
            score += 20

    if score:
        # 访问量只作为同等相关性下的小幅加成，避免热门但不相关的站点排到前面。
        score += min(max(to_int(str(site.get("visits", 0)), 0), 0), 10_000) // 100

    return score


def filter_sites(
    sites: list[dict],
    category: str | None = None,
    query: str | None = None,
    categories: list[dict] | None = None,
) -> list[dict]:
    """按分类和关键字过滤站点；关键字搜索会按相关性排序。"""
    filtered = sites
    if category:
        filtered = [site for site in filtered if category in site_category_slugs(site)]

    if query:
        terms = [term for term in normalize_search_text(query).split(" ") if term]
        categories_by_slug = category_name_map(categories or [])
        scored_sites = [
            (search_score(site, terms, categories_by_slug), site)
            for site in filtered
        ]
        filtered = [
            site
            for score, site in sorted(
                scored_sites,
                key=lambda item: (
                    # 主排序是搜索相关性；访问量和更新时间只用于相关性相同时的排序。
                    item[0],
                    to_int(str(item[1].get("visits", 0)), 0),
                    item[1].get("updated_at") or item[1].get("added_at", ""),
                ),
                reverse=True,
            )
            if score > 0
        ]

    return filtered


