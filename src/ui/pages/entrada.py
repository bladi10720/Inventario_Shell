from __future__ import annotations

from datetime import date

import streamlit as st

from ...auth import AuthState
from ...db import get_engine
from ...repo.movements import get_stock_by_code, insert_movement
from ...repo.products import get_product


def render(*, auth: AuthState) -> None:
    st.header("Entradas")

    engine = get_engine()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        code = st.text_input("Código", placeholder="Ej: 959523")
    with col2:
        qty = st.number_input("Cantidad", min_value=1, step=1, value=1)
    with col3:
        movement_date = st.date_input("Fecha", value=date.today())

    code_norm = (code or "").strip()
    product = None
    stock = None
    if code_norm:
        try:
            product = get_product(engine=engine, code=code_norm)
            if product:
                stock = get_stock_by_code(engine=engine, code=code_norm)
        except Exception as e:  # noqa: BLE001
            st.error(f"Error consultando producto/stock: {e}")

    if code_norm and not product:
        st.warning("Código no encontrado en productos.")

    if product:
        st.success(f"{product.name} — {product.category}")
        if stock is not None:
            st.caption(f"Stock actual: {stock}")

    if st.button("Guardar entrada", type="primary", disabled=not bool(code_norm)):
        if not code_norm:
            st.error("Ingresa un código.")
            return
        if not product:
            st.error("El código no existe en el catálogo de productos.")
            return
        try:
            insert_movement(
                engine=engine,
                movement_type="IN",
                movement_date=movement_date,
                product_code=code_norm,
                qty=int(qty),
                actor_role=auth.role,
            )
            st.success("Entrada registrada.")
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo registrar la entrada: {e}")

