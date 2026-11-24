import streamlit as st
from db import DB

st.set_page_config(page_title="Palworld Combo Tracker", layout="wide")


def format_gender(gender: str | None) -> str:
    if gender == "Male":
        return ":blue[♂] Male"
    if gender == "Female":
        return ":red[♀] Female"
    return ""


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

# Map completed combos by unordered parent pair
completed_combos = {}
for p in pals:
    p1, p2 = p.get("parent_1"), p.get("parent_2")
    if p1 and p2 and p.get("complete"):
        completed_combos[frozenset([p1, p2])] = p

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

# Main Combo Matrix Header & Progress
st.title("🧬 Palworld Breeding Combo Tracker")
total_combos = len(males) * len(females)
completed_count = sum(
    1
    for m in males
    for f in females
    if frozenset([m["id"], f["id"]]) in completed_combos
)

st.caption(
    f"Pool: {len(males)} :blue[♂] × {len(females)} :red[♀] = {total_combos} Combinations | "
    f"Completed: {completed_count} / {total_combos}"
)
if total_combos > 0:
    st.progress(completed_count / total_combos)

if not males or not females:
    st.info("Add at least one Male and one Female Pal above to generate combinations.")
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

    for m in males:
        for f in females:
            if selected_parent_id and selected_parent_id not in (m["id"], f["id"]):
                continue

            pair_key = frozenset([m["id"], f["id"]])
            combo_uid = f"{m['id']}__{f['id']}"
            existing_child = completed_combos.get(pair_key)
            is_complete = existing_child is not None

            if hide_completed and is_complete:
                continue

            visible_rows += 1
            col_status, col_pair, col_name, col_gender, col_action = st.columns(
                [0.6, 3.0, 2.5, 2.2, 1.5]
            )

            with col_status:
                st.markdown("🟢" if is_complete else "🟠")

            with col_pair:
                st.markdown(f"**{m['pal_name']}** :blue[♂] × **{f['pal_name']}** :red[♀]")

            default_name = existing_child["pal_name"] if is_complete else ""
            existing_gender = existing_child.get("gender") if is_complete else None
            default_gender_idx = (
                gender_options.index(existing_gender)
                if existing_gender in gender_options
                else None
            )

            with col_name:
                child_name = st.text_input(
                    "Offspring Name",
                    value=default_name,
                    key=f"name_{combo_uid}",
                    label_visibility="collapsed",
                    placeholder="Enter hatched Pal name...",
                    disabled=is_complete,
                )

            with col_gender:
                child_gender = st.radio(
                    "Offspring Gender",
                    options=gender_options,
                    index=default_gender_idx,
                    format_func=format_gender,
                    horizontal=True,
                    key=f"gender_{combo_uid}",
                    label_visibility="collapsed",
                    disabled=is_complete,
                )

            with col_action:
                can_register = bool(child_name.strip()) and bool(child_gender) and not is_complete
                if st.button(
                    "Registered" if is_complete else "Register",
                    key=f"btn_{combo_uid}",
                    disabled=not can_register,
                    use_container_width=True,
                ):
                    clean_child = child_name.strip()
                    child_id = f"{clean_child}_{child_gender}"

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
