from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from ...auth import AuthState
from ...db import get_engine
from ...repo.products import list_categories, search_products, update_product, upsert_products
from ...repo.schema import apply_schema


def render(*, auth: AuthState) -> None:
    st.header("Productos (admin)")
    if auth.role != "admin":
        st.error("Acceso solo para admin.")
        return

    engine = get_engine()

    with st.expander("Inicialización (solo la primera vez)", expanded=False):
        st.caption("Crea las tablas en la base de datos si todavía no existen.")
        if st.button("Inicializar base de datos"):
            apply_schema(engine=engine)
            st.success("Listo. Esquema aplicado.")

    st.subheader("Importar productos (CSV)")
    st.caption("Columnas esperadas: CODIGO, PRODUCTO, CATEGORIA.")
    uploaded = st.file_uploader("Sube tu CSV", type=["csv"])

    if uploaded is not None:
        raw = BytesIO(uploaded.getvalue())
        try:
            df = pd.read_csv(raw, dtype=str)
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo leer el CSV: {e}")
            df = None

        if df is not None:
            normalized = _normalize_products_df(df)
            st.write("Vista previa")
            st.dataframe(normalized.head(50), use_container_width=True)

            if st.button("Importar / Actualizar", type="primary"):
                inserted, updated = upsert_products(
                    engine=engine,
                    rows=normalized.to_dict(orient="records"),
                )
                st.success(f"Importación completa. Insertados: {inserted}. Actualizados: {updated}.")

    st.divider()
    st.subheader("Editar productos")
    categories = ["Todas"] + list_categories(engine=engine)
    selected_category = st.selectbox("Categoría", options=categories)
    query = st.text_input("Buscar (código exacto o parte del nombre)")
    results = search_products(engine=engine, query=query, category=selected_category)

    st.caption(f"Resultados: {len(results)} (máx 500)")
    for p in results[:200]:
        with st.expander(f"{p.code} — {p.name}", expanded=False):
            col1, col2 = st.columns([2, 2])
            with col1:
                name = st.text_input("Nombre", value=p.name, key=f"name:{p.code}")
                category = st.text_input("Categoría", value=p.category, key=f"cat:{p.code}")
            with col2:
                active = st.checkbox("Activo", value=p.active, key=f"active:{p.code}")

            if st.button("Guardar cambios", key=f"save:{p.code}"):
                update_product(engine=engine, code=p.code, name=name.strip(), category=category.strip() or "Sin categoría", active=active)
                st.success("Guardado.")


def _normalize_products_df(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize column names
    cols = {c.strip().upper(): c for c in df.columns}
    required = ["CODIGO", "PRODUCTO", "CATEGORIA"]
    missing = [r for r in required if r not in cols]
    if missing:
        raise ValueError(f"Faltan columnas: {', '.join(missing)}")

    out = pd.DataFrame()
    out["code"] = df[cols["CODIGO"]].astype(str).str.strip()
    out["name"] = df[cols["PRODUCTO"]].astype(str).str.strip()
    out["category"] = df[cols["CATEGORIA"]].astype(str).str.strip().replace({"": "Sin categoría", "nan": "Sin categoría", "None": "Sin categoría"})

    # Remove empty codes/names
    out = out[(out["code"] != "") & (out["name"] != "")]
    # Keep unique codes (last wins)
    out = out.drop_duplicates(subset=["code"], keep="last")

    return out

