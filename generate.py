"""CLI / automation: python generate.py --title "..." --theme navy --variants 3"""
import argparse

from core import THEME_MAP, generate_batch


def main():
    ap = argparse.ArgumentParser(description="Free AI blog featured-image generator")
    ap.add_argument("--title", required=True, help="Blog post title (drawn on the image)")
    ap.add_argument("--theme", default="navy", choices=sorted(THEME_MAP),
                    help="Colour theme (15 available)")
    ap.add_argument("--variants", type=int, default=3, help="How many images to make")
    ap.add_argument("--layout", default="right", choices=["right", "bottom"])
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--visual-hint", default="", help="Custom visual keywords")
    ap.add_argument("--seed", type=int, default=None, help="Base seed for reproducibility")
    ap.add_argument("--provider", default="pollinations", choices=["pollinations", "gemini"])
    ap.add_argument("--gemini-key", default=None, help="Free Google AI Studio key")
    ap.add_argument("--model", default="flux", choices=["flux", "turbo"],
                    help="Pollinations model (turbo = faster)")
    ap.add_argument("--size", type=int, default=1024, help="AI square size (smaller = faster)")
    ap.add_argument("--sizes", nargs="+", default=["desktop"],
                    choices=["desktop", "mobile"],
                    help="Output size(s): desktop=1200x629, mobile=450x236")
    args = ap.parse_args()

    print(f"Theme: {args.theme} | variants: {args.variants} | provider: {args.provider} | sizes: {args.sizes}")
    paths, prompt = generate_batch(
        title=args.title, theme_id=args.theme, variants=args.variants,
        layout=args.layout, subtitle=args.subtitle,
        visual_hint=args.visual_hint or None, base_seed=args.seed,
        provider=args.provider, size=args.size, model=args.model,
        api_key=args.gemini_key, sizes=args.sizes,
    )
    print("Prompt:", prompt[:120], "...")
    for p in paths:
        print("saved:", p)


if __name__ == "__main__":
    main()
