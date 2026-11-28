import streamlit as st
from db import DB

st.set_page_config(page_title="Palworld Combo Tracker", layout="wide")


def format_gender(gender: str | None) -> str:
    if gender == "Male":
        return ":blue[♂] Male"
    if gender == "Female":
        return ":red[♀] Female"
    return ""


def is_same_pal(m: dict, f: dict) -> bool:
    m_name = (m.get("pal_name") or "").strip().lower()
    f_name = (f.get("pal_name") or "").strip().lower()
    return bool(m_name) and m_name == f_name


@st.cache_resource
def get_db_obj():
    return DB(st.secrets["supabase"]["url"])


db_obj = get_db_obj()

# Load Pals from Postgres
pals = db_obj.fetch_all_pals()

males = [p for p in pals if p.get("gender") == "Male"]
females = [p for p in pals if p.get("gender") == "Female"]
all_parent_options = {
    p["id"]: f"{p['pal_name']} ({':blue[♂]' if p['gender'] == 'Male' else ':red[♀]'})"
    for p in males + females
}

# Map completed combos by unordered parent pair -> list of registered offspring (max 2: M & F)
completed_combos: dict[frozenset, list[dict]] = {}
for p in pals:
    p1, p2 = p.get("parent_1"), p.get("parent_2")
    if p1 and p2 and p.get("complete"):
        pair_key = frozenset([p1, p2])
        completed_combos.setdefault(pair_key, []).append(p)

# Add Base / Wild Pal to Pool
with st.expander("➕ Add Base / Wild Pal to Pool"):
    with st.form("add_base_pal", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2.2, 1.5])
        base_name = c1.text_input("Pal Name (e.g., Splatterina #1)")
        base_gender = c2.radio(
            "Gender",
            options=["Male", "Female"],
            format_func=format_gender,
            horizontal=True,
        )
        submitted = c3.form_submit_button("Add to Pool", use_container_width=True)

        if submitted and base_name.strip() and base_gender:
            clean_name = base_name.strip()
            unique_id = f"{clean_name}_{base_gender}"
            db_obj.upsert_pal(
                pal_id=unique_id,
                pal_name=clean_name,
                gender=base_gender,
                parent_1=None,
                parent_2=None,
                complete=False,
            )
            st.rerun()

# Build valid cross-gender pairs excluding same-Pal pairings
valid_pairs = [
    (m, f)
    for m in males
    for f in females
    if not is_same_pal(m, f)
]

# Main Combo Matrix Header & Progress
st.title("🧬 Palworld Breeding Combo Tracker")
total_combos = len(valid_pairs)
fully_completed_count = sum(
    1
    for m, f in valid_pairs
    if len(completed_combos.get(frozenset([m["id"], f["id"]]), [])) >= 2
)
partial_count = sum(
    1
    for m, f in valid_pairs
    if len(completed_combos.get(frozenset([m["id"], f["id"]]), [])) == 1
)

st.caption(
    f"Pool: {len(males)} :blue[♂] × {len(females)} :red[♀] = {total_combos} Valid Combos | "
    f"Full (2/2): {fully_completed_count} | Partial (1/2): {partial_count}"
)
if total_combos > 0:
    st.progress(fully_completed_count / total_combos)

if not valid_pairs:
    st.info("Add distinct Male and Female Pals above to generate valid combinations.")
else:
    # Filter Controls
    f_col1, f_col2 = st.columns([2, 1])
    selected_parent_id = f_col1.selectbox(
        "Show combos involving:",
        options=[""] + list(all_parent_options.keys()),
        format_func=lambda pid: "All Pals" if pid == "" else all_parent_options[pid],
    )
    hide_completed = f_col2.toggle("Hide completed (🟢)", value=False)

    st.divider()

    # Touch-friendly column layout for iPad
    h_status, h_pair, h_name, h_gender, h_action = st.columns([0.6, 3.0, 2.5, 2.2, 1.5])
    h_status.markdown("**Status**")
    h_pair.markdown("**Parent Pair (:blue[♂] × :red[♀])**")
    h_name.markdown("**Offspring Name**")
    h_gender.markdown("**Gender**")
    h_action.markdown("**Action**")

    visible_rows = 0
    gender_options = ["Male", "Female"]

    for m, f in valid_pairs:
        if selected_parent_id and selected_parent_id not in (m["id"], f["id"]):
            continue

        pair_key = frozenset([m["id"], f["id"]])
        combo_uid = f"{m['id']}__{f['id']}"
        registered_children = completed_combos.get(pair_key, [])
        registered_genders = {c.get("gender") for c in registered_children}
        is_fully_complete = len(registered_children) >= 2

        if hide_completed and is_fully_complete:
            continue

        visible_rows += 1
        col_status, col_pair, col_name, col_gender, col_action = st.columns(
            [0.6, 3.0, 2.5, 2.2, 1.5]
        )

        with col_status:
            if is_fully_complete:
                st.markdown("🟢")
            elif len(registered_children) == 1:
                st.markdown("🟡")
            else:
                st.markdown("🟠")

        with col_pair:
            st.markdown(f"**{m['pal_name']}** :blue[♂] × **{f['pal_name']}** :red[♀]")
            if registered_children:
                badges = ", ".join(
                    f"{c['pal_name']} ({':blue[♂]' if c.get('gender') == 'Male' else ':red[♀]'})"
                    for c in registered_children
                )
                st.caption(f"Registered ({len(registered_children)}/2): {badges}")

        latest_child = registered_children[-1] if registered_children else None
        default_name = latest_child["pal_name"] if latest_child else ""

        available_genders = [g for g in gender_options if g not in registered_genders]
        default_gender_idx = (
            gender_options.index(latest_child["gender"])
            if is_fully_complete and latest_child and latest_child.get("gender") in gender_options
            else None
        )

        with col_name:
            child_name = st.text_input(
                "Offspring Name",
                value=default_name,
                key=f"name_{combo_uid}_{len(registered_children)}",
                label_visibility="collapsed",
                placeholder="Enter hatched Pal name...",
                disabled=is_fully_complete,
            )

        with col_gender:
            if is_fully_complete:
                child_gender = st.radio(
                    "Offspring Gender",
                    options=gender_options,
                    index=default_gender_idx,
                    format_func=format_gender,
                    horizontal=True,
                    key=f"gender_{combo_uid}_done",
                    label_visibility="collapsed",
                    disabled=True,
                )
            else:
                child_gender = st.radio(
                    "Offspring Gender",
                    options=available_genders,
                    index=None,
                    format_func=format_gender,
                    horizontal=True,
                    key=f"gender_{combo_uid}_{len(registered_children)}",
                    label_visibility="collapsed",
                )

        with col_action:
            same_gender_blocked = child_gender in registered_genders
            can_register = (
                bool(child_name.strip())
                and bool(child_gender)
                and not is_fully_complete
                and not same_gender_blocked
            )
            button_label = (
                "Full (2/2)"
                if is_fully_complete
                else f"Register ({len(registered_children)}/2)"
            )
            if st.button(
                button_label,
                key=f"btn_{combo_uid}_{len(registered_children)}",
                disabled=not can_register,
                use_container_width=True,
            ):
                clean_child = child_name.strip()
                child_id = f"{clean_child}_{child_gender}_{m['id']}_{f['id']}"

                db_obj.upsert_pal(
                    pal_id=child_id,
                    pal_name=clean_child,
                    gender=child_gender,
                    parent_1=m["id"],
                    parent_2=f["id"],
                    complete=True,
                )
                st.rerun()

    if visible_rows == 0:
        st.info("No matching combinations under the current filters.")
