import plotly.graph_objects as go
import streamlit as st

from models import CATEGORIES, load_characters

MAX_RATING = 5.0

# Distinct hues; each player gets one, with a translucent fill for the FIFA look.
PALETTE = [
    "#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9A6324", "#800000", "#808000", "#000075",
]


def category_overall(char: dict, category: str) -> float:
    stats = char[category]
    return sum(stats.values()) / len(stats)


def grand_overall(char: dict, categories: dict[str, list[str]]) -> float:
    values = [v for cat in categories for v in char[cat].values()]
    return sum(values) / len(values)


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def build_radar(characters: dict, selected: list[str], view: str,
                categories: dict[str, list[str]]) -> go.Figure:
    if view == "Overall":
        axes = list(categories.keys())
        axis_labels = [c.replace("_", " ").title() for c in axes]

        def value_for(char, axis):
            return category_overall(char, axis)
    else:
        axes = categories[view]
        axis_labels = [a.replace("_", " ").title() for a in axes]

        def value_for(char, axis):
            return char[view][axis]

    # Close the polygon by repeating the first axis.
    closed_labels = axis_labels + axis_labels[:1]

    fig = go.Figure()
    for i, name in enumerate(selected):
        char = characters[name]
        values = [value_for(char, a) for a in axes]
        values += values[:1]
        color = PALETTE[i % len(PALETTE)]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=closed_labels,
                fill="toself",
                name=name.replace("_", " ").title(),
                line=dict(color=color, width=2),
                fillcolor=rgba(color, 0.25),
                hovertemplate="%{theta}: %{r:.2f}<extra>" + name + "</extra>",
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, MAX_RATING])),
        showlegend=True,
        height=600,
        margin=dict(l=60, r=60, t=40, b=40),
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="Ultimate XI", layout="wide")
    st.title("Ultimate XI — Stat Comparison")

    characters = load_characters()
    categories = CATEGORIES
    view_options = ["Overall"] + [c.replace("_", " ").title() for c in categories]
    label_to_key = {c.replace("_", " ").title(): c for c in categories}

    with st.sidebar:
        st.header("Compare")
        selected = st.multiselect(
            "Characters",
            options=sorted(characters.keys()),
            default=["mario", "bowser"],
            format_func=lambda n: n.replace("_", " ").title(),
        )
        view_label = st.radio("Stat view", view_options, index=0)

    view = "Overall" if view_label == "Overall" else label_to_key[view_label]

    if not selected:
        st.info("Pick at least one character in the sidebar to compare.")
        return

    st.plotly_chart(build_radar(characters, selected, view, categories),
                    use_container_width=True)

    st.subheader("Ratings")
    cols = st.columns(len(selected))
    for col, name in zip(cols, selected):
        char = characters[name]
        with col:
            st.markdown(f"**{name.replace('_', ' ').title()}**")
            st.metric("Overall", f"{grand_overall(char, categories):.2f}")
            for cat in categories:
                st.caption(
                    f"{cat.replace('_', ' ').title()}-Overall: "
                    f"{category_overall(char, cat):.2f}"
                )


if __name__ == "__main__":
    main()
