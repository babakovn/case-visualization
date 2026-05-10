from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT = Path(os.environ.get("FULL_TABLE_INPUT", ROOT / "output_deduped" / "normalized_cases_links_repaired_final.xlsx"))
OUTPUT = Path(os.environ.get("FULL_TABLE_OUTPUT", ROOT / "output_deduped" / "full_table_tags_left.html"))
VERSION = os.environ.get("FULL_TABLE_VERSION", "v1.1")


FIELDS = {
    "no": "№",
    "title": "Название кейса",
    "brief": "Краткое описание",
    "detail": "Подробное описание",
    "organization": "Организация",
    "problem": "Решаемая проблема",
    "result": "Результат",
    "contact": "К кому обратиться",
    "link": "Ссылка",
    "l1": "Класс проблемы",
    "l2": "Зона применения",
    "country": "Страна",
    "macrotrend": "Макротренд",
    "technology": "Технология / тип решения (тренд)",
    "microtrend": "Микротренд",
    "trl": "TRL",
    "object": "Объект воздействия",
    "availability": "Доступность технологии",
    "vendors": "Вендоры",
}


TAG_GROUPS = [
    ("object", "Объект воздействия"),
    ("macrotrend", "Макротренд"),
    ("microtrend", "Микротренд"),
    ("trl", "TRL"),
    ("country", "Страна"),
    ("availability", "Доступность"),
]

TABLE_FILTER_GROUPS = [
    ("l1", "Класс проблемы"),
    ("l2", "Зона применения"),
]


def clean(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def split_multi(value) -> list[str]:
    text = clean(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"\s*;\s*", text) if part.strip()]


