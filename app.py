from __future__ import annotations

import streamlit as st

from src.auth import logout_button, require_auth
from src.config import load_settings


def main() -> None:
    st.set_page_config(page_title="Inventario", layout="wide")

    settings = load_settings()
    auth = require_auth(settings)

    st.sidebar.title("Inventario")
    st.sidebar.caption(f"Rol: {auth.role}")
    logout_button()

    page = st.sidebar.radio(
        "Menú",
        options=[
            "Entradas",
            "Salidas diarias",
            "Inventario",
            "Alertas",
            "Ajuste stock (admin)",
            "Productos (admin)",
        ],
    )

    if page == "Entradas":
        from src.ui.pages.entrada import render as render_entrada

        render_entrada(auth=auth)
    elif page == "Salidas diarias":
        from src.ui.pages.salida_diaria import render as render_salida

        render_salida(auth=auth)
    elif page == "Inventario":
        from src.ui.pages.inventario import render as render_inventario

        render_inventario(auth=auth)
    elif page == "Alertas":
        from src.ui.pages.alertas import render as render_alertas

        render_alertas(auth=auth)
    elif page == "Ajuste stock (admin)":
        from src.ui.pages.ajuste_stock_admin import render as render_ajuste

        render_ajuste(auth=auth)
    elif page == "Productos (admin)":
        from src.ui.pages.productos_admin import render as render_productos

        render_productos(auth=auth)
    else:
        st.write("Selecciona una opción del menú.")


if __name__ == "__main__":
    main()

