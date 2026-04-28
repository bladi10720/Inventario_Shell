from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import streamlit as st

from .config import Settings

Role = Literal["admin", "operador"]


@dataclass(frozen=True)
class AuthState:
    role: Role


def get_auth_state() -> AuthState | None:
    role = st.session_state.get("auth_role")
    if role in ("admin", "operador"):
        return AuthState(role=role)
    return None


def require_auth(settings: Settings) -> AuthState:
    auth = get_auth_state()
    if auth:
        return auth

    st.title("Inventario")
    st.subheader("Acceso por PIN")
    pin = st.text_input("PIN", type="password")

    if st.button("Entrar", type="primary"):
        normalized = (pin or "").strip()
        if normalized == settings.pin_admin:
            st.session_state["auth_role"] = "admin"
            st.rerun()
        elif normalized == settings.pin_operador:
            st.session_state["auth_role"] = "operador"
            st.rerun()
        else:
            st.error("PIN incorrecto.")

    st.stop()


def logout_button() -> None:
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.pop("auth_role", None)
        st.rerun()

