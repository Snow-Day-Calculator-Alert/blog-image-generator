# 🎨 Blog Image Generator — bilkul FREE

Apne blog ke liye **ek jaisi design language** mein featured images banao —
jaise reference image (3D isometric stack + floating cards + side par title).
Koi paid tool/API **nahi** chahiye.

## Kaise kaam karta hai (3 steps)

1. **Style-locked prompt** — ek fixed prompt template har image ko same design
   mein rakhta hai (3D isometric stack, floating icon cards, laptop/tablet).
   Sirf topic keywords aur colour theme badalte hain.
2. **Free AI image** — illustration banti hai:
   - **Pollinations** (default): bilkul free, **koi API key nahi** chahiye.
   - **Gemini** (optional): Google AI Studio ki free key se, zyada accurate.
3. **Title locally** — title Pillow se image par lagta hai, is liye text
   hamesha crisp aur readable hota hai (AI se text likhwana unreliable hai).

## Quickstart (local)

```bash
cd blog-image-generator
pip install -r requirements.txt

# Web UI:
streamlit run app.py

# Ya command line (automation ke liye):
python generate.py --title "Inside SOA OS23: A New Perspective on Software Architecture" \
  --theme navy --variants 3
```

Images `output/` folder mein `1200x630` PNG mein save hoti hain.

## Features

- **15 colour themes**: navy, emerald, violet, crimson, amber, teal, indigo,
  rose, slate, forest, midnight, copper, burgundy, charcoal-gold, steel-blue
- **2 layouts**: title right side par (reference jaisa) / title neeche strip mein
- **Batch variants**: ek click par 1–4 images, alag seeds ke saath
- **Seed control**: same seed + same title = same composition (consistent series)
- **Apni image bhi**: chaaho to AI ki bajaye apni base image upload karke
  us par title lagao
- **CLI**: scripting/automation ke liye `generate.py`

## Free hosting (live karna ho to)

- **Streamlit Community Cloud** (free): GitHub repo connect karo, `app.py` select karo.
- **Hugging Face Spaces** (free): Streamlit SDK space banao, files upload karo.

## Notes

- Pollinations free shared service hai — kabhi busy ho to 1 minute ruk kar
  retry karo, ya Gemini provider use karo (free AI Studio key).
- Fonts (Poppins, OFL licence) pehli run par auto-download hote hain.
- `enhance=false` rakha hai taake AI prompt ko apni marzi se na badle —
  design consistent rahe.
