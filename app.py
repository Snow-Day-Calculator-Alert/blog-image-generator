"""Web UI: run with  streamlit run app.py"""
# v1.5 — providers: Pollinations (free) + Gemini + Hugging Face (free token)
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
                        ["pollinations", "gemini", "huggingface"],
                        format_func=lambda x: {"pollinations": "Pollinations (free, no key)",
                                               "gemini": "Gemini (AI Studio key)",
                                               "huggingface": "Hugging Face (free token)"}[x])
    api_key = ""
    if provider in ("gemini", "huggingface"):
        if provider == "gemini":
            label, param = "Gemini API key", "gemini_key"
            help_text = "Key from Google AI Studio (aistudio.google.com/apikey)"
        else:
            label, param = "Hugging Face token", "hf_token"
            help_text = "Free token from huggingface.co/settings/tokens (read access is enough)"
        saved = st.query_params.get(param, "")
        api_key = st.text_input(label, type="password", value=saved, help=help_text)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("💾 Save key", key=f"save_{param}"):
                if api_key.strip():
                    st.query_params[param] = api_key.strip()
                    st.success("Key is URL mein save ho gayi — is page ko bookmark kar lo.")
                else:
                    st.warning("Pehle key paste karo, phir Save dabao.")
        with b2:
            if st.button("🗑 Forget key", key=f"forget_{param}"):
                if param in st.query_params:
                    del st.query_params[param]
                st.rerun()
        st.caption("⚠️ Key sirf is URL mein mehfooz hoti hai (kisi server par nahi). "
                   "Ye link kisi se share na karo — jis ke paas link hoga wo tumhari key/token use kar sakega.")
    base_seed = st.number_input("Base seed (same seed = same composition)",
                                min_value=0, max_value=999999, value=501)
    st.caption("💡 Tip: illustration pasand na aaye to seed badal kar dobara Generate dabao — har seed nayi composition deta hai.")

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
                api_key=api_key or None,
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
