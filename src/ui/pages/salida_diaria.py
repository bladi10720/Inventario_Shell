from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from ...auth import AuthState
from ...db import get_engine
from ...repo.movements import insert_daily_out_batch, void_out_closure_and_delete_out_movements
from ...repo.products import get_product
from ...repo.movements import get_stock_by_code


def render(*, auth: AuthState) -> None:
    st.header("Salidas diarias")
    engine = get_engine()

    default_day = date.today() - timedelta(days=1)
    movement_date = st.date_input("Fecha de ventas (por defecto: ayer)", value=default_day)

    # Reset input widgets on next run to avoid StreamlitAPIException.
    if st.session_state.pop("_reset_daily_out_inputs", False):
        st.session_state["daily_out_code"] = ""
        st.session_state["daily_out_qty"] = 1

    if "daily_out_cart" not in st.session_state:
        st.session_state["daily_out_cart"] = {}  # code -> qty
    if "daily_out_validated" not in st.session_state:
        st.session_state["daily_out_validated"] = False

    st.subheader("Agregar producto")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        code = st.text_input("Código", key="daily_out_code", placeholder="Ej: 959523")
    with c2:
        qty = st.number_input("Cantidad", key="daily_out_qty", min_value=1, step=1, value=1)
    with c3:
        add_clicked = st.button("Agregar", type="primary")

    code_norm = (code or "").strip()
    if add_clicked:
        if not code_norm:
            st.error("Ingresa un código.")
        else:
            p = get_product(engine=engine, code=code_norm)
            if not p:
                st.error("El código no existe en productos.")
            else:
                cart: dict[str, int] = st.session_state["daily_out_cart"]
                cart[code_norm] = int(cart.get(code_norm, 0)) + int(qty)
                st.session_state["daily_out_cart"] = cart
                st.session_state["daily_out_validated"] = False
                st.session_state["_reset_daily_out_inputs"] = True
                st.rerun()

    st.divider()
    st.subheader("Pendiente por guardar")
    cart = st.session_state["daily_out_cart"]
    if not cart:
        st.info("No hay productos agregados todavía.")
        return

    # Build preview rows
    preview_rows = []
    errors: list[str] = []
    for c, q in cart.items():
        p = get_product(engine=engine, code=c)
        if not p:
            errors.append(f"Código no existe: {c}")
            continue
        stock = get_stock_by_code(engine=engine, code=c)
        if stock is None:
            errors.append(f"No se pudo calcular stock para: {c}")
            continue
        status = "OK" if stock >= q else f"Stock insuficiente (disp {stock})"
        preview_rows.append(
            {
                "codigo": c,
                "producto": p.name,
                "categoria": p.category,
                "stock_actual": stock,
                "cantidad": q,
                "estado": status,
            }
        )

    st.dataframe(preview_rows, use_container_width=True)

    total_items = len(preview_rows)
    total_units = sum(int(r["cantidad"]) for r in preview_rows)
    st.caption(f"Productos: {total_items} — Unidades: {total_units}")

    # Remove items UI
    with st.expander("Quitar productos", expanded=False):
        to_remove = st.multiselect("Selecciona códigos a quitar", options=sorted(cart.keys()))
        if st.button("Quitar seleccionados"):
            for c in to_remove:
                cart.pop(c, None)
            st.session_state["daily_out_cart"] = cart
            st.session_state["daily_out_validated"] = False
            st.rerun()

    cval, csave, cclear = st.columns([1, 1, 1])
    validate_clicked = cval.button("Validar")
    save_clicked = csave.button("Guardar todo", type="primary", disabled=not bool(st.session_state.get("daily_out_validated")))
    clear_clicked = cclear.button("Limpiar lista")

    if clear_clicked:
        st.session_state["daily_out_cart"] = {}
        st.session_state["daily_out_validated"] = False
        st.rerun()

    if validate_clicked:
        errors = []
        for r in preview_rows:
            if r["estado"] != "OK":
                errors.append(f"{r['codigo']}: {r['estado']}")
        if errors:
            st.session_state["daily_out_validated"] = False
            st.error("Corrige antes de guardar:")
            for e in errors:
                st.write(f"- {e}")
            st.rerun()
        else:
            st.session_state["daily_out_validated"] = True
            st.success("Validación OK. Ya puedes guardar.")
            st.rerun()

    if save_clicked:
        items = [{"product_code": c, "qty": int(q)} for c, q in cart.items()]
        try:
            insert_daily_out_batch(engine=engine, movement_date=movement_date, items=items, actor_role=auth.role)
            st.success("Salidas guardadas y cierre creado.")
            st.session_state["daily_out_cart"] = {}
            st.session_state["daily_out_validated"] = False
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
            st.session_state["daily_out_validated"] = False
            if auth.role == "admin":
                st.warning("Si necesitas corregir, puedes anular el cierre y volver a cargar.")
                if st.button("Anular cierre de esta fecha (admin)"):
                    try:
                        deleted = void_out_closure_and_delete_out_movements(engine=engine, movement_date=movement_date)
                        st.success(f"Cierre anulado y salidas eliminadas para esa fecha. Filas eliminadas: {deleted}.")
                    except Exception as e2:  # noqa: BLE001
                        st.error(f"No se pudo anular: {e2}")

