from __future__ import annotations

import json

import streamlit.components.v1 as components

APP_DISPLAY_NAME = "Inventario Shell"


def apply_mobile_app_name(name: str = APP_DISPLAY_NAME) -> None:
    """
  Set browser / home-screen label on mobile. Streamlit Cloud serves a default
  manifest named "Streamlit"; this patches the parent document when possible.
  """
    safe = json.dumps(name)
    components.html(
        f"""
        <script>
        (function () {{
          const doc = window.parent !== window ? window.parent.document : document;
          const name = {safe};
          doc.title = name;
          function setMeta(key, value) {{
            let el = doc.querySelector('meta[name="' + key + '"]');
            if (!el) {{
              el = doc.createElement("meta");
              el.setAttribute("name", key);
              doc.head.appendChild(el);
            }}
            el.setAttribute("content", value);
          }}
          setMeta("apple-mobile-web-app-title", name);
          setMeta("application-name", name);
          const manifest = doc.querySelector('link[rel="manifest"]');
          if (manifest) {{
            const payload = {{
              name: name,
              short_name: name,
              start_url: doc.location.href,
              display: "standalone",
              background_color: "#ffffff",
              theme_color: "#ffffff",
              icons: [],
            }};
            const blob = new Blob([JSON.stringify(payload)], {{ type: "application/json" }});
            manifest.href = URL.createObjectURL(blob);
          }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )
