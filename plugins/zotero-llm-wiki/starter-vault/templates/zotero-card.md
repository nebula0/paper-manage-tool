{#- 外掛只取「第一個有標註的附件」；這裡合併所有附件（正文＋補充資料）的標註 -#}
{%- set allAnnots = [] -%}
{%- for att in attachments or [] -%}{%- for a in att.annotations or [] -%}{%- set _ = allAnnots.push(a) -%}{%- endfor -%}{%- endfor -%}
{%- set annotations = allAnnots if allAnnots | length else annotations -%}
---
title: "{{title | replace('"', "'")}}"
citekey: {{citekey}}
authors: "{{authors}}"
year: {% if date %}{{date | format("YYYY")}}{% endif %}
journal: "{{publicationTitle}}"
doi: "{{DOI}}"
{%- set cols = (collections or []) | sort(false, true, "fullPath") %}
{%- set c1 = cols | first %}
{%- if c1 %}
topic: "{{ c1.fullPath }}"
collections:
{%- for c in cols %}
  - "{{ c.fullPath }}"
{%- endfor %}
{%- else %}
topic:
collections:
{%- endif %}
{%- set n1 = (notes or []) | first %}
{%- if n1 and n1.note %}
claim: "{{ n1.note.split("\n") | first | trim | replace('"', "'") }}"
{%- else %}
claim:
{%- endif %}
{%- set imgs = (annotations or []) | filterby("type", "contains", "image") %}
{%- set cov = (imgs | filterby("comment", "startswith", "cover") | first) or (imgs | first) %}
{%- if cov %}
cover: "[[{{cov.imageRelativePath}}]]"
{%- else %}
cover:
{%- endif %}
{%- set imp = (tags or []) | filterby("tag", "startswith", "重要性/") | first %}
importance: {% if imp %}{{ imp.tag | replace("重要性/", "") }}{% endif %}
{%- set st = (tags or []) | filterby("tag", "startswith", "狀態/") | first %}
status: {% if st %}{{ st.tag | replace("狀態/", "") }}{% else %}未讀{% endif %}
tags:
  - lit
{%- for t in (tags or []) | filterby("tag", "contains", "/") %}
  - {{ t.tag | replace(" ", "-") }}
{%- endfor %}
---

# {{title}}

{% if markdownNotes %}{{markdownNotes}}{% else %}> [!warning] 還沒寫筆記
> 在 Zotero 右側的「筆記」欄位寫。**第一行寫主張**（會變成卡片上的 `claim`）。
{% endif %}

---
{%- set label = {
  "Yellow": "核心論述",
  "Red": "有疑慮",
  "Green": "方法可參考",
  "Blue": "關鍵數據",
  "Cyan": "關鍵數據",
  "Purple": "待查資料",
  "Magenta": "待查資料",
  "Orange": "其他",
  "Gray": "其他",
  "Black": "其他",
  "White": "其他"
} %}
{#- 灰色保留給 AI 標註（規範見 zotero-llm-wiki 外掛 skills/lit-library/規則.md §5.2），不放進人類分區 #}
{%- for color, items in (annotations or []) | groupby("colorCategory") %}
{%- if color != "Gray" %}

## {{ label[color] if label[color] else color }}
{% for a in items %}
{%- if a.imageRelativePath %}
![[{{a.imageRelativePath}}]]
{%- elif a.annotatedText %}
{%- if a.color %}
<div style="border-left:4px solid {{a.color}};background:{{a.color}}1f;padding:0.5em 0.9em;border-radius:0 5px 5px 0;margin:0.6em 0">{% if a.allTags and "AI/" in a.allTags %}🤖 {% endif %}{{a.annotatedText}}</div>
{%- else %}
> {{a.annotatedText}}
{%- endif %}
{%- endif %}
{%- if a.comment %}

🍄‍🟫{{a.comment}}
{%- endif %}

{% if a.desktopURI %}<sup>[p.{{a.pageLabel}}]({{a.desktopURI}})</sup>{% else %}<sup>[↗ 在 Zotero 開啟]({{desktopURI}}) — 此附件副檔名非小寫 .pdf，無法定位到頁</sup>{% endif %}
{% endfor %}
{%- endif %}
{%- endfor %}

{#- AI 標註：灰色，依 AI/ tag 分組；使用者改成自己的顏色 = 採納，會移到上面的人類分區並加 🤖 #}
{%- set ai = (annotations or []) | filterby("colorCategory", "startswith", "gray") %}
{%- if ai | length %}

---

## 🤖 AI 標註
{%- set aicats = [["論點", "核心論述"], ["質疑", "有疑慮"], ["方法", "方法可參考"], ["數據", "關鍵數據"], ["待查", "待查資料"], ["本研究", "與本研究相關"]] %}
{%- for c in aicats %}
{%- set its = ai | filterby("allTags", "contains", "AI/" + c[0]) %}
{%- if its | length %}

### {{ c[1] }}
{% for a in its %}
<div style="border-left:4px solid #aaaaaa;background:#aaaaaa1f;padding:0.5em 0.9em;border-radius:0 5px 5px 0;margin:0.6em 0">{{a.annotatedText}}</div>
{%- if a.comment %}

🤖{{a.comment}}
{%- endif %}

{% if a.desktopURI %}<sup>[p.{{a.pageLabel}}]({{a.desktopURI}})</sup>{% else %}<sup>[↗ 在 Zotero 開啟]({{desktopURI}})</sup>{% endif %}
{% endfor %}
{%- endif %}
{%- endfor %}
{%- endif %}

---

## Obsidian 隨手記
{% persist "obsidian-only" %}{% endpersist %}

[在 Zotero 開啟]({{desktopURI}})