def norm(text: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", " ", text.lower().replace("ё", "е")).strip()


def records_from_table(df: pd.DataFrame) -> list[dict]:
    records = []
    for idx, row in df.iterrows():
        item = {
            "id": idx + 1,
            "no": clean(row.get(FIELDS["no"])),
            "title": clean(row.get(FIELDS["title"])),
            "brief": clean(row.get(FIELDS["brief"])),
            "detail": clean(row.get(FIELDS["detail"])),
            "organization": clean(row.get(FIELDS["organization"])),
            "problem": clean(row.get(FIELDS["problem"])),
            "result": clean(row.get(FIELDS["result"])),
            "contact": clean(row.get(FIELDS["contact"])),
            "link": clean(row.get(FIELDS["link"])),
            "l1": split_multi(row.get(FIELDS["l1"])),
            "l2": split_multi(row.get(FIELDS["l2"])),
            "country": split_multi(row.get(FIELDS["country"])),
            "macrotrend": split_multi(row.get(FIELDS["macrotrend"])),
            "technology": split_multi(row.get(FIELDS["technology"])),
            "microtrend": split_multi(row.get(FIELDS["microtrend"])),
            "trl": split_multi(row.get(FIELDS["trl"])),
            "object": split_multi(row.get(FIELDS["object"])),
            "availability": split_multi(row.get(FIELDS["availability"])),
            "vendors": split_multi(row.get(FIELDS["vendors"])),
        }
        search_parts = [
            item["no"],
            item["title"],
            item["brief"],
            item["detail"],
            item["organization"],
            item["problem"],
            item["result"],
            item["contact"],
            item["link"],
            *item["l1"],
            *item["l2"],
            *item["country"],
            *item["macrotrend"],
            *item["technology"],
            *item["microtrend"],
            *item["trl"],
            *item["object"],
            *item["availability"],
            *item["vendors"],
        ]
        item["searchText"] = norm(" ".join(part for part in search_parts if part))
        records.append(item)
    return records


def tag_summary(records: list[dict]) -> dict:
    summary = {}
    for key, title in TAG_GROUPS:
        counter = Counter(value for row in records for value in row[key])
        summary[key] = {
            "title": title,
            "values": [{"name": name, "count": count} for name, count in counter.most_common()],
        }
    return summary


def build_html(records: list[dict]) -> str:
    generated_at = os.environ.get("FULL_TABLE_GENERATED_AT") or datetime.now().strftime("%d.%m.%Y %H:%M")
    disclaimer = (
        "Каталог подготовлен для внутренней работы компаний Группы и предназначен для "
        "предварительного поиска релевантных кейсов, технологий и решений. Материалы "
        "помогают быстрее перейти от бизнес-задачи или проблемы к возможным направлениям "
        "для обсуждения, проверки и пилотирования."
    )
    payload = json.dumps(
        {
            "records": records,
            "tags": tag_summary(records),
            "tableFilters": {
                key: {
                    "title": title,
                    "values": [
                        {"name": name, "count": count}
                        for name, count in Counter(value for row in records for value in row[key]).most_common()
                    ],
                }
                for key, title in TABLE_FILTER_GROUPS
            },
            "meta": {
                "source": INPUT.name,
                "total": len(records),
                "generatedAt": generated_at,
                "version": VERSION,
                "disclaimer": disclaimer,
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Полная таблица кейсов с тегами слева</title>
<style>
:root{{--bg:#f6f8fc;--panel:#fff;--ink:#0f172a;--muted:#64748b;--soft:#f8fafc;--line:#e2e8f0;--line2:#cbd5e1;--accent:#4f46e5;--accent2:#10b981;--shadow:0 1px 2px rgba(15,23,42,.04),0 8px 24px rgba(15,23,42,.06);font-family:Inter,ui-sans-serif,system-ui,"Segoe UI",sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink)}}a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}button,input{{font:inherit}}
.shell{{max-width:1680px;margin:0 auto;padding:24px 18px 38px}}.hero{{display:grid;grid-template-columns:minmax(0,1fr) 520px;gap:18px;align-items:end;margin-bottom:14px}}.eyebrow{{font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:#475569;font-weight:850}}h1{{font-size:clamp(26px,3vw,40px);line-height:1.08;margin:4px 0 8px;letter-spacing:-.03em}}.sub{{max-width:860px;color:var(--muted);font-size:14px;line-height:1.6;margin:0}}.metaPanel{{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:13px 14px;color:#334155;font-size:12px;line-height:1.45}}.metaPanel dl{{display:grid;grid-template-columns:118px minmax(0,1fr);gap:6px 10px;margin:0 0 10px}}.metaPanel dt{{color:var(--muted);font-weight:850;text-transform:uppercase;letter-spacing:.05em;font-size:10px}}.metaPanel dd{{margin:0;font-weight:750;overflow-wrap:anywhere}}.metaDisclaimer{{border-top:1px solid #edf2f7;padding-top:9px;color:#64748b;font-size:11px;line-height:1.45}}
.kpis{{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:10px;margin:14px 0}}.kpi{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:13px 14px;box-shadow:var(--shadow)}}.kpi b{{display:block;font-size:25px;line-height:1;color:var(--accent)}}.kpi span{{display:block;margin-top:6px;color:var(--muted);font-size:11px;font-weight:850;text-transform:uppercase;letter-spacing:.055em}}
.toolbar{{display:flex;gap:10px;align-items:center;margin:14px 0;flex-wrap:wrap}}#search{{flex:1 1 460px;border:1px solid var(--line);border-radius:13px;background:#fff;padding:12px 14px;box-shadow:var(--shadow);font-size:14px}}#search:focus{{outline:none;border-color:#a5b4fc;box-shadow:0 0 0 4px rgba(79,70,229,.12),var(--shadow)}}.reset{{border:1px solid var(--line);background:#fff;border-radius:13px;padding:12px 14px;font-weight:850;color:#334155;cursor:pointer;white-space:nowrap;box-shadow:var(--shadow)}}.viewSwitch{{display:flex;gap:4px;background:#eaf0f7;border:1px solid #dde6f0;border-radius:13px;padding:4px}}.viewSwitch button{{border:0;background:transparent;color:#475569;padding:9px 12px;border-radius:10px;font-weight:850;font-size:13px;cursor:pointer;white-space:nowrap}}.viewSwitch button.active{{background:#fff;color:#111827;box-shadow:0 1px 4px rgba(15,23,42,.12)}}
.layout{{display:grid;grid-template-columns:320px minmax(0,1fr);gap:14px;align-items:start}}.sidebar{{position:sticky;top:12px;background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:14px;max-height:calc(100vh - 24px);overflow:auto}}.sideHead{{display:flex;justify-content:space-between;gap:12px;align-items:center;border-bottom:1px solid var(--line);padding-bottom:11px;margin-bottom:10px}}.sideHead b{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#334155}}.clearTags{{border:0;background:transparent;color:var(--accent);font-size:12px;font-weight:850;cursor:pointer;padding:0}}
.tagGroup{{border-bottom:1px solid #edf2f7;padding:11px 0;position:relative}}.tagGroup:last-child{{border-bottom:0}}.tagTitle{{width:100%;display:flex;justify-content:space-between;gap:8px;align-items:center;color:#334155;font-size:12px;font-weight:850;margin-bottom:8px;border:0;background:transparent;padding:0;text-align:left;cursor:pointer}}.tagTitle .tagTitleMain{{display:flex;align-items:center;gap:7px;min-width:0}}.tagTitle .chevron{{width:18px;height:18px;border-radius:999px;background:#f1f5f9;color:#64748b;display:inline-flex;align-items:center;justify-content:center;font-size:12px;line-height:1;transition:transform .18s ease}}.tagTitle .tagCount{{color:#94a3b8;font-size:11px;white-space:nowrap}}.tagGroup.collapsed .chevron{{transform:rotate(-90deg)}}.tags{{display:flex;flex-wrap:wrap;gap:6px;max-height:154px;overflow:auto;padding-right:2px}}.tagGroup.collapsed .tags{{display:none}}.tag{{display:inline-flex;align-items:center;gap:6px;max-width:100%;border:1px solid transparent;background:#f1f5f9;color:#334155;border-radius:999px;padding:6px 8px;font-size:12px;font-weight:750;cursor:pointer}}.tag .text{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:218px}}.tag .count{{min-width:20px;height:18px;display:inline-flex;align-items:center;justify-content:center;border-radius:999px;background:rgba(15,23,42,.08);font-size:10px;padding:0 5px}}.groupInfo{{width:17px;height:17px;display:inline-flex;align-items:center;justify-content:center;border-radius:999px;background:#fff;border:1px solid rgba(100,116,139,.28);color:#64748b;font-size:11px;font-weight:900;line-height:1;position:static;flex:0 0 auto;cursor:help}}.groupInfo:after{{content:attr(data-tip);position:absolute;left:24px;top:34px;transform:none;width:270px;max-width:calc(100% - 34px);background:#fff;color:#334155;border:1px solid var(--line2);border-radius:8px;padding:8px 10px;font-size:11px;font-weight:650;line-height:1.35;box-shadow:0 8px 24px rgba(15,23,42,.16);opacity:0;pointer-events:none;z-index:8;text-align:left;white-space:normal}}.groupInfo:hover:after,.groupInfo:focus-visible:after{{opacity:1}}.tag.active{{background:linear-gradient(135deg,var(--accent),#6366f1);color:#fff;box-shadow:0 6px 16px rgba(79,70,229,.22)}}.tag.active .count{{background:rgba(255,255,255,.24);color:#fff}}
.panel{{min-width:0}}.resultLine{{display:flex;justify-content:space-between;gap:12px;align-items:center;color:var(--muted);font-size:13px;margin-bottom:10px;flex-wrap:wrap}}.resultLine b{{color:var(--ink)}}.tableWrap,.matrixWrap{{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);overflow:auto;max-height:calc(100vh - 218px)}}table{{border-collapse:collapse;width:100%;min-width:1480px;font-size:12px}}th{{position:sticky;top:0;background:#f8fafc;color:#334155;border-bottom:1px solid var(--line);padding:10px;text-align:left;white-space:nowrap;text-transform:uppercase;letter-spacing:.05em;font-size:11px;z-index:1}}td{{border-bottom:1px solid #eef2f7;padding:10px;vertical-align:top;line-height:1.42;color:#334155}}tr:hover td{{background:#fafcff}}.matrixWrap{{padding:8px}}.matrix{{border-collapse:separate;border-spacing:6px;min-width:1180px}}.matrix th.corner{{background:transparent;border:0}}.matrix th.l2{{position:static;text-align:center;border:1px solid var(--line);border-radius:12px;white-space:normal;vertical-align:bottom;line-height:1.25}}.matrix th.l1{{position:static;color:#fff;border-radius:12px;min-width:230px;white-space:normal;line-height:1.25;background:var(--row)}}.matrix .cell{{height:58px;text-align:center;border:1px solid var(--line);border-radius:12px;background:#fff;font-weight:900;font-size:18px;color:#111827;padding:0}}.matrix .cell.emptyCell{{background:#fbfdff;color:#cbd5e1}}.matrixBtn{{width:100%;min-height:58px;border:0;background:transparent;color:inherit;font-weight:900;cursor:pointer;border-radius:12px}}.matrixHeadBtn{{width:100%;border:0;background:transparent;color:inherit;font:inherit;font-weight:900;text-align:inherit;cursor:pointer;padding:0}}.matrix .selectedAxis{{outline:3px solid rgba(79,70,229,.28);outline-offset:1px}}.matrix .selectedPair{{background:#eef2ff;color:#3730a3;border-color:#818cf8}}.num{{white-space:nowrap;font-weight:850;color:#475569}}.title{{min-width:260px;font-weight:850;color:#0f172a}}.clamp{{max-width:340px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}.chips{{display:flex;flex-wrap:wrap;gap:4px;min-width:190px}}.chip{{font-size:10.5px;line-height:1.1;border-radius:7px;padding:4px 6px;background:#eef2ff;color:#3730a3;font-weight:800;max-width:190px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.chip.l2{{background:#f3e8ff;color:#6b21a8}}.chip.country{{background:#fdf2f8;color:#9d174d}}.chip.tech{{background:#ecfdf5;color:#047857}}.cardsGrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:15px;position:relative;overflow:hidden}}.card:before{{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--accent)}}.cardTop{{display:flex;justify-content:space-between;gap:10px;color:var(--muted);font-size:12px;font-weight:850}}.card h3{{font-size:16px;line-height:1.3;margin:9px 0 5px}}.org{{color:var(--muted);font-size:13px;margin:0 0 8px}}.brief{{font-size:13px;line-height:1.55;color:#334155}}.card details{{margin-top:10px;border-top:1px solid #edf2f7;padding-top:10px}}.card summary{{cursor:pointer;color:var(--accent);font-size:13px;font-weight:850}}.detail{{font-size:13px;line-height:1.55;color:#334155;margin-top:8px}}.empty{{padding:44px;text-align:center;color:var(--muted)}}.mobileHint{{display:none}}
@media(max-width:980px){{.hero{{grid-template-columns:1fr}}.kpis{{grid-template-columns:repeat(2,minmax(0,1fr))}}.layout{{grid-template-columns:1fr}}.sidebar{{position:relative;top:auto;max-height:none}}.tableWrap{{max-height:none}}.mobileHint{{display:inline}}.shell{{padding:18px 12px 32px}}}}
</style>
</head>
<body>
<main class="shell">
  <section class="hero">
    <div>
      <div class="eyebrow">Полная таблица</div>
      <h1>Интерактивная база кейсов для поиска решений по задачам бизнеса: от производственных потерь и затрат до качества, безопасности, логистики и новых продуктов.</h1>
      <p class="sub">Табличная визуализация показывает все строки нормализованной таблицы. Левая панель содержит теги-фильтры по классификации, трендам, странам, TRL, доступности и вендорам.</p>
    </div>
    <aside class="metaPanel" aria-label="Метаданные генерации">
      <dl>
        <dt>Дата</dt><dd>{generated_at}</dd>
        <dt>Версия</dt><dd>{VERSION}</dd>
      </dl>
      <div class="metaDisclaimer"><b>Дисклеймер.</b> {disclaimer}</div>
    </aside>
  </section>
  <section class="kpis" id="kpis"></section>
  <section class="toolbar">
    <input id="search" type="search" placeholder="Поиск по всей таблице: название, описание, организация, результат, страна, технология, ссылка">
    <div class="viewSwitch" role="tablist" aria-label="Переключение вида">
      <button class="active" data-view="matrix">Матрица</button>
      <button data-view="table">Таблица</button>
      <button data-view="cards">Карточки</button>
    </div>
    <button class="reset" id="reset">Сбросить</button>
  </section>
  <section class="layout">
    <aside class="sidebar">
      <div class="sideHead"><b>Теги</b><button class="clearTags" id="clearTags">Очистить</button></div>
      <div id="tagPanel"></div>
    </aside>
    <section class="panel">
      <div class="resultLine"><span>Показано: <b id="visibleCount">0</b> из <b id="totalCount">0</b></span><span class="mobileHint">Матрицу и таблицу можно прокручивать горизонтально.</span></div>
      <div id="content"></div>
    </section>
  </section>
</main>
<script id="table-data" type="application/json">{payload}</script>
<script>
const DATA = JSON.parse(document.getElementById('table-data').textContent);
const selected = Object.fromEntries(Object.keys(DATA.tags).map(k => [k, new Set()]));
const selectedTable = Object.fromEntries(Object.keys(DATA.tableFilters).map(k => [k, new Set()]));
const collapsedTags = new Set(Object.keys(DATA.tags));
let query = '';
let view = 'matrix';
const L1_ORDER = ['Повышение производительности процессов','Снижение затрат','Повышение качества продукта и сервиса','Расширение и кастомизация клиентского предложения','Повышение безопасности производства и охрана труда','Создание новых продуктов и рыночных предложений','Создание новых моделей кооперации и монетизации'];
const L2_ORDER = ['Разработка и проектирование','Подготовка и организация производства','Производственное исполнение','Снабжение, запасы и логистика','Эксплуатация, ремонт и обслуживание','Клиентское взаимодействие и исполнение заказа','Продуктовое развитие и коммерциализация','Персонал, условия труда и производственная среда'];
const L1_COLORS = ['#4F46E5','#10B981','#8B5CF6','#06B6D4','#EF4444','#F59E0B','#EC4899'];
const esc = v => String(v ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
const norm = v => String(v ?? '').toLowerCase().replaceAll('ё','е').replace(/[^0-9a-zа-яе]+/g, ' ').trim();
function tagGroupDescription(key){{
  const labels = {{
    object: 'Объект воздействия: показывает, на какой актив или часть производственной системы влияет кейс.',
    macrotrend: 'Макротренд: крупное технологическое направление, к которому относится кейс.',
    microtrend: 'Микротренд: более узкая тема или прикладной фокус внутри макротренда.',
    trl: 'TRL: уровень технологической готовности решения в этом кейсе.',
    country: 'Страна: география происхождения, внедрения или основного контекста кейса.',
    availability: 'Доступность: оценка применимости технологии с учетом ограничений, локализации и санкционных рисков.'
  }};
  return labels[key] || 'Тип тега используется для фильтрации кейсов.';
}}
function chip(values, cls=''){{ return values.map(v => `<span class="chip ${{cls}}">${{esc(v)}}</span>`).join(''); }}
function passTags(row){{
  for(const [key, values] of Object.entries(selectedTable)){{
    if(values.size === 0) continue;
    if(!row[key].some(v => values.has(v))) return false;
  }}
  for(const [key, values] of Object.entries(selected)){{
    if(values.size === 0) continue;
    if(!row[key].some(v => values.has(v))) return false;
  }}
  return true;
}}
function passTagsExcept(row, exceptKey){{
  for(const [key, values] of Object.entries(selectedTable)){{
    if(values.size === 0) continue;
    if(!row[key].some(v => values.has(v))) return false;
  }}
  for(const [key, values] of Object.entries(selected)){{
    if(key === exceptKey || values.size === 0) continue;
    if(!row[key].some(v => values.has(v))) return false;
  }}
  return true;
}}
function passSearch(row){{
  const q = norm(query);
  if(!q) return true;
  return q.split(/\\s+/).every(token => row.searchText.includes(token));
}}
function visibleRows(){{ return DATA.records.filter(row => passTags(row) && passSearch(row)); }}
function facetCount(key, value){{
  return DATA.records.filter(row => passSearch(row) && passTagsExcept(row, key) && row[key].includes(value)).length;
}}
function renderKpis(rows){{
  const unique = key => new Set(rows.flatMap(row => row[key])).size;
  const items = [
    ['Всего строк', DATA.meta.total],
    ['Показано', rows.length],
    ['Стран', unique('country')],
    ['Технологий', unique('technology')],
    ['Вендоров', unique('vendors')],
  ];
  document.getElementById('kpis').innerHTML = items.map(([label,value]) => `<div class="kpi"><b>${{esc(value)}}</b><span>${{esc(label)}}</span></div>`).join('');
}}
function renderTags(){{
  const panel = document.getElementById('tagPanel');
  panel.innerHTML = Object.entries(DATA.tags).map(([key, group]) => {{
    const active = selected[key].size;
    const isCollapsed = collapsedTags.has(key);
    const tags = group.values.map(item => {{
      const count = facetCount(key, item.name);
      return `<button class="tag ${{selected[key].has(item.name) ? 'active' : ''}}" data-key="${{esc(key)}}" data-value="${{esc(item.name)}}" title="${{esc(item.name)}}"><span class="text">${{esc(item.name)}}</span><span class="count">${{count}}</span></button>`;
    }}).join('');
    return `<div class="tagGroup ${{isCollapsed ? 'collapsed' : ''}}"><button class="tagTitle" data-collapse-key="${{esc(key)}}" aria-expanded="${{isCollapsed ? 'false' : 'true'}}"><span class="tagTitleMain"><span class="chevron">⌄</span><span>${{esc(group.title)}}</span><span class="groupInfo" tabindex="0" data-tip="${{esc(tagGroupDescription(key))}}">?</span></span><span class="tagCount">${{active ? active + ' выбрано' : group.values.length}}</span></button><div class="tags">${{tags}}</div></div>`;
  }}).join('');
  panel.querySelectorAll('[data-collapse-key]').forEach(btn => btn.addEventListener('click', () => {{
    const key = btn.dataset.collapseKey;
    if(collapsedTags.has(key)) collapsedTags.delete(key); else collapsedTags.add(key);
    renderTags();
  }}));
  panel.querySelectorAll('.groupInfo').forEach(info => info.addEventListener('click', event => event.stopPropagation()));
  panel.querySelectorAll('.tag').forEach(btn => btn.addEventListener('click', () => {{
    const set = selected[btn.dataset.key];
    if(set.has(btn.dataset.value)) set.delete(btn.dataset.value); else set.add(btn.dataset.value);
    render();
  }}));
}}
function renderTable(rows){{
  if(rows.length === 0){{
    return '<div class="tableWrap"><table><tbody><tr><td class="empty" colspan="15">Нет строк под выбранные теги и поиск.</td></tr></tbody></table></div>';
  }}
  const body = rows.map(row => `<tr>
    <td class="num">${{esc(row.no)}}</td>
    <td class="title">${{esc(row.title)}}</td>
    <td><div class="clamp">${{esc(row.organization)}}</div></td>
    <td><div class="clamp">${{esc(row.brief)}}</div></td>
    <td><div class="chips">${{chip(row.l1,'l1')}}</div></td>
    <td><div class="chips">${{chip(row.l2,'l2')}}</div></td>
    <td><div class="chips">${{chip(row.country,'country')}}</div></td>
    <td><div class="chips">${{chip(row.macrotrend)}}</div></td>
    <td><div class="chips">${{chip(row.technology,'tech')}}</div></td>
    <td><div class="chips">${{chip(row.microtrend,'tech')}}</div></td>
    <td><div class="chips">${{chip(row.trl)}}</div></td>
    <td><div class="chips">${{chip(row.availability)}}</div></td>
    <td><div class="chips">${{chip(row.vendors)}}</div></td>
    <td><div class="clamp">${{esc(row.result)}}</div></td>
    <td>${{row.link ? `<a href="${{esc(row.link)}}" target="_blank" rel="noopener">открыть</a>` : ''}}</td>
  </tr>`).join('');
  return `<div class="tableWrap"><table><thead><tr>
    <th>№</th><th>Название</th><th>Организация</th><th>Краткое описание</th><th>Класс проблемы</th><th>Зона применения</th><th>Страна</th><th>Макротренд</th><th>Технология</th><th>Микротренд</th><th>TRL</th><th>Доступность</th><th>Вендоры</th><th>Результат</th><th>Ссылка</th>
  </tr></thead><tbody>${{body}}</tbody></table></div>`;
}}
function renderMatrix(rows){{
  const l1Names = DATA.tableFilters.l1.values.map(item => item.name);
  const l2Names = DATA.tableFilters.l2.values.map(item => item.name);
  const l1Values = [...L1_ORDER.filter(v => l1Names.includes(v)), ...l1Names.filter(v => !L1_ORDER.includes(v))];
  const l2Values = [...L2_ORDER.filter(v => l2Names.includes(v)), ...l2Names.filter(v => !L2_ORDER.includes(v))];
  const head = l2Values.map(v => `<th class="l2 ${{selectedTable.l2.has(v) ? 'selectedAxis' : ''}}"><button class="matrixHeadBtn" data-matrix-key="l2" data-value="${{esc(v)}}" title="${{esc(v)}}">${{esc(v)}}</button></th>`).join('');
  const body = l1Values.map((l1, idx) => {{
    const cells = l2Values.map(l2 => {{
      const count = rows.filter(row => row.l1.includes(l1) && row.l2.includes(l2)).length;
      const selectedPair = selectedTable.l1.has(l1) && selectedTable.l2.has(l2);
      return `<td class="cell ${{count ? '' : 'emptyCell'}}">${{count || '—'}}</td>`;
    }}).join('');
    return `<tr><th class="l1" style="--row:${{L1_COLORS[idx % L1_COLORS.length]}}">${{esc(l1)}}</th>${{cells}}</tr>`;
  }}).join('');
  return `<div class="matrixWrap"><table class="matrix"><thead><tr><th class="corner"></th>${{head}}</tr></thead><tbody>${{body}}</tbody></table></div>`;
}}
function renderMatrix(rows){{
  const l1Names = DATA.tableFilters.l1.values.map(item => item.name);
  const l2Names = DATA.tableFilters.l2.values.map(item => item.name);
  const l1Values = [...L1_ORDER.filter(v => l1Names.includes(v)), ...l1Names.filter(v => !L1_ORDER.includes(v))];
  const l2Values = [...L2_ORDER.filter(v => l2Names.includes(v)), ...l2Names.filter(v => !L2_ORDER.includes(v))];
  const head = l2Values.map(v => `<th class="l2 ${{selectedTable.l2.has(v) ? 'selectedAxis' : ''}}"><button class="matrixHeadBtn" data-matrix-key="l2" data-value="${{esc(v)}}" title="${{esc(v)}}">${{esc(v)}}</button></th>`).join('');
  const body = l1Values.map((l1, idx) => {{
    const cells = l2Values.map(l2 => {{
      const count = rows.filter(row => row.l1.includes(l1) && row.l2.includes(l2)).length;
      const selectedPair = selectedTable.l1.has(l1) && selectedTable.l2.has(l2);
      return `<td class="cell ${{count ? '' : 'emptyCell'}} ${{selectedPair ? 'selectedPair' : ''}}"><button class="matrixBtn" data-matrix-l1="${{esc(l1)}}" data-matrix-l2="${{esc(l2)}}" title="${{esc(l1)}} / ${{esc(l2)}}">${{count || '-'}}</button></td>`;
    }}).join('');
    return `<tr><th class="l1 ${{selectedTable.l1.has(l1) ? 'selectedAxis' : ''}}" style="--row:${{L1_COLORS[idx % L1_COLORS.length]}}"><button class="matrixHeadBtn" data-matrix-key="l1" data-value="${{esc(l1)}}" title="${{esc(l1)}}">${{esc(l1)}}</button></th>${{cells}}</tr>`;
  }}).join('');
  return `<div class="matrixWrap"><table class="matrix"><thead><tr><th class="corner"></th>${{head}}</tr></thead><tbody>${{body}}</tbody></table></div>`;
}}
function bindMatrixFilters(){{
  document.querySelectorAll('[data-matrix-key]').forEach(btn => btn.addEventListener('click', () => {{
    const set = selectedTable[btn.dataset.matrixKey];
    if(set.has(btn.dataset.value)) set.delete(btn.dataset.value); else set.add(btn.dataset.value);
    render();
  }}));
  document.querySelectorAll('[data-matrix-l1]').forEach(btn => btn.addEventListener('click', () => {{
    selectedTable.l1.clear();
    selectedTable.l2.clear();
    selectedTable.l1.add(btn.dataset.matrixL1);
    selectedTable.l2.add(btn.dataset.matrixL2);
    view = 'cards';
    render();
  }}));
}}
function renderCards(rows){{
  if(rows.length === 0){{
    return '<div class="empty">Нет карточек под выбранные теги и поиск.</div>';
  }}
  return `<div class="cardsGrid">${{rows.map(row => `<article class="card">
    <div class="cardTop"><span>${{esc(row.no)}}</span>${{row.link ? `<a href="${{esc(row.link)}}" target="_blank" rel="noopener">источник</a>` : ''}}</div>
    <h3>${{esc(row.title)}}</h3>
    <p class="org">${{esc(row.organization)}}</p>
    <p class="brief">${{esc(row.brief)}}</p>
    <div class="chips">${{chip(row.l1,'l1')}}${{chip(row.l2,'l2')}}${{chip(row.country,'country')}}${{chip(row.technology,'tech')}}</div>
    <details><summary>Проблема и результат</summary><div class="detail"><b>Проблема:</b> ${{esc(row.problem)}}<br><b>Результат:</b> ${{esc(row.result)}}</div></details>
  </article>`).join('')}}</div>`;
}}
function renderContent(rows){{
  document.querySelectorAll('.viewSwitch button').forEach(btn => btn.classList.toggle('active', btn.dataset.view === view));
  document.getElementById('content').innerHTML = view === 'matrix' ? renderMatrix(rows) : (view === 'cards' ? renderCards(rows) : renderTable(rows));
  if(view === 'matrix') bindMatrixFilters();
}}
function render(){{
  const rows = visibleRows();
  document.getElementById('visibleCount').textContent = rows.length;
  document.getElementById('totalCount').textContent = DATA.meta.total;
  renderKpis(rows);
  renderTags();
  renderContent(rows);
}}
document.querySelectorAll('.viewSwitch button').forEach(btn => btn.addEventListener('click', () => {{ view = btn.dataset.view; render(); }}));
document.getElementById('search').addEventListener('input', e => {{ query = e.target.value; render(); }});
document.getElementById('reset').addEventListener('click', () => {{
  query = '';
  document.getElementById('search').value = '';
  Object.values(selected).forEach(set => set.clear());
  Object.values(selectedTable).forEach(set => set.clear());
  render();
}});
document.getElementById('clearTags').addEventListener('click', () => {{ Object.values(selected).forEach(set => set.clear()); render(); }});
render();
</script>
</body>
</html>"""


def main() -> None:
    df = pd.read_excel(INPUT)
    records = records_from_table(df)
    OUTPUT.write_text(build_html(records), encoding="utf-8")
    print(f"Saved {OUTPUT}")
    print(f"Rows: {len(records)}")


if __name__ == "__main__":
    main()
