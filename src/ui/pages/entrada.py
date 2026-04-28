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

    # Reset widgets on next run (avoid StreamlitAPIException by not mutating widget keys
    # after instantiation in the same run).
    if st.session_state.pop("_reset_in_widgets", False):
        st.session_state["in_code"] = ""
        st.session_state["in_qty"] = 1
        st.session_state["in_supplier"] = ""
        st.session_state["in_folio"] = ""
        st.session_state["in_note"] = ""

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        code = st.text_input("Código", key="in_code", placeholder="Ej: 959523")
    with col2:
        qty = st.number_input("Cantidad", key="in_qty", min_value=1, step=1, value=1)
    with col3:
        movement_date = st.date_input("Fecha", key="in_date", value=date.today())

    st.subheader("Referencia (opcional)")
    r1, r2, r3 = st.columns([1, 1, 2])
    with r1:
        proveedor = st.text_input("Proveedor", key="in_supplier")
    with r2:
        folio = st.text_input("Folio/Factura", key="in_folio")
    with r3:
        nota = st.text_input("Nota", key="in_note")

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
            note_parts = []
            if proveedor.strip():
                note_parts.append(f"Proveedor: {proveedor.strip()}")
            if folio.strip():
                note_parts.append(f"Folio: {folio.strip()}")
            if nota.strip():
                note_parts.append(nota.strip())
            note_text = " | ".join(note_parts) if note_parts else None

            insert_movement(
                engine=engine,
                movement_type="IN",
                movement_date=movement_date,
                product_code=code_norm,
                qty=int(qty),
                actor_role=auth.role,
                note=note_text,
            )
            new_stock = get_stock_by_code(engine=engine, code=code_norm)
            st.success(f"Entrada registrada. Nuevo stock: {int(new_stock or 0)}")
            st.session_state["_reset_in_widgets"] = True
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo registrar la entrada: {e}")

