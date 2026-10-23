"""Arte procedural: cenários dark gerados localmente, sem banco de imagens.

Cada cena ganha um "cenário" (arquetipo) derivado do roteiro ou definido no
plano. Tudo é desenhado por código — silhuetas, névoa, brasas, raios de luz —
então não há direitos autorais envolvidos e a fábrica pode gerar 100 episódios
sem pedir nada a ninguém.

Se o plano apontar `imagem` ou `clip`, a arte procedural é ignorada e a mídia
do usuário (screenshot do jogo, arte de IA, captura de gameplay) é usada.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ---------------------------------------------------------------- paletas
# (ceu topo, horizonte, luz, sombra, bruma)
PALETAS = {
    "abismo": {"ceu": (7, 9, 13), "horizonte": (26, 18, 12), "luz": (208, 150, 78),
               "sombra": (4, 5, 8), "bruma": (44, 52, 62)},
    "catacumba": {"ceu": (9, 8, 11), "horizonte": (30, 19, 21), "luz": (186, 112, 72),
                  "sombra": (4, 4, 6), "bruma": (54, 44, 48)},
    "floresta": {"ceu": (6, 10, 12), "horizonte": (18, 28, 27), "luz": (158, 196, 176),
                 "sombra": (3, 6, 7), "bruma": (42, 60, 58)},
    "gelo": {"ceu": (9, 13, 19), "horizonte": (32, 44, 56), "luz": (176, 204, 224),
             "sombra": (5, 8, 12), "bruma": (60, 74, 90)},
    "fogo": {"ceu": (13, 8, 7), "horizonte": (58, 24, 13), "luz": (236, 142, 64),
             "sombra": (7, 4, 4), "bruma": (78, 46, 34)},
    "trono": {"ceu": (8, 8, 13), "horizonte": (26, 21, 27), "luz": (204, 162, 98),
              "sombra": (4, 4, 8), "bruma": (48, 45, 58)},
}

ARQUETIPOS = ["ruina", "caverna", "floresta", "abismo", "trono", "campo"]


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed & 0xFFFFFFFF)


def _jitter(pts, rng, ampl: float):
    return [(x + rng.uniform(-ampl, ampl), y + rng.uniform(-ampl, ampl)) for x, y in pts]


# ---------------------------------------------------------------- céu
def _ceu(W: int, H: int, pal: dict, rng) -> np.ndarray:
    y = np.linspace(0, 1, H)[:, None] ** 1.9
    topo = np.array(pal["ceu"], dtype=np.float32)
    horiz = np.array(pal["horizonte"], dtype=np.float32)
    col = topo[None, :] * (1 - y) + horiz[None, :] * y
    img = np.repeat(col[:, None, :], W, axis=1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for _ in range(3):
        cx, cy = rng.uniform(0, W), rng.uniform(-H * 0.1, H * 0.55)
        r = rng.uniform(W * 0.22, W * 0.6)
        d = ((xx - cx) ** 2 + ((yy - cy) * 2.2) ** 2) / (r * r)
        img += np.exp(-d)[..., None] * np.array(pal["bruma"], dtype=np.float32) * 0.30
    return np.clip(img, 0, 255)


def _estrelas(img: np.ndarray, rng, qtd: int = 220) -> np.ndarray:
    H, W = img.shape[:2]
    camada = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(camada)
    for _ in range(qtd):
        x, y = rng.uniform(0, W), rng.uniform(0, H * 0.45) ** 1.0
        y = y if rng.random() < 0.85 else rng.uniform(0, H * 0.7)
        r = rng.uniform(0.4, 1.8)
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(rng.uniform(30, 150)))
    camada = camada.filter(ImageFilter.GaussianBlur(0.8))
    a = np.asarray(camada).astype(np.float32)[..., None] / 255.0
    return img * (1 - a * 0.75) + a * 0.75 * np.array([176, 190, 210], dtype=np.float32)


def _astro(img: np.ndarray, pal: dict, rng) -> np.ndarray:
    """Lua/sol velado com halo e borda difusa."""
    H, W = img.shape[:2]
    cx, cy = W * rng.uniform(0.58, 0.84), H * rng.uniform(0.10, 0.26)
    r = min(W, H) * rng.uniform(0.030, 0.055)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    disco = np.clip((r - d) / 3.0 + 0.5, 0, 1) * rng.uniform(0.75, 1.0)
    halo = np.exp(-((d / (r * 5.0)) ** 2)) * 0.5 + np.exp(-((d / (r * 14)) ** 2)) * 0.22
    luz = np.array(pal["luz"], dtype=np.float32)
    b = np.clip(disco + halo, 0, 1.5)[..., None]
    return img * (1 - np.clip(b, 0, 1) * 0.10) + b * luz * 0.80


def _raios(img: np.ndarray, pal: dict, rng, cx: float | None = None) -> np.ndarray:
    H, W = img.shape[:2]
    camada = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(camada)
    ox = W * (cx if cx is not None else rng.uniform(0.55, 0.9))
    for _ in range(int(rng.integers(4, 9))):
        larg = rng.uniform(W * 0.006, W * 0.045)
        incl = rng.uniform(-0.75, 0.75)
        base = ox + rng.uniform(-W * 0.2, W * 0.2)
        pts = [(base, -H * 0.05), (base + larg, -H * 0.05),
               (base + larg + incl * H * 1.4, H * 1.1), (base + incl * H * 1.4, H * 1.1)]
        d.polygon(pts, fill=int(rng.uniform(14, 46)))
    camada = camada.filter(ImageFilter.GaussianBlur(W * 0.018))
    a = np.asarray(camada).astype(np.float32)[..., None] / 255.0
    return img + a * np.array(pal["luz"], dtype=np.float32) * 0.60


def _bruma(img: np.ndarray, pal: dict, rng, y_base: float, altura: float,
           forca: float = 0.55) -> np.ndarray:
    H, W = img.shape[:2]
    peq = rng.standard_normal((max(6, H // 14), max(8, W // 14))).astype(np.float32)
    cam = Image.fromarray((np.clip(peq, -1, 1) * 127 + 127).astype(np.uint8))
    cam = cam.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(W * 0.026))
    a = np.asarray(cam).astype(np.float32) / 255.0
    y = np.linspace(0, 1, H)[:, None]
    faixa = np.exp(-(((y - y_base) / altura) ** 2))
    alpha = (a * faixa * forca)[..., None]
    return img * (1 - alpha) + np.array(pal["bruma"], dtype=np.float32) * alpha * 1.25


def _brasas(img: np.ndarray, pal: dict, rng, qtd: int, origem: tuple[float, float],
            raio: float = 0.35) -> np.ndarray:
    H, W = img.shape[:2]
    camada = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(camada)
    ox, oy = W * origem[0], H * origem[1]
    for _ in range(qtd):
        ang = rng.uniform(-math.pi, math.pi)
        dist = abs(rng.normal(0, raio)) * W
        x = ox + math.cos(ang) * dist * 0.6
        y = oy + math.sin(ang) * dist * 0.9
        if not (0 <= x < W and 0 <= y < H):
            continue
        r = rng.uniform(0.5, 2.6)
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(rng.uniform(60, 235)))
    camada = camada.filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(camada).astype(np.float32)[..., None] / 255.0
    return img + a * np.array(pal["luz"], dtype=np.float32) * 1.15


# ---------------------------------------------------------------- arquitetura
def _torre(d, x: float, base_y: float, larg: float, alt: float, rng, ponta=True):
    topo = base_y - alt
    pts = [(x, base_y), (x, topo), (x + larg, topo), (x + larg, base_y)]
    d.polygon(_jitter(pts, rng, larg * 0.012), fill=255)
    if ponta and rng.random() < 0.8:
        h = alt * rng.uniform(0.18, 0.45)
        d.polygon(_jitter([(x - larg * 0.12, topo), (x + larg * 1.12, topo),
                           (x + larg * rng.uniform(0.45, 0.55), topo - h)], rng, larg * 0.02),
                  fill=255)
    elif rng.random() < 0.6:  # ameias
        passo = larg / 5
        for k in range(5):
            if rng.random() < 0.75:
                d.rectangle([x + k * passo, topo - alt * 0.06,
                             x + k * passo + passo * 0.55, topo], fill=255)
    # janelas
    for _ in range(int(rng.integers(1, 5))):
        if alt < alt * 0.3:
            continue
        wx = x + larg * rng.uniform(0.25, 0.75)
        wy = topo + alt * rng.uniform(0.15, 0.72)
        ww = max(1.6, larg * rng.uniform(0.05, 0.12))
        wh = ww * rng.uniform(1.4, 2.8)
        d.rectangle([wx, wy, wx + ww, wy + wh], fill=int(rng.uniform(80, 190)))


def _arco(d, cx: float, base_y: float, larg: float, alt: float, rng):
    """Arco gótico (ogiva) vazado."""
    passos = 14
    esq, dirr = [], []
    for i in range(passos + 1):
        f = i / passos
        ang = math.pi * f
        x = cx - larg / 2 * math.cos(ang) * 0.98
        # ogiva: topo mais alto e estreito
        y = base_y - alt * (math.sin(ang) ** 0.72)
        esq.append((x, y))
    d.polygon(esq + [(cx + larg / 2, base_y), (cx - larg / 2, base_y)], fill=255)


def _rochedo(X, Y, rng, irregular=0.03):
    """Linha de crista irregular para montanhas/rochas."""
    pts = []
    n = len(X)
    for i in range(n):
        fr = math.sin(i * 0.7) * 0.4 + math.sin(i * 0.19 + 1.3) * 0.6
        pts.append((X[i], Y[i] * (1 + fr * irregular) ))
    return pts


def _arvore(d, x: float, base_y: float, alt: float, larg: float, rng):
    topo = base_y - alt
    # tronco afunilado
    d.polygon(_jitter([(x - larg, base_y), (x + larg, base_y),
                       (x + larg * 0.35, topo), (x - larg * 0.25, topo)], rng, larg * 0.15),
              fill=255)
    # galhos
    for _ in range(int(rng.integers(4, 10))):
        f = rng.uniform(0.15, 0.95)
        gy = base_y - alt * f
        dirx = rng.choice([-1, 1])
        comp = larg * rng.uniform(1.5, 5.0) * (1 - f * 0.5)
        gy2 = gy - comp * rng.uniform(0.3, 0.8)
        d.line([(x, gy), (x + dirx * comp, gy2)], fill=255,
               width=max(1, int(larg * (1.0 - f) * 1.6)))
    # copa: aglomerado de blobs
    for _ in range(int(rng.integers(5, 12))):
        bx = x + rng.uniform(-larg * 3.5, larg * 3.5)
        by = topo + rng.uniform(-alt * 0.10, alt * 0.30)
        br = larg * rng.uniform(1.2, 3.4)
        d.ellipse([bx - br, by - br * 0.8, bx + br, by + br * 0.8], fill=255)


def _chao_perspectiva(d, W, H, base_y, pal, rng, arquetipo):
    """Laje/piso em perspectiva, dá profundidade real à cena."""
    vpx, vpy = W * 0.5, base_y - H * 0.02
    # linhas convergindo ao ponto de fuga
    for i in range(-14, 15):
        x0 = W * 0.5 + i * W * 0.16
        d.line([(x0, H * 1.05), (vpx + (x0 - vpx) * 0.12, vpy)], fill=255, width=2)
    # travessas horizontais com espaçamento crescente
    for i in range(1, 12):
        f = (i / 12) ** 2.2
        y = vpy + (H * 1.02 - vpy) * f
        d.line([(0, y), (W, y)], fill=255, width=max(1, int(1 + f * 4)))


def _silhueta_cena(W, H, arquetipo, rng, horizonte, densidade, com_chao=False):
    camada = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(camada)
    base_y = H * horizonte
    som = 255

    if arquetipo in ("ruina", "trono", "campo"):
        if com_chao:
            _chao_perspectiva(d, W, H, base_y, None, rng, arquetipo)
        # muralha corrida
        parede = rng.uniform(H * 0.04, H * 0.10) * densidade
        d.rectangle([-10, base_y - parede, W + 10, H], fill=som)
        x = -W * 0.05
        while x < W * 1.05:
            larg = rng.uniform(W * 0.02, W * 0.07) * densidade
            alt = rng.uniform(H * 0.10, H * 0.34) * densidade
            if rng.random() < 0.30:
                alt *= rng.uniform(1.5, 2.8)
            _torre(d, x, base_y - parede * 0.5, larg, alt, rng)
            # vãos de arco entre torres
            if rng.random() < 0.45 and larg > W * 0.03:
                _arco(d, x + larg * 1.4, base_y - parede * 0.5,
                      larg * rng.uniform(0.6, 1.1), alt * rng.uniform(0.3, 0.6), rng)
            x += larg * rng.uniform(1.3, 2.6) + rng.uniform(0, W * 0.02)
    elif arquetipo == "caverna":
        # paredes laterais com ondulação
        for lado in (-1, 1):
            pts = []
            for i in range(24):
                f = i / 23
                x = (W * 0.16 * (1 - f) if lado < 0 else W - W * 0.16 * (1 - f))
                x += math.sin(f * 9 + lado) * W * 0.012
                pts.append((x, H * f))
            pts = ([(-10, 0)] + pts + [(-10, H)]) if lado < 0 else ([(W + 10, 0)] + pts + [(W + 10, H)])
            d.polygon(pts, fill=som)
        # ...
        # estalactites orgânicas (topo) e estalagmites (base)
        for lado in ("topo", "base"):
            x = -W * 0.05
            while x < W * 1.05:
                larg = rng.uniform(W * 0.02, W * 0.08)
                alt = rng.uniform(H * 0.10, H * 0.40) * densidade
                curva = rng.uniform(-0.25, 0.25)
                if lado == "topo":
                    pts = [(x, -10), (x + larg, -10),
                           (x + larg * (0.5 + curva), alt * 0.75),
                           (x + larg * (0.5 - curva * 0.5), alt)]
                    d.polygon(_jitter(pts, rng, larg * 0.05), fill=som)
                else:
                    y0 = H + 10
                    pts = [(x, y0), (x + larg, y0),
                           (x + larg * (0.5 - curva), y0 - alt * 0.42),
                           (x + larg * (0.5 + curva * 0.4), y0 - alt * 0.30)]
                    d.polygon(_jitter(pts, rng, larg * 0.05), fill=som)
                x += larg * rng.uniform(0.55, 1.15)
    elif arquetipo == "floresta":
        if com_chao:
            _chao_perspectiva(d, W, H, base_y, None, rng, arquetipo)
        d.rectangle([-10, base_y, W + 10, H], fill=som)
        x = -W * 0.03
        while x < W * 1.03:
            alt = rng.uniform(H * 0.40, H * 0.95) * densidade
            larg = rng.uniform(W * 0.004, W * 0.016) * densidade
            _arvore(d, x, base_y + H * 0.02, alt, larg, rng)
            x += rng.uniform(W * 0.03, W * 0.11)
    elif arquetipo == "abismo":
        # cânion: duas paredes que convergem para o fundo, saliência no primeiro plano
        for lado in (-1, 1):
            pts = []
            N = 90
            for i in range(N):
                f = i / (N - 1)
                # da borda superior externa em direção ao centro/fundo
                x = (W * 0.40) * (1 - f) * (1 if lado < 0 else -1) + (W * 0.5 if lado < 0 else W * 0.5)
                x = (f * W * 0.06) if lado < 0 else (W - f * W * 0.06)
                y = f * H * 0.92
                # serrilhado de rocha: várias oitavas de ruído senoidal
                serra = (math.sin(f * 41 + lado * 2) * 0.45 +
                         math.sin(f * 97 + lado) * 0.30 +
                         math.sin(f * 173) * 0.18)
                x += serra * W * 0.045 * (1 - f * 0.35)
                pts.append((x, y))
            # estratos: linhas horizontais claras na rocha
            for i in range(2, N - 2, 7):
                (x1, y1), (x2, y2) = pts[i], pts[min(i + 4, N - 1)]
                d.line([(x1, y1), (x2, y2)], fill=int(rng.uniform(40, 110)),
                       width=max(2, int(H * 0.004)))
            if lado < 0:
                pts = [(-10, -10)] + pts + [(-10, H + 10)]
            else:
                pts = [(W + 10, -10)] + pts + [(W + 10, H + 10)]
            d.polygon(pts, fill=som)
        # saliência onde o personagem pisa
        ledge = [(x, H * (0.90 + 0.05 * math.sin(x * 0.004)))
                 for x in np.linspace(-10, W + 10, 60)]
        d.polygon(ledge + [(W + 10, H + 10), (-10, H + 10)], fill=som)
    elif arquetipo == "trono":
        # colunata + trono central
        n = 7
        for i in range(n):
            cx = W * (0.06 + i * (0.88 / (n - 1)))
            if abs(cx - W / 2) < W * 0.06:
                continue
            cw = W * 0.028 * densidade
            _torre(d, cx, base_y + H * 0.08, cw, H * rng.uniform(0.42, 0.62), rng, ponta=False)
            d.rectangle([cx - cw * 0.5, base_y - H * 0.42, cx + cw * 1.5, base_y - H * 0.38], fill=som)
        cw, ch = W * 0.15, H * 0.34
        cx, cy = W / 2 - cw / 2, base_y - ch * 0.05
        d.polygon(_jitter([(cx - cw * 0.32, cy + ch), (cx + cw * 1.32, cy + ch),
                           (cx + cw * 1.05, cy - ch * 0.05),
                           (cx + cw * 0.5, cy - ch * 0.95),
                           (cx - cw * 0.05, cy - ch * 0.05)], rng, cw * 0.02), fill=som)
        d.rectangle([cx - cw * 0.15, base_y - ch * 0.12, cx + cw * 1.15, base_y + ch * 0.30], fill=som)
        if com_chao:
            _chao_perspectiva(d, W, H, base_y, None, rng, arquetipo)
    return camada


def _figura(camada: Image.Image, x_frac: float, altura_frac: float, rng,
            base_frac: float = 0.995) -> None:
    """Silhueta de um viajante de costas, olhando o cenário."""
    W, H = camada.size
    d = ImageDraw.Draw(camada)
    h = H * altura_frac
    cx = W * x_frac
    base = H * base_frac
    cabeca = h * 0.075
    # pernas
    d.line([(cx, base), (cx - h * 0.05, base - h * 0.46)], fill=255, width=max(2, int(h * 0.040)))
    d.line([(cx, base), (cx + h * 0.055, base - h * 0.46)], fill=255, width=max(2, int(h * 0.040)))
    # torso
    d.polygon([(cx - h * 0.085, base - h * 0.44), (cx + h * 0.09, base - h * 0.44),
               (cx + h * 0.06, base - h * 0.82), (cx - h * 0.055, base - h * 0.82)], fill=255)
    # capa
    d.polygon(_jitter([(cx - h * 0.06, base - h * 0.80), (cx + h * 0.065, base - h * 0.80),
                       (cx + h * 0.155, base - h * 0.22), (cx - h * 0.145, base - h * 0.28)],
                      rng, h * 0.006), fill=255)
    # capuz: ponta + ombros, conectado ao torso
    topo_cabeca = base - h * 0.98
    d.polygon([(cx - cabeca * 1.25, base - h * 0.76),
               (cx - cabeca * 0.65, topo_cabeca),
               (cx + cabeca * 0.55, topo_cabeca - h * 0.01),
               (cx + cabeca * 1.3, base - h * 0.76)], fill=255)
    d.ellipse([cx - cabeca * 1.05, topo_cabeca - cabeca * 0.35,
               cx + cabeca * 1.05, topo_cabeca + cabeca * 1.6], fill=255)
    # cajado
    d.line([(cx + h * 0.135, base - h * 0.02), (cx + h * 0.20, base - h * 0.98)],
           fill=255, width=max(2, int(h * 0.012)))


def _textura(camada: Image.Image, rng, forca: float = 0.35) -> Image.Image:
    """Ruído multiplicado nas bordas — tira o aspecto de vetor chapado."""
    a = np.asarray(camada).astype(np.float32)
    H, W = a.shape
    peq = rng.standard_normal((max(16, H // 3), max(16, W // 3))).astype(np.float32)
    img = Image.fromarray((np.clip(peq * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8))
    img = img.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(W * 0.0015))
    n = np.asarray(img).astype(np.float32) / 255.0
    mod = 1.0 - forca * (1.0 - n)
    return Image.fromarray(np.clip(a * mod, 0, 255).astype(np.uint8))


def _aplicar(img: np.ndarray, camada: Image.Image, cor, blur=1.0, opacidade=1.0,
             luz_borda=None) -> np.ndarray:
    a = camada.filter(ImageFilter.GaussianBlur(blur))
    am = np.asarray(a).astype(np.float32)[..., None] / 255.0 * opacidade
    out = img * (1 - am) + np.array(cor, dtype=np.float32) * am
    if luz_borda is not None:
        b = camada.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(3.2))
        bm = np.asarray(b).astype(np.float32)[..., None] / 255.0
        out = out + bm * np.array(luz_borda, dtype=np.float32) * 0.14
    return out


# ---------------------------------------------------------------- público
def compor(arquetipo: str, seed: int, *, largura: int = 1920, altura: int = 1080,
           paleta: str | None = None, figura: bool = False,
           escurecer: float = 0.0, escala_figura: float | None = None,
           figura_x: float | None = None, desfoque_profundo: float = 1.0) -> np.ndarray:
    """Monta uma cena completa e devolve o array RGB (não grava arquivo)."""
    rng = _rng(seed)
    pal = PALETAS[paleta if paleta in PALETAS else rng.choice(list(PALETAS))]
    arq = arquetipo if arquetipo in ARQUETIPOS else rng.choice(ARQUETIPOS)

    img = _ceu(largura, altura, pal, rng)
    img = _estrelas(img, rng, qtd=int(rng.integers(80, 240)))
    astro_x = None
    if rng.random() < 0.85:
        img = _astro(img, pal, rng)
        astro_x = rng.uniform(0.55, 0.85)
    if rng.random() < 0.7:
        img = _raios(img, pal, rng, cx=astro_x)

    # --- camada distante (perspectiva atmosférica: clara e borrada)
    dist = _silhueta_cena(largura, altura, arq, rng, rng.uniform(0.55, 0.65), 0.62, com_chao=False)
    cor_dist = tuple(int(c * 0.42 + b * 0.28) for c, b in zip(pal["sombra"], pal["bruma"]))
    img = _aplicar(img, _textura(dist, rng, 0.10), cor_dist, blur=largura * 0.005, opacidade=0.85)

    # --- névoa intermediária
    img = _bruma(img, pal, rng, rng.uniform(0.52, 0.68), rng.uniform(0.14, 0.26), 0.42)

    # --- camada média
    media = _silhueta_cena(largura, altura, arq, rng, rng.uniform(0.70, 0.80), 0.85, com_chao=arq != "abismo")
    img = _aplicar(img, _textura(media, rng, 0.14), tuple(int(c * 0.55) for c in pal["sombra"]),
                   blur=2.2 * desfoque_profundo, opacidade=0.92)

    # --- clarão subindo da fenda (só no arquétipo abismo)
    if arq == "abismo":
        yy, xx = np.mgrid[0:altura, 0:largura].astype(np.float32)
        cx, cy = largura * 0.5, altura * 1.02
        d = np.sqrt(((xx - cx) / (largura * 0.16)) ** 2 + ((yy - cy) / (altura * 0.70)) ** 2)
        glow = np.exp(-(d ** 2) * 1.1)[..., None]
        img = img + glow * np.array(pal["luz"], dtype=np.float32) * 1.35
        img = img + np.exp(-(d * 3.0) ** 2)[..., None] * np.array([255, 240, 210], dtype=np.float32) * 0.45

    # --- primeiro plano: escuro, nítido, com luz de borda
    prox = _silhueta_cena(largura, altura, arq, rng, rng.uniform(0.86, 0.96), 1.25, com_chao=False)
    if figura:
        # enquadramento: "plano médio" (personagem grande) dá a sensação de
        # alguém falando com a câmera; "plano aberto" mostra o cenário.
        escala = escala_figura if escala_figura is not None else rng.uniform(0.19, 0.30)
        x_fig = figura_x if figura_x is not None else rng.uniform(0.36, 0.64)
        _figura(prox, x_fig, escala, rng,
                base_frac=0.90 if arq == 'abismo' else 0.995)
    img = _aplicar(img, _textura(prox, rng, 0.18), pal["sombra"], blur=1.0, luz_borda=pal["luz"])

    # --- bruma de chão + brasas
    img = _bruma(img, pal, rng, 1.02, 0.26, 0.50)
    origem = (astro_x or 0.6, 0.75)
    img = _brasas(img, pal, rng, int(rng.integers(15, 70)), origem, 0.30)

    # --- pós: bloom, vinheta, grão
    arr = np.clip(img, 0, 255)
    pil = Image.fromarray(arr.astype(np.uint8))
    bloom = pil.filter(ImageFilter.GaussianBlur(largura * 0.022))
    arr = np.asarray(pil).astype(np.float32) * 0.85 + np.asarray(bloom).astype(np.float32) * 0.19
    yy, xx = np.mgrid[0:altura, 0:largura].astype(np.float32)
    d = np.sqrt(((xx - largura / 2) / (largura / 2)) ** 2 + ((yy - altura / 2) / (altura / 2)) ** 2)
    arr *= np.clip(1.05 - 0.30 * d ** 2, 0.42, 1.05)[..., None]
    # curva de "lift": sobe as sombras sem lavar o preto (dark, mas legível)
    arr = 255.0 * np.power(np.clip(arr / 255.0, 0, 1), 0.86) * 1.02 + 6.0
    luminancia = arr.mean(axis=2, keepdims=True)
    escala_grao = 0.35 + 0.65 * np.clip(luminancia / 90.0, 0, 1)
    arr += rng.normal(0, 2.4, arr.shape) * escala_grao
    # grade final: sombras frias, altas luzes quentes
    arr[..., 2] *= 1.04
    arr[..., 0] *= 1.02
    arr = np.clip(arr, 0, 255)

    if escurecer > 0:
        arr = arr * (1.0 - escurecer)
    return np.clip(arr, 0, 255).astype(np.uint8)


def gerar(arquetipo: str, seed: int, saida: Path, *, largura: int = 1920,
          altura: int = 1080, paleta: str | None = None, figura: bool = False) -> Path:
    """Cria um cenário dark e salva em JPG."""
    arr = compor(arquetipo, seed, largura=largura, altura=altura,
                 paleta=paleta, figura=figura)
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(saida, quality=94)
    return saida


# ---------------------------------------------------------------- cartões
F_TITULO = Path(__file__).resolve().parent.parent / "assets/brand/fonts/Cinzel.ttf"
F_LEGENDA = Path(__file__).resolve().parent.parent / "assets/brand/fonts/BebasNeue.ttf"


def _fonte(caminho: Path, tamanho: int):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(str(caminho), tamanho)
    except Exception:
        return ImageFont.load_default(size=tamanho)


def _fundo_card(W: int, H: int, seed: int, paleta: str | None = None,
                arquetipo: str = "ruina") -> np.ndarray:
    """Cenário real, porém muito escurecido, para o texto respirar por cima."""
    arr = compor(arquetipo, seed + 91, largura=W, altura=H, paleta=paleta,
                 figura=False, escurecer=0.62)
    # vinheta extra para fechar as bordas
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    arr = arr.astype(np.float32) * np.clip(1.0 - 0.35 * d ** 2, 0.25, 1.0)[..., None]
    return np.clip(arr, 0, 255)


def _texto_centro(pil: Image.Image, linhas: list[tuple[str, int, tuple, int]], espaco: int = 26) -> Image.Image:
    """Desenha linhas centralizadas com leve halo (sem depender de blur pesado)."""
    camada = Image.new("RGBA", pil.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    medidas = []
    for texto, tam, cor, alpha in linhas:
        f = _fonte(F_TITULO if tam > 60 else F_LEGENDA, tam)
        bb = d.textbbox((0, 0), texto, font=f)
        medidas.append((bb, f, texto, tam, cor, alpha))
    alturas = [m[0][3] - m[0][1] for m in medidas]
    total = sum(alturas) + espaco * (len(linhas) - 1)
    W, H = pil.size
    y = (H - total) / 2
    for (bb, f, texto, tam, cor, alpha), alt in zip(medidas, alturas):
        w = bb[2] - bb[0]
        x = (W - w) / 2
        # halo/contorno suave
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2)):
            d.text((x + dx, y - bb[1] + dy), texto, font=f, fill=(0, 0, 0, min(160, alpha)))
        d.text((x, y - bb[1]), texto, font=f, fill=cor + (alpha,))
        y += alt + espaco
    camada = camada.filter(ImageFilter.GaussianBlur(0.4))
    return Image.alpha_composite(pil.convert("RGBA"), camada).convert("RGB")


def cartao_titulo(titulo: str, subtitulo: str, saida: Path, semente: int = 1,
                  largura: int = 1920, altura: int = 1080, paleta: str | None = None,
                  arquetipo: str = "ruina") -> Path:
    fundo = _fundo_card(largura, altura, semente, paleta, arquetipo)
    pil = Image.fromarray(fundo.astype("uint8"))
    escala = largura / 1920
    linhas = []
    if subtitulo:
        linhas.append((subtitulo.upper(), int(38 * escala), (206, 172, 122), 220))
    linhas.append((titulo.upper(), int(104 * escala), (240, 235, 226), 255))
    pil = _texto_centro(pil, linhas, espaco=int(30 * escala))
    # linha decorativa sob o subtítulo
    d = ImageDraw.Draw(pil)
    y = altura * 0.30
    d.line([(largura / 2 - 90 * escala, y), (largura / 2 + 90 * escala, y)],
           fill=(132, 100, 62), width=max(1, int(2 * escala)))
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    pil.save(saida, quality=95)
    return saida


def cartao_cta(texto_principal: str, texto_secundario: str, saida: Path,
               semente: int = 5, largura: int = 1920, altura: int = 1080,
               paleta: str | None = None, arquetipo: str = "trono") -> Path:
    fundo = _fundo_card(largura, altura, semente, paleta, arquetipo)
    pil = Image.fromarray(fundo.astype("uint8"))
    escala = largura / 1920
    linhas = [(texto_principal.upper(), int(86 * escala), (242, 236, 226), 255)]
    if texto_secundario:
        linhas.append((texto_secundario.upper(), int(44 * escala), (208, 160, 98), 235))
    pil = _texto_centro(pil, linhas, espaco=int(28 * escala))
    d = ImageDraw.Draw(pil)
    y = altura / 2 - 92 * escala
    d.line([(largura / 2 - 110 * escala, y), (largura / 2 + 110 * escala, y)],
           fill=(132, 100, 62), width=max(1, int(2 * escala)))
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    pil.save(saida, quality=95)
    return saida


def thumbnail(base_img: Path, titulo: str, saida: Path, linha2: str = "",
              largura: int = 1280, altura: int = 720) -> Path:
    """Thumbnail 16:9: base escurecida à esquerda + título em Cinzel com contorno."""
    img = Image.open(base_img).convert("RGB")
    alvo = largura / altura
    w, h = img.size
    if w / h > alvo:
        nw = int(h * alvo)
        img = img.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
    else:
        nh = int(w / alvo)
        img = img.crop((0, max(0, (h - nh) // 2), w, max(0, (h - nh) // 2) + nh))
    img = img.resize((largura, altura), Image.LANCZOS)

    arr = np.asarray(img).astype(np.float32)
    grad = np.linspace(0.28, 1.0, largura)[None, :, None]
    arr = np.clip(arr * (0.42 + 0.72 * grad) * 1.05 - 4, 0, 255)
    img = Image.fromarray(arr.astype(np.uint8))

    d = ImageDraw.Draw(img)
    escala = largura / 1280
    f_titulo = _fonte(F_TITULO, int(96 * escala))
    f_sub = _fonte(F_LEGENDA, int(50 * escala))
    y = altura * 0.20
    for linha, fnt, cor in ((titulo, f_titulo, (245, 240, 232)), (linha2, f_sub, (216, 168, 104))):
        if not linha:
            continue
        bb = d.textbbox((0, 0), linha.upper(), font=fnt)
        x = 64 * escala
        for dx in (-4, 4):
            for dy in (-4, 4):
                d.text((x + dx, y + dy - bb[1]), linha.upper(), font=fnt, fill=(0, 0, 0))
        d.text((x, y - bb[1]), linha.upper(), font=fnt, fill=cor)
        y += (bb[3] - bb[1]) + 30 * escala
    # faixa de acento
    d.rectangle([64 * escala, y + 6 * escala, 64 * escala + 120 * escala, y + 12 * escala],
                fill=(168, 120, 66))
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    img.save(saida, quality=92)
    return saida
