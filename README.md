# Research project page

This is a standalone static site on the `website` branch. It adapts the [`ripl/nerfies-template` `website` branch](https://github.com/ripl/nerfies-template/tree/website) for Nabin Oli's CMP6200 project, *Verifiable Reward Modelling for Automated Manim Animation and Audio Synthesis*.

The page content and four research figures come from `END_REPORT/combined_report/poster/poster.tex`. Four supplied MP4 examples are included in `static/videos/`. They contain H.264 video and AAC stereo audio, and the page uses native HTML video controls without muting.

## Preview

Open `index.html` in a browser or serve this branch's root with any static HTTP server. Run the local asset and video markup check with:

```bash
python verify.py
```

## GitHub Pages

The root workflow `.github/workflows/deploy-pages.yml` publishes this branch root on every push to `website` and from the Actions tab. Enable GitHub Pages with **Build and deployment → Source: GitHub Actions** if the repository has not used Pages before. The published URL for this repository is expected to be `https://nabin2004.github.io/AOS/`.

The page is based on the Nerfies project-page template. Its CSS and original layout are retained with attribution in the page footer.
