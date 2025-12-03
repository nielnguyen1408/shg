"""
Generate a self-contained product_viewer_v1.html with embedded JSON data.

Usage:
    python build_product_viewer_v1.py

The script reads product_viewer.html as the template and injects
clean_info_noimage.json + new_website_tinhnang_noimage.json directly into the
first <script>...</script> block so the resulting HTML works without fetch().
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_HTML = BASE_DIR / "product_viewer.html"
OUTPUT_HTML = BASE_DIR / "product_viewer_v1.html"
CLEAN_JSON = BASE_DIR / "clean_info_noimage.json"
NEW_JSON = BASE_DIR / "new_website_tinhnang_noimage.json"

SCRIPT_TEMPLATE = """  <script>
    const CLEAN_DATA = __CLEAN__;
    const NEW_DATA = __NEW__;

    const DEFAULT_FIELDS = {{
      TongQuan: ["TongQuan"],
      ThietKe: ["ThietKe"],
      CongNang: ["CongNang"],
    }};

    const DATASETS = [
      {{
        key: "clean",
        url: "clean_info_noimage.json",
        label: "clean_info_noimage.json",
        type: "sections",
        fields: DEFAULT_FIELDS,
      }},
      {{
        key: "new",
        url: "new_website_tinhnang_noimage.json",
        label: "new_website_tinhnang_noimage.json",
        type: "features",
      }},
    ];

    const datasetMeta = Object.fromEntries(DATASETS.map((meta) => [meta.key, meta]));
    const sourceLabels = {{
      clean: document.getElementById("panel-clean-source"),
      new: document.getElementById("panel-new-source"),
    }};
    Object.entries(sourceLabels).forEach(([key, element]) => {{
      if (element && datasetMeta[key]) {{
        element.textContent = `Nguon: ${datasetMeta[key].label}`;
      }}
    }});

    const EMBEDDED_DATA = {{
      clean: CLEAN_DATA,
      new: NEW_DATA,
    }};

    const searchInput = document.getElementById("searchInput");
    const productSelect = document.getElementById("productSelect");
    const details = document.getElementById("details");
    const emptyState = document.getElementById("emptyState");
    const productHeading = document.getElementById("productHeading");

    const panels = {{
      clean: {{
        body: document.getElementById("panel-clean-body"),
        empty: document.getElementById("panel-clean-empty"),
        fields: {{
          TongQuan: document.getElementById("panel-clean-tongquan"),
          ThietKe: document.getElementById("panel-clean-thietke"),
          CongNang: document.getElementById("panel-clean-congnang"),
        }},
      }},
      new: {{
        body: document.getElementById("panel-new-body"),
        empty: document.getElementById("panel-new-empty"),
        container: document.getElementById("panel-new-features"),
      }},
    }};

    const state = {{
      datasets: {{}},
      codes: [],
      filteredCodes: [],
      selectedCode: null,
    }};

    DATASETS.forEach(({ key, type }) => {{
      const source = EMBEDDED_DATA[key] || [];
      const normalized =
        type === "features"
          ? normalizeFeatureRows(source)
          : normalizeRows(source, datasetMeta[key].fields);
      state.datasets[key] = {{
        rows: normalized,
        map: new Map(normalized.map((item) => [item.Code, item])),
        error: null,
        type,
      }};
    }});

    finalizeLoad();

    function normalizeRows(rows, fieldMap = DEFAULT_FIELDS) {{
      if (!Array.isArray(rows)) {{
        return [];
      }}
      return rows
        .map((item) => normalizeEntry(item, fieldMap))
        .filter((item) => item !== null);
    }}

    function normalizeEntry(entry, fieldMap) {{
      if (!entry || typeof entry !== "object") {{
        return null;
      }}
      const lowered = {{}};
      Object.entries(entry).forEach(([key, value]) => {{
        lowered[String(key).toLowerCase()] = value;
      }});
      const code = pickField(lowered, ["code"]);
      if (!code) {{
        return null;
      }}
      return {{
        Code: code,
        TongQuan: pickField(
          lowered,
          (fieldMap?.TongQuan || DEFAULT_FIELDS.TongQuan).map((f) => f.toLowerCase())
        ),
        ThietKe: pickField(
          lowered,
          (fieldMap?.ThietKe || DEFAULT_FIELDS.ThietKe).map((f) => f.toLowerCase())
        ),
        CongNang: pickField(
          lowered,
          (fieldMap?.CongNang || DEFAULT_FIELDS.CongNang).map((f) => f.toLowerCase())
        ),
      }};
    }}

    function normalizeFeatureRows(rows) {{
      if (!Array.isArray(rows)) {{
        return [];
      }}
      return rows
        .map((entry) => {{
          if (!entry || typeof entry !== "object") {{
            return null;
          }}
          const code = toText(entry.Code || entry.ProductCode);
          if (!code) {{
            return null;
          }}
          const featuresSource = Array.isArray(entry.Features)
            ? entry.Features
            : Array.isArray(entry.AttributeBlocks)
            ? entry.AttributeBlocks
            : [];
          const features = featuresSource
            .map((feature) => normalizeFeatureItem(feature))
            .filter((feature) => feature !== null);
          return {{ Code: code, Features: features }};
        }})
        .filter((entry) => entry !== null);
    }}

    function normalizeFeatureItem(feature) {{
      if (!feature || typeof feature !== "object") {{
        return null;
      }}
      const title = toText(feature.Title || feature.AttributeTitle);
      const content = toText(feature.Content || feature.AttributeContentText);
      const image = toText(feature.Image || feature.AttributeImageFile);
      if (!title && !content && !image) {{
        return null;
      }}
      return {{ Title: title, Content: content, Image: image }};
    }}

    function toText(value) {{
      if (value === undefined || value === null) {{
        return "";
      }}
      return String(value).trim();
    }}

    function pickField(source, candidates) {{
      for (const name of candidates) {{
        const value = source[name];
        if (value !== undefined && value !== null && String(value).trim().length) {{
          return String(value).trim();
        }}
      }}
      return "";
    }}

    function finalizeLoad() {{
      const allCodes = new Set();
      DATASETS.forEach(({ key }) => {{
        state.datasets[key].rows.forEach((item) => allCodes.add(item.Code));
      }});
      state.codes = Array.from(allCodes).sort((a, b) =>
        a.localeCompare(b)
      );
      state.filteredCodes = [...state.codes];
      if (state.codes.length === 0) {{
        details.hidden = true;
        emptyState.hidden = false;
        emptyState.textContent =
          "Khong tim thay ma nao trong cac file clean_info_noimage.json hoac new_website_tinhnang_noimage.json.";
        return;
      }}
      state.selectedCode = state.filteredCodes[0];
      renderSelect();
      productSelect.focus();
    }}

    function renderSelect() {{
      productSelect.innerHTML = "";
      const fragment = document.createDocumentFragment();
      state.filteredCodes.forEach((code, index) => {{
        const option = document.createElement("option");
        option.value = code;
        option.textContent = code;
        if (code === state.selectedCode) {{
          option.selected = true;
        }}
        fragment.appendChild(option);
        if (index === 0 && !state.selectedCode) {{
          option.selected = true;
        }}
      }});
      productSelect.appendChild(fragment);
      const hasItems = state.filteredCodes.length > 0;
      productSelect.disabled = !hasItems;
      if (!state.selectedCode && hasItems) {{
        state.selectedCode = state.filteredCodes[0];
      }}
      updateDetails();
    }}

    function updateDetails() {{
      const code = state.selectedCode;
      if (!code) {{
        details.hidden = true;
        emptyState.hidden = false;
        emptyState.textContent = "Khong tim thay ma san pham phu hop.";
        return;
      }}
      emptyState.hidden = true;
      details.hidden = false;
      productHeading.textContent = `Ma: ${code}`;
      DATASETS.forEach(({ key }) => {{
        const meta = datasetMeta[key];
        renderPanel(panels[key], state.datasets[key], code, meta);
      }});
    }}

    function renderPanel(panel, dataset, code, meta) {{
      const product = dataset.map.get(code);
      if (!product) {{
        panel.body.hidden = true;
        panel.empty.hidden = false;
        if (dataset.rows.length === 0 && dataset.error) {{
          panel.empty.textContent = `Khong doc duoc ${meta.label}: ${dataset.error}`;
        }} else if (dataset.rows.length === 0) {{
          panel.empty.textContent = `Khong co du lieu nao trong ${meta.label}.`;
        }} else {{
          panel.empty.textContent = `Khong co ma nay trong ${meta.label}.`;
        }}
        return;
      }}
      panel.empty.hidden = true;
      panel.body.hidden = false;
      if (meta.type === "features") {{
        renderFeaturesList(panel.container, product.Features);
      }} else {{
        fillField(panel.fields.TongQuan, product.TongQuan);
        fillField(panel.fields.ThietKe, product.ThietKe);
        fillField(panel.fields.CongNang, product.CongNang);
      }}
    }}

    function renderFeaturesList(container, features) {{
      container.innerHTML = "";
      if (!features || !features.length) {{
        const placeholder = document.createElement("p");
        placeholder.className = "feature-placeholder";
        placeholder.textContent = "Khong co tinh nang nao cho ma nay.";
        container.appendChild(placeholder);
        return;
      }}
      const fragment = document.createDocumentFragment();
      features.forEach((feature, index) => {{
        fragment.appendChild(createFeatureNode(feature, index));
      }});
      container.appendChild(fragment);
    }}

    function createFeatureNode(feature, index) {{
      const wrapper = document.createElement("div");
      wrapper.className = "feature-item";
      const titleText = feature.Title || `Tinh nang ${index + 1}`;
      const titleEl = document.createElement("h5");
      titleEl.textContent = titleText;
      wrapper.appendChild(titleEl);

      if (feature.Content) {{
        const contentEl = document.createElement("div");
        contentEl.className = "feature-content";
        contentEl.innerHTML = feature.Content;
        wrapper.appendChild(contentEl);
      }}

      if (feature.Image) {{
        const imageWrapper = document.createElement("div");
        imageWrapper.className = "feature-image";
        const img = document.createElement("img");
        img.src = feature.Image;
        img.alt = titleText;
        imageWrapper.appendChild(img);
        wrapper.appendChild(imageWrapper);
      }}
      return wrapper;
    }}

    function fillField(element, value) {{
      if (value && value.trim()) {{
        element.classList.remove("placeholder");
        element.innerHTML = value;
      }} else {{
        element.classList.add("placeholder");
        element.innerHTML = "Khong co du lieu";
      }}
    }}

    productSelect.addEventListener("change", () => {{
      state.selectedCode = productSelect.value || null;
      updateDetails();
    }});

    searchInput.addEventListener("input", (event) => {{
      const keyword = event.target.value.trim().toLowerCase();
      state.filteredCodes = state.codes.filter((code) =>
        code.toLowerCase().includes(keyword)
      );
      state.selectedCode = state.filteredCodes[0] || null;
      renderSelect();
    }});
  </script>
"""


def build_html() -> None:
    base_html = TEMPLATE_HTML.read_text(encoding="utf-8")
    clean_data = json.loads(CLEAN_JSON.read_text(encoding="utf-8"))
    new_data = json.loads(NEW_JSON.read_text(encoding="utf-8"))

    try:
        start = base_html.index("<script>")
        end = base_html.rindex("</script>")
    except ValueError as exc:
        raise SystemExit("Khong tim thay the <script> trong template HTML.") from exc

    script_block = (
        SCRIPT_TEMPLATE.replace("__CLEAN__", json.dumps(clean_data, ensure_ascii=False))
        .replace("__NEW__", json.dumps(new_data, ensure_ascii=False))
        .replace("\\t", "\t")
    )
    script_block = script_block.replace("{{", "{").replace("}}", "}")

    new_html = base_html[:start] + script_block + base_html[end + len("</script>") :]
    OUTPUT_HTML.write_text(new_html, encoding="utf-8")
    print(f"Da tao {OUTPUT_HTML.name} tu template va du lieu hien tai.")


if __name__ == "__main__":
    build_html()
