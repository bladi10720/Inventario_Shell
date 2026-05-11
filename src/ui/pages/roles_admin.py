from __future__ import annotations

import streamlit as st
from sqlalchemy.exc import IntegrityError

from ...auth import AuthState
from ...db import get_engine
from ...repo.roles import (
    insert_pin,
    insert_role,
    is_valid_slug,
    list_pins_for_role,
    list_roles,
    set_pin_active,
    update_role,
)


def render(*, auth: AuthState) -> None:
    st.header("Roles y PINs")
    if not auth.is_admin:
        st.error("Acceso solo para administradores.")
        return

    engine = get_engine()

    st.caption(
        "Define roles y asigna PINs. El **slug** se guarda en movimientos (auditoría); el **nombre** se muestra al usuario. "
        "Los PIN del servidor (variables de entorno) siguen funcionando aunque no haya filas aquí."
    )

    with st.expander("Crear rol", expanded=False):
        with st.form("form_new_role"):
            slug_in = st.text_input(
                "Slug interno",
                placeholder="ej: supervisor_bodega",
                help="Solo minúsculas, números y guión bajo; debe empezar con letra. No se puede cambiar después.",
            )
            disp_in = st.text_input("Nombre en pantalla", placeholder="ej: Supervisor bodega")
            adm_in = st.checkbox("Rol administrador (productos, ajustes, roles, reemplazar salidas del día)")
            create_sub = st.form_submit_button("Crear rol", type="primary")
        if create_sub:
            slug_s = (slug_in or "").strip()
            disp_s = (disp_in or "").strip()
            if not disp_s:
                st.error("El nombre en pantalla es obligatorio.")
            elif not is_valid_slug(slug_s):
                st.error(
                    "Slug inválido: usa solo letras minúsculas, números y _; máximo 40 caracteres; debe empezar con letra."
                )
            else:
                try:
                    insert_role(engine=engine, slug=slug_s, display_name=disp_s, is_admin=adm_in)
                    st.success(f"Rol creado: {slug_s}")
                    st.rerun()
                except IntegrityError:
                    st.error("Ese slug ya existe.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"No se pudo crear: {e}")

    st.subheader("Roles existentes")
    roles = list_roles(engine=engine, include_inactive=True)
    if not roles:
        st.info("Todavía no hay roles en la base. Crea uno y luego asigna PINs.")
        return

    for r in roles:
        status = "activo" if r.active else "inactivo"
        with st.expander(f"{r.display_name} (`{r.slug}`) — {status}", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                new_disp = st.text_input("Nombre", value=r.display_name, key=f"rdisp:{r.id}")
            with c2:
                new_adm = st.checkbox("Administrador", value=r.is_admin, key=f"radm:{r.id}")
                new_act = st.checkbox("Rol activo", value=r.active, key=f"ract:{r.id}")

            if st.button("Guardar cambios del rol", key=f"rsave:{r.id}"):
                try:
                    update_role(
                        engine=engine,
                        role_id=r.id,
                        display_name=new_disp,
                        is_admin=new_adm,
                        active=new_act,
                    )
                    st.success("Rol actualizado.")
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))

            st.divider()
            st.caption("PINs para este rol (cada PIN solo puede usarse una vez en toda la app).")
            pins = list_pins_for_role(engine=engine, role_id=r.id)
            for p in pins:
                lab = p.label or "—"
                state = "activo" if p.active else "desactivado"
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.write(f"`{p.pin}` — {lab} ({state})")
                with col_b:
                    if p.active:
                        if st.button("Desactivar PIN", key=f"poff:{p.id}"):
                            set_pin_active(engine=engine, pin_id=p.id, active=False)
                            st.rerun()
                    else:
                        if st.button("Reactivar PIN", key=f"pon:{p.id}"):
                            set_pin_active(engine=engine, pin_id=p.id, active=True)
                            st.rerun()

            with st.form(f"addpin_{r.id}"):
                np = st.text_input("Nuevo PIN", type="password", key=f"npin:{r.id}")
                nl = st.text_input("Etiqueta (opcional)", placeholder="ej: Juan / caja 2", key=f"nlab:{r.id}")
                if st.form_submit_button("Añadir PIN", type="primary"):
                    try:
                        insert_pin(engine=engine, role_id=r.id, pin=np, label=nl or None)
                        st.success("PIN añadido.")
                        st.rerun()
                    except IntegrityError:
                        st.error("Ese PIN ya está en uso (en cualquier rol).")
                    except ValueError as ve:
                        st.error(str(ve))
                    except Exception as e:  # noqa: BLE001
                        st.error(str(e))
