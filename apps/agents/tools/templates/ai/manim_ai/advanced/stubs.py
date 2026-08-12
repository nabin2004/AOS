"""P2 skeleton concepts for d2l Ch 13–21 (extensible stubs)."""

from __future__ import annotations

from manim import VGroup

from manim_ai.core.base import stub_concept
from manim_ai.core.registry import register_concept

_STUBS: list[tuple[str, str, str, str, str]] = [
    ("data_parallel", "advanced", "13.5", "Multi-GPU Data Parallel", r"\theta \leftarrow \mathrm{AllReduce}(\nabla L)"),
    ("image_augmentation", "advanced", "14.1", "Image Augmentation", r"x' = T(x)"),
    ("bounding_boxes", "advanced", "14.3", "Bounding Boxes", r"(x_1,y_1,x_2,y_2)"),
    ("anchor_boxes", "advanced", "14.4", "Anchor Boxes / IoU", r"\mathrm{IoU}=\frac{|A\cap B|}{|A\cup B|}"),
    ("rcnn_family", "advanced", "14.8", "R-CNN Family", r"\text{R-CNN}\to\text{Fast}\to\text{Faster}\to\text{Mask}"),
    ("fcn_segmentation", "advanced", "14.11", "Fully Convolutional Networks", r"\text{FCN}"),
    ("style_transfer", "advanced", "14.12", "Neural Style Transfer", r"L=L_{\mathrm{content}}+\lambda L_{\mathrm{style}}"),
    ("word2vec", "advanced", "15.1", "word2vec", r"\max \log P(w_o\mid w_c)"),
    ("bert", "advanced", "15.8", "BERT", r"\text{MLM} + \text{NSP}"),
    ("sentiment_rnn", "advanced", "16.2", "Sentiment Analysis (RNN)", r"P(y\mid x)"),
    ("nli_attention", "advanced", "16.5", "NLI with Attention", r"P(\text{entail}\mid p,h)"),
    ("mdp", "advanced", "17.1", "Markov Decision Process", r"(S,A,P,R,\gamma)"),
    ("q_learning", "advanced", "17.3", "Q-Learning", r"Q(s,a)\leftarrow Q(s,a)+\alpha\delta"),
    ("gaussian_process", "advanced", "18.1", "Gaussian Processes", r"f\sim\mathcal{GP}(m,k)"),
    ("hpo_random", "advanced", "19.1", "Hyperparameter Optimization", r"\lambda^\star=\arg\min_\lambda L_{\mathrm{val}}"),
    ("gan", "advanced", "20.1", "GAN", r"\min_G\max_D V(D,G)"),
    ("dcgan", "advanced", "20.2", "DCGAN", r"G:\ z\mapsto x"),
    ("recommender", "advanced", "21.1", "Recommender Systems", r"\hat r_{ui}=p_u^\top q_i"),
    ("builders_modules", "neural_network", "6.1", "Layers and Modules", r"y=f_L\circ\cdots\circ f_1(x)"),
    ("seq2seq", "recurrent", "10.7", "Seq2Seq Encoder–Decoder", r"P(y\mid x)"),
    ("beam_search", "recurrent", "10.8", "Beam Search", r"k\text{-beam}"),
    ("vision_transformer", "transformer", "11.8", "Vision Transformer", r"\text{ViT}"),
    ("intro_ml", "fundamental", "1.1", "Introduction to ML", r"\text{data}+\text{model}+\text{loss}+\text{opt}"),
]


def _register_stub(cid: str, domain: str, chapter: str, title: str, equation: str) -> None:
    def builder(**_kwargs) -> VGroup:
        return stub_concept(title, equation)

    builder.__name__ = f"build_{cid}"
    register_concept(
        id=cid,
        domain=domain,
        chapter=chapter,
        title=title,
        stub=True,
        description=f"Skeleton for {title} (d2l {chapter})",
        tags=["stub"],
    )(builder)


for _cid, _domain, _chapter, _title, _eq in _STUBS:
    _register_stub(_cid, _domain, _chapter, _title, _eq)
