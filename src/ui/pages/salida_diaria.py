from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from ...auth import AuthState
from ...db import get_engine
from ...repo.movements import insert_daily_out_batch, void_out_closure
from ...repo.products import get_product
from ...repo.movements import get_stock_by_code


def render(*, auth: AuthState) -> None:
    st.header("Salidas diarias")
    engine = get_engine()

    default_day = date.today() - timedelta(days=1)
    movement_date = st.date_input("Fecha de ventas (por defecto: ayer)", value=default_day)

    st.caption("Formato por línea: `codigo cantidad` (separado por espacio). Ejemplo: `959523 2`")
    raw = st.text_area("Pega o escribe aquí", height=220, placeholder="959523 2\n965174 1")

    col1, col2 = st.columns([1, 1])
    validate_clicked = col1.button("Validar")
    save_clicked = col2.button("Guardar salidas", type="primary")

    if "daily_out_items" not in st.session_state:
        st.session_state["daily_out_items"] = []

    if validate_clicked:
        try:
            items = _parse_lines(raw)
        except Exception as e:  # noqa: BLE001
            st.error(f"Error al parsear: {e}")
            items = []

        preview: list[_PreviewRow] = []
        errors: list[str] = []
        for code, qty in items.items():
            p = get_product(engine=engine, code=code)
            if not p:
                errors.append(f"Código no existe: {code}")
                continue
            stock = get_stock_by_code(engine=engine, code=code)
            if stock is None:
                errors.append(f"No se pudo calcular stock para: {code}")
                continue
            if stock < qty:
                errors.append(f"Stock insuficiente: {code} — disponible {stock}, solicitado {qty}")
            preview.append(_PreviewRow(code=code, name=p.name, category=p.category, stock=stock, qty=qty))

        if errors:
            st.error("Corrige estos problemas antes de guardar:")
            for e in errors:
                st.write(f"- {e}")

        if preview:
            st.subheader("Vista previa")
            st.dataframe([r.__dict__ for r in preview], use_container_width=True)

        # Save only the valid/known items; we still require no errors to proceed on save.
        st.session_state["daily_out_items"] = [{"product_code": r.code, "qty": r.qty} for r in preview]
        st.session_state["daily_out_has_errors"] = bool(errors)

    if save_clicked:
        items = st.session_state.get("daily_out_items") or []
        has_errors = bool(st.session_state.get("daily_out_has_errors"))
        if not raw.strip():
            st.error("No hay líneas para procesar.")
            return
        if not items:
            st.error("Primero valida y asegúrate de que haya productos válidos.")
            return
        if has_errors:
            st.error("Hay errores de validación. Corrige y vuelve a validar.")
            return

        try:
            insert_daily_out_batch(engine=engine, movement_date=movement_date, items=items, actor_role=auth.role)
            st.success("Salidas guardadas.")
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
            if auth.role == "admin":
                st.warning("Si necesitas corregir, puedes anular el cierre y volver a cargar.")
                if st.button("Anular cierre de esta fecha (admin)"):
                    try:
                        void_out_closure(engine=engine, movement_date=movement_date)
                        st.success("Cierre anulado. Ahora puedes volver a cargar y guardar.")
                    except Exception as e2:  # noqa: BLE001
                        st.error(f"No se pudo anular: {e2}")


@dataclass(frozen=True)
class _PreviewRow:
    code: str
    name: str
    category: str
    stock: int
    qty: int


def _parse_lines(raw: str) -> dict[str, int]:
    """
    Parse lines like: CODE QTY
    Consolidates repeated codes by summing.
    """
    out: dict[str, int] = {}
    for idx, line in enumerate((raw or "").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue

        parts = stripped.replace(",", " ").split()
        if len(parts) != 2:
            raise ValueError(f"Línea {idx}: formato inválido. Usa `codigo cantidad`.")
        code, qty_s = parts[0].strip(), parts[1].strip()
        if not code:
            raise ValueError(f"Línea {idx}: código vacío.")
        try:
            qty = int(qty_s)
        except ValueError as e:
            raise ValueError(f"Línea {idx}: cantidad inválida: {qty_s}") from e
        if qty <= 0:
            raise ValueError(f"Línea {idx}: cantidad debe ser > 0.")

        out[code] = out.get(code, 0) + qty
    return out

