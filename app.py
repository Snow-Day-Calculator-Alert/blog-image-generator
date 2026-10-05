"""Web UI: run with  streamlit run app.py"""
import io
import os

import streamlit as st
from PIL import Image

from core import THEMES, generate_batch

st.set_page_config(page_title="Blog Image Generator", page_icon="🎨", layout="wide")
st.title("🎨 Blog Image Generator")
st.caption("Same design language every time — free AI illustration + crisp local title. No paid APIs.")

with st.sidebar:
    st.header("Settings")
    theme_names = [t["name"] for t in THEMES]
    theme_idx = st.selectbox("Colour theme", range(len(theme_names)),
                             format_func=lambda i: theme_names[i])
    layout = st.radio("Layout",
                      ["right", "bottom"],
                      format_func=lambda x: "Title on right (reference style)" if x == "right" else "Title strip at bottom")
    size_choice = st.radio("Image size",
                           ["desktop", "mobile", "both"],
                           format_func=lambda x: {"desktop": "Desktop (1200×629)",
                                                  "mobile": "Mobile (450×236)",
                                                  "both": "Both sizes"}[x])
    variants = st.slider("Variants to generate", 1, 4, 2)
    provider = st.radio("Image provider",
                        ["pollinations", "gemini"],
                        format_func=lambda x: "Pollinations (free, no key)" if x == "pollinations" else "Gemini (free AI Studio key)")
    gemini_key = ""
    if provider == "gemini":
        gemini_key = st.text_input("Gemini API key", type="password",
                                   help="Free key from Google AI Studio")
    base_seed = st.number_input("Base seed (same seed = same composition)",
                                min_value=0, max_value=999999, value=42)

st.subheader("Blog post")
title = st.text_input("Blog title", "Inside SOA OS23: A New Perspective on Software Architecture")
subtitle = st.text_input("Subtitle (optional)", "")
visual_hint = st.text_input("Visual keywords (optional — auto-extracted from title if empty)",
                            help="e.g. 'microservices api gateway cloud'")
uploaded = st.file_uploader("…or use your OWN base image instead of AI (optional)",
                            type=["png", "jpg", "jpeg", "webp"])

if st.button("🚀 Generate", type="primary", disabled=not title.strip()):
    theme_id = THEMES[theme_idx]["id"]
    sizes = ["desktop", "mobile"] if size_choice == "both" else [size_choice]
    custom_image = Image.open(uploaded) if uploaded else None
    progress = st.progress(0, text="Working…")
    try:
        with st.spinner("Generating illustrations… (free AI, ~30–60s each)"):
            paths, prompt = generate_batch(
                title=title.strip(),
                theme_id=theme_id,
                variants=variants,
                layout=layout,
                subtitle=subtitle.strip(),
                visual_hint=visual_hint,
                base_seed=int(base_seed),
                provider=provider,
                api_key=gemini_key or None,
                custom_image=custom_image,
                sizes=sizes,
            )
        progress.progress(1.0, text="Done!")
        st.success(f"Generated {len(paths)} image(s) in the **{THEMES[theme_idx]['name']}** theme.")
        with st.expander("Style prompt used (this is what keeps the design consistent)"):
            st.code(prompt)
        cols = st.columns(min(len(paths), 2))
        for i, p in enumerate(paths):
            with cols[i % len(cols)]:
                st.image(p, use_container_width=True)
                with open(p, "rb") as f:
                    st.download_button("⬇ Download PNG", f,
                                       file_name=os.path.basename(p),
                                       key=f"dl_{i}")
    except Exception as e:  # noqa: BLE001
        st.error(f"Something failed: {e}")
        st.info("Pollinations is a free shared service — if it is busy, wait a minute and retry, "
                "or switch to the Gemini provider with a free AI Studio key.")
