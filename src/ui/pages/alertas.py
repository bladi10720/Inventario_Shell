from __future__ import annotations

import streamlit as st

from ...auth import AuthState
from ...db import get_engine
from ...repo.movements import list_low_stock
from ...repo.products import list_categories


def render(*, auth: AuthState) -> None:
    st.header("Alertas")
    engine = get_engine()

    categories = ["Todas"] + list_categories(engine=engine)
    selected_category = st.selectbox("Categoría", options=categories)

    low = list_low_stock(engine=engine, threshold=2, category=selected_category)
    if not low:
        st.success("No hay productos con stock bajo (0 o 1).")
        return

    st.caption(f"Alertas: {len(low)} (stock < 2)")

    cols = st.columns(3)
    for i, r in enumerate(low):
        col = cols[i % 3]
        with col:
            if r.stock <= 0:
                st.error(f"{r.code} — AGOTADO")
            else:
                st.warning(f"{r.code} — ÚLTIMA UNIDAD")
            st.write(r.name)
            st.caption(r.category)
            st.metric("Stock", r.stock)

