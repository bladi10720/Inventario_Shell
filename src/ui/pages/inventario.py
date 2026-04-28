from __future__ import annotations

import streamlit as st

from ...auth import AuthState
from ...db import get_engine
from ...repo.movements import get_stock_by_code, list_inventory
from ...repo.products import get_product, list_categories


def render(*, auth: AuthState) -> None:
    st.header("Inventario")
    engine = get_engine()

    st.subheader("Buscar por código")
    code = st.text_input("Código", placeholder="Ej: 959523")
    code_norm = (code or "").strip()
    if code_norm:
        p = get_product(engine=engine, code=code_norm)
        if not p:
            st.warning("Código no encontrado.")
        else:
            stock = get_stock_by_code(engine=engine, code=code_norm)
            st.success(f"{p.name} — {p.category}")
            st.metric("Stock", value=int(stock or 0))

    st.divider()
    st.subheader("Listado")
    categories = ["Todas"] + list_categories(engine=engine)
    selected_category = st.selectbox("Categoría", options=categories)
    only_active = st.checkbox("Solo activos", value=True)

    rows = list_inventory(engine=engine, category=selected_category, only_active=only_active)
    st.caption(f"Productos: {len(rows)}")

    table = [
        {"codigo": r.code, "producto": r.name, "categoria": r.category, "stock": r.stock}
        for r in rows
    ]
    st.dataframe(table, use_container_width=True)

