from __future__ import annotations

from dataclasses import dataclass

import streamlit as st
from sqlalchemy.exc import OperationalError, ProgrammingError

from .config import Settings
from .db import get_engine
from .repo.roles import lookup_pin


@dataclass(frozen=True)
class AuthState:
    """role: slug stored in movements.actor_role; is_admin unlocks admin screens."""

    role: str
    display_name: str
    is_admin: bool


def get_auth_state() -> AuthState | None:
    role = st.session_state.get("auth_role")
    if not isinstance(role, str):
        return None
    role = role.strip()
    if not role:
        return None

    display = st.session_state.get("auth_display_name")
    if not isinstance(display, str) or not display.strip():
        display = "Administrador" if role == "admin" else ("Operador" if role == "operador" else role)

    raw_admin = st.session_state.get("auth_is_admin")
    if raw_admin is None:
        is_admin = role == "admin"
    else:
        is_admin = bool(raw_admin)

    return AuthState(role=role, display_name=display.strip(), is_admin=is_admin)


def require_auth(settings: Settings) -> AuthState:
    auth = get_auth_state()
    if auth:
        return auth

    st.title("Inventario")
    st.subheader("Acceso por PIN")
    st.caption(
        "Puedes usar los PIN definidos en el servidor (admin / operador) "
        "o los PIN que el administrador haya configurado en **Roles y PINs**."
    )
    pin = st.text_input("PIN", type="password")

    if st.button("Entrar", type="primary"):
        normalized = (pin or "").strip()
        if not normalized:
            st.error("Ingresa un PIN.")
        else:
            row = None
            try:
                row = lookup_pin(engine=get_engine(), pin=normalized)
            except (ProgrammingError, OperationalError):
                row = None

            if row:
                slug, display_name, is_admin = row
                st.session_state["auth_role"] = slug
                st.session_state["auth_display_name"] = display_name
                st.session_state["auth_is_admin"] = is_admin
                st.rerun()
            elif normalized == settings.pin_admin:
                st.session_state["auth_role"] = "admin"
                st.session_state["auth_display_name"] = "Administrador"
                st.session_state["auth_is_admin"] = True
                st.rerun()
            elif normalized == settings.pin_operador:
                st.session_state["auth_role"] = "operador"
                st.session_state["auth_display_name"] = "Operador"
                st.session_state["auth_is_admin"] = False
                st.rerun()
            else:
                st.error("PIN incorrecto.")

    st.stop()


def logout_button() -> None:
    if st.sidebar.button("Cerrar sesión"):
        for k in ("auth_role", "auth_display_name", "auth_is_admin"):
            st.session_state.pop(k, None)
        st.rerun()
