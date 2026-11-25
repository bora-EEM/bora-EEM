"""Film sahnelerinin durgun resimleri (saydam WebP), foto/ klasörüne. Hiçbiri filmden alınmış görüntü değildir:
gargantua.webp : ışığın kara delik çevresinde bükülmesi hesaplanarak (Schwarzschild jeodeziği) çizilir; disk ölçüleri ve
                 bakış açısı filmin kara deliği için yayımlanan değerler (dış 18,70 M, eğim 86,6 derece; iç kenar 6,4 M).
gemi-golge, gemi-isik-1..4 : kareden taşan uzaylı gemisi, gölgede; gövdede gezinen ışığın lekeleri.
tunel-ag, -deri, -damar, kapi-ust, -alt : kendi kendine büyüyen tünelin katmanları ve ucundaki kapı.
hail-mary.webp : iki yan itici, ortada modüler gövde, dikey uzun güneş paneli.
endurance.webp : on iki bölmeli halka gemi, önden.
Kullanım: python film_resimleri.py [gargantua] [golge_gemi] [tunel] [kapi] [hail] [los_hail] [endurance]"""
import math, random, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

FOTO = Path(__file__).resolve().parent / "foto"


def kaydet(rgba: np.ndarray, ad: str, boyut: tuple, kalite: int = 70, kademe: int = 20) -> None:
    """Küçültüp WebP yazar. Boyutun çoğunu renk değil saydamlık kanalı tutar; saydamlık az kademeye indirilince dosya
    üçte birine iner, gözle aynı kalır (yumuşak ışıklarda kademe 32)."""
    im = Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    # küçültürken saydam kenar kararmasın diye önce alfa ile çarpılır
    im = im.convert("RGBa").resize(boyut, Image.LANCZOS).convert("RGBA")
    d = np.asarray(im).astype(float)
    d[..., 3] = np.round(d[..., 3] / 255 * kademe) / kademe * 255
    Image.fromarray(d.astype(np.uint8), "RGBA").save(FOTO / ad, "WEBP", quality=kalite, alpha_quality=100, method=6)
    print(ad, boyut, f"{(FOTO / ad).stat().st_size / 1024:.1f} KB")


# ---------------------------------------------------------------- Gargantua
def gargantua() -> None:
    G, Y = 1500, 900                # çizim boyu (sahnede 500 x 300 birim, 3 kat)
    ALAN = 31.0                     # yatayda yarı genişlik, M cinsinden
    R0, EGIM = 74.1, np.radians(86.56)
    IC, DIS = 6.4, 18.70
    xs = (np.arange(G) + 0.5 - G / 2) / (G / 2) * ALAN
    ys = -(np.arange(Y) + 0.5 - Y / 2) / (G / 2) * ALAN
    X, YY = np.meshgrid(xs, ys)
    # kamera (R0, eğim) konumunda, delik merkezine bakar; disk z=0 düzleminde
    n = np.array([np.sin(EGIM), 0, np.cos(EGIM)])
    sag, yuk = np.array([0., 1, 0]), np.array([-np.cos(EGIM), 0, np.sin(EGIM)])
    yon = -n[None, None, :] + (X / R0)[..., None] * sag + (YY / R0)[..., None] * yuk
    yon /= np.linalg.norm(yon, axis=-1, keepdims=True)
    p = np.broadcast_to(n * R0, yon.shape).reshape(-1, 3).copy()
    v = yon.reshape(-1, 3).copy()
    h2 = (np.cross(p, v) ** 2).sum(-1)
    renk = np.zeros((len(p), 3)); kalan = np.ones(len(p)); dustu = np.zeros(len(p), bool)
    canli = np.ones(len(p), bool)
    r = random.Random(5)
    # disk dokusu: yarıçapa göre ince halkalar, açıya göre sarmal tutamlar
    rr = np.linspace(IC, DIS, 2048)
    halka = np.interp(rr, np.linspace(IC, DIS, 90), [0.72 + 0.5 * r.random() for _ in range(90)])
    halka = halka * np.interp(rr, np.linspace(IC, DIS, 260), [0.86 + 0.28 * r.random() for _ in range(260)])
    dalga = [(r.uniform(1.5, 7), r.randint(2, 14), r.uniform(0, 6.28), r.uniform(0.04, 0.1)) for _ in range(16)]

    def disk_isik(x, y):
        q = np.hypot(x, y)
        a = np.arctan2(y, x)
        u = (q - IC) / (DIS - IC)
        doku = np.interp(q, rr, halka)
        kat = 1.0
        for k, m, f0, g in dalga:
            kat = kat + g * np.sin(m * a + k * q * 1.3 + f0)
        # içte kremsi beyaz, dışta altın turuncu
        sic = np.clip(1 - u, 0, 1)
        ic_r = np.stack([1.0 + 0 * sic, 0.60 + 0.34 * sic ** 0.7, 0.30 + 0.52 * sic ** 0.9], -1)
        guc = (0.30 + 1.55 * sic ** 1.5) * np.clip(u / 0.05, 0, 1) * np.clip((1 - u) / 0.28, 0, 1) ** 1.2 * doku * np.clip(kat, 0.35, 1.8)
        opak = np.clip(0.35 + 0.65 * sic, 0, 1) * np.clip(u / 0.04, 0, 1) * np.clip((1 - u) / 0.3, 0, 1)
        return ic_r * guc[:, None], opak

    for adim in range(1400):
        i = np.nonzero(canli)[0]
        if not len(i):
            break
        pi, vi = p[i], v[i]
        q = np.linalg.norm(pi, axis=-1)
        dt = np.clip(0.06 * q, 0.06, 2.0)
        dt = np.where(np.abs(pi[:, 2]) < 2, np.minimum(dt, np.maximum(0.12, 0.05 * q)), dt)[:, None]
        ivme = lambda pp: -3.0 * h2[i, None] * pp / np.linalg.norm(pp, axis=-1, keepdims=True) ** 5   # 1.5 rs, rs=2
        k1v, k1p = ivme(pi), vi
        k2v, k2p = ivme(pi + dt / 2 * k1p), vi + dt / 2 * k1v
        k3v, k3p = ivme(pi + dt / 2 * k2p), vi + dt / 2 * k2v
        k4v, k4p = ivme(pi + dt * k3p), vi + dt * k3v
        yp = pi + dt / 6 * (k1p + 2 * k2p + 2 * k3p + k4p)
        yv = vi + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        kes = pi[:, 2] * yp[:, 2] < 0
        if kes.any():
            j = np.nonzero(kes)[0]
            t = pi[j, 2] / (pi[j, 2] - yp[j, 2])
            kx = pi[j, 0] + t * (yp[j, 0] - pi[j, 0]); ky = pi[j, 1] + t * (yp[j, 1] - pi[j, 1])
            q2 = np.hypot(kx, ky); ok = (q2 > IC) & (q2 < DIS)
            if ok.any():
                jj = i[j[ok]]
                c, o = disk_isik(kx[ok], ky[ok])
                renk[jj] += kalan[jj, None] * c
                kalan[jj] *= 1 - o
        p[i], v[i] = yp, yv
        q = np.linalg.norm(yp, axis=-1)
        d = q < 2.02
        dustu[i[d]] = True
        canli[i[d]] = False
        canli[i[(q > 90)]] = False
        canli[i[kalan[i] < 0.02]] = False
    dustu |= canli          # ışık halkasında dolanıp kalan ışınlar
    renk = renk.reshape(Y, G, 3); golge = dustu.reshape(Y, G)
    # parıltı: dar, orta ve geniş yayılma
    parla = sum(a * np.stack([gaussian_filter(np.minimum(renk[..., k], 2.2), s) for k in range(3)], -1)
                for s, a in ((5, 0.45), (18, 0.42), (70, 0.75)))
    g_yum = gaussian_filter(golge.astype(float), 2.0)
    parla *= (1 - 0.86 * g_yum * np.clip(1 - renk.max(-1), 0, 1))[..., None]   # gölgenin içi siyah kalsın
    halka = np.clip(4 * g_yum * (1 - g_yum), 0, 1) ** 1.5 * np.clip(1 - renk.max(-1), 0, 1)   # ince ışık halkası
    toplam = renk * 0.95 + parla * np.array([1.0, 0.86, 0.68]) + 0.9 * halka[..., None] * np.array([1.0, 0.93, 0.80])
    toplam = 1 - np.exp(-1.25 * toplam)                    # film gibi yumuşak doygunluk
    # kenarda sıfıra insin (kare sınır görünmesin)
    kx = np.clip((1 - np.abs(xs) / ALAN) / 0.22, 0, 1); ky = np.clip((1 - np.abs(ys) / ys.max()) / 0.30, 0, 1)
    sonum = (kx * kx * (3 - 2 * kx))[None, :] * (ky * ky * (3 - 2 * ky))[:, None]
    toplam *= sonum[..., None]
    alfa = toplam.max(-1)
    g_alfa = gaussian_filter(golge.astype(float), 1.2)
    a = np.maximum(alfa, g_alfa)
    rgb = np.where(a[..., None] > 1e-4, toplam / np.maximum(a, 1e-4)[..., None], 0)
    kaydet(np.dstack([rgb, a]), "gargantua.webp", (760, 456), 70, 64)


# ---------------------------------------------------------------- Blip-A
def golge_gemi() -> None:
    """Gölgeye gömülü uzaylı gemisi: sahnede x 500..960, y 0..300 (460 x 300 birim). Sağı, üstü ve altı kareden taşar."""
    S, EN, BOY = 4, 460, 300
    G, Y = EN * S, BOY * S
    r = random.Random(44)
    rgb = np.zeros((Y, G, 3)); alfa = np.zeros((Y, G))
    cy = 150 * S

    def kat(ciz, bulanik=0.0):
        nonlocal rgb, alfa
        im = Image.new("RGBA", (G, Y), (0, 0, 0, 0)); ciz(ImageDraw.Draw(im, "RGBA"))
        if bulanik: im = im.filter(ImageFilter.GaussianBlur(bulanik * S))
        b = np.asarray(im).astype(float) / 255; a = b[..., 3]
        rgb = rgb * (1 - a[..., None]) + b[..., :3] * a[..., None]; alfa = alfa + a * (1 - alfa)

    def renk(g):
        t = [(0, (4, 3, 3)), (0.25, (44, 30, 20)), (0.55, (128, 90, 54)), (0.8, (212, 170, 116)), (1, (255, 240, 212))]
        g = max(0, min(1, g))
        for (a, c), (b, d) in zip(t, t[1:]):
            if g <= b:
                k = (g - a) / (b - a); return tuple(int(c[i] + (d[i] - c[i]) * k) for i in range(3))

    def uc(y):                                  # geminin sol kenarı: eksende sola uzar, yukarı aşağı çekilir
        v = abs(y - 150) / 150
        return 92 + 215 * v ** 1.25 + 92 * math.exp(-(v / 0.17) ** 4)

    def silueti(dr):
        nok = [(uc(y) * S + 26 * S, y * S) for y in range(0, 301, 3)]
        dr.polygon(nok + [(G, Y), (G, 0)], fill=(3, 2, 3, 255))
    kat(silueti, 7); kat(silueti, 1.5)

    def cubuklar(n, d0, d1):
        def ciz(dr):
            for _ in range(n):
                y = r.uniform(-2, 302); v = abs(y - 150) / 150
                if v < 0.10: continue
                d = r.uniform(d0, d1)
                x0 = uc(y) + r.expovariate(1 / 34) - 10
                x1 = min(EN + 5, x0 + r.uniform(50, 420))
                kal = r.choice((0.5, 0.7, 0.9, 1.3)) * (0.6 + 0.7 * d)
                isik = (0.12 + 0.75 * d ** 1.7) * (1 if y < 150 else 0.68) * r.uniform(0.6, 1.1)
                x = x0
                while x < x1:                   # çubuk boyunca boğum boğum değişen ışık
                    L = r.uniform(5, 26); b = isik * r.uniform(0.55, 1.15)
                    dr.rectangle([x * S, (y - kal / 2) * S, min(x1, x + L) * S, (y + kal / 2) * S], fill=renk(b * 0.5) + (255,))
                    dr.line([x * S, (y - kal / 2) * S, min(x1, x + L) * S, (y - kal / 2) * S], fill=renk(b) + (255,), width=max(1, int(kal * 1.3)))
                    x += L
                if r.random() < 0.3:
                    a = r.uniform(x0, x1); w = r.uniform(2, 9)
                    dr.rectangle([a * S, (y - kal) * S, (a + w) * S, (y + kal) * S], fill=renk(isik * 0.75) + (255,))
        return ciz

    def sis(g):
        return lambda dr: dr.rectangle([150 * S, 0, G, Y], fill=(2, 1, 2, g))
    kat(cubuklar(420, 0.0, 0.35)); kat(sis(110), 30); kat(cubuklar(330, 0.2, 0.7)); kat(sis(60), 30)

    def kaburga(dr):                            # kareden taşan dev kaburgalar
        for i, kx in enumerate((252, 290, 334, 384, 432)):
            for yon in (-1, 1):
                es = 1 if yon < 0 else 0.62
                for k in range(260):
                    t = k / 259; y = 150 + yon * (17 + 140 * t)
                    x = kx + 26 * math.sin(t * 1.5) ** 2 * (1 if i % 2 else 0.6) + 3 * math.sin(t * 9 + i)
                    w = (5.6 if i in (1, 2) else 4.4) * (0.8 + 0.5 * t) * r.uniform(0.9, 1.12)
                    dr.rectangle([(x - w - 4) * S, (y - .4) * S, (x + w + 9) * S, (y + .4) * S], fill=(1, 1, 1, 120))
                    for s in range(-7, 8):
                        u = s / 7; g = (0.06 + 0.74 * max(0, 1 - ((u + 0.5) / 0.8) ** 2)) * es * r.uniform(0.55, 1.15)
                        if k % 13 == 0: g *= 0.35
                        dr.rectangle([(x + u * w) * S, (y - .35) * S, (x + u * w + w / 7) * S, (y + .35) * S], fill=renk(g) + (255,))
    kat(kaburga)
    kat(cubuklar(120, 0.5, 1.0))

    def yuva(dr):                               # kapının oturduğu koyu yuva
        dr.polygon([(190 * S, 132 * S), (218 * S, 112 * S), (330 * S, 106 * S), (EN * S, 112 * S), (EN * S, 188 * S), (330 * S, 194 * S), (218 * S, 188 * S), (190 * S, 168 * S)], fill=(4, 3, 3, 250))
    kat(yuva, 2.5)

    def makine(dr):
        for _ in range(330):
            x = 190 + r.expovariate(1 / 95); y = r.gauss(150, 18)
            if not 112 < y < 188 or x > EN: continue
            w, h = r.uniform(3, 18), r.uniform(1, 5); g = r.uniform(0.04, 0.5) * (1 if y < 150 else 0.6)
            dr.rectangle([x * S, y * S, (x + w) * S, (y + h) * S], fill=renk(g * 0.5) + (255,))
            dr.line([x * S, y * S, (x + w) * S, y * S], fill=renk(g) + (255,), width=3)
    kat(makine)

    al = np.clip(alfa, 0, 1)
    duz = np.where(al[..., None] > 1e-3, rgb / np.maximum(al, 1e-3)[..., None], 0)
    yy, xx = np.mgrid[0:Y, 0:G] / S
    # gölge: yalnız kapının çevresinde ve sol kıyıda hafif ışık; sağa, yukarı ve aşağı doğru kara
    yakin = np.exp(-(((xx - 175) / 85) ** 2 + ((yy - 150) / 62) ** 2))
    kiyi = np.exp(-((xx - np.vectorize(uc)(yy[:, :1]) - 40) / 34) ** 2) * np.clip(1 - np.abs(yy - 118) / 130, 0, 1)
    isik = 0.10 + 0.95 * yakin + 0.62 * kiyi
    isik *= np.clip((430 - xx) / 190, 0.0, 1)
    # ısı kızıllığı derine indikçe kızarır
    ton = np.dstack([np.ones_like(isik), 0.92 - 0.12 * (xx / EN), 0.86 - 0.2 * (xx / EN)])
    kaydet(np.dstack([duz * isik[..., None] * ton, al]), "gemi-golge.webp", (828, 540), 70, 32)
    # ışık lekeleri: gövdenin aydınlık hali, kenarları yumuşak
    for i, (mx, my, rx, ry) in enumerate(((205, 72, 64, 40), (292, 40, 62, 46), (330, 122, 66, 44), (285, 232, 66, 46))):
        m = np.exp(-(((xx - mx) / rx) ** 2 + ((yy - my) / ry) ** 2) * 1.4); m = np.clip((m - 0.04) / 0.96, 0, 1)
        x0, x1 = max(0, int(mx - rx * 1.8)), min(EN, int(mx + rx * 1.8)); y0, y1 = max(0, int(my - ry * 1.8)), min(BOY, int(my + ry * 1.8))
        k = (slice(y0 * S, y1 * S), slice(x0 * S, x1 * S))
        soguk = duz * np.array([0.92, 0.95, 1.0]) * 1.25
        kaydet(np.dstack([soguk[k], (al * m)[k]]), f"gemi-isik-{i + 1}.webp", (int((x1 - x0) * 1.4), int((y1 - y0) * 1.4)), 66, 32)


def _gurultu(sekil, olcek, tohum):
    g = np.random.default_rng(tohum).standard_normal(sekil); g = gaussian_filter(g, olcek); return g / g.std()


def tunel() -> None:
    """Kendi kendine büyüyen tünel: 200 x 70 birim. ag: kas teli gibi ağ; deri: pullu kara kabuk; damar: pulların arasındaki kor."""
    S, EN, BOY = 8, 200, 70
    G, Y = EN * S, BOY * S
    yy, xx = np.mgrid[0:Y, 0:G] / S; yy = yy - BOY / 2
    x1 = np.arange(G) / S
    R = 14.5 + 0.9 * np.sin(x1 / 5.2) + 0.5 * np.sin(x1 / 2.1 + 1) + 7.5 * np.exp(-(EN - x1) / 12) + 3.5 * np.exp(-x1 / 9)
    u = yy / R[None, :]; ic = np.abs(u) < 1
    th = np.arcsin(np.clip(u, -0.9999, 0.9999))
    isikv = np.array([-0.35, -0.72, 0.6]); isikv /= np.linalg.norm(isikv)

    def golgele(bump, govde, parlak, kenar):
        gy, gx = np.gradient(bump, 1 / S)
        nz = np.cos(th); ny = np.sin(th)
        n = np.dstack([-gx, ny - gy * nz, nz + gy * ny]); n /= np.linalg.norm(n, axis=2, keepdims=True)
        dif = np.clip((n * isikv).sum(2), 0, 1)
        h = isikv + np.array([0, 0, 1]); h /= np.linalg.norm(h)
        sp = np.clip((n * h).sum(2), 0, 1)
        rim = np.clip(1 - n[..., 2], 0, 1) ** 2.2
        alt = np.clip(n[..., 1], 0, 1)
        c = np.array(govde) * (0.18 + 0.82 * dif[..., None])
        c = c + np.array([0.95, 0.92, 0.88]) * (parlak * (0.75 * sp ** 60 + 0.22 * sp ** 12))[..., None]
        c = c + np.array([1.0, 0.55, 0.2]) * (kenar * rim * (0.3 + 0.9 * alt))[..., None]
        return c
    # deri: pullar (Voronoi hücreleri), tünel boyunca uzamış
    rg = np.random.default_rng(5)
    P = np.column_stack([rg.uniform(-5, EN + 5, 1500), rg.uniform(-2.2, 2.2, 1500) * 15])
    d, ix = cKDTree(P * [0.62, 1]).query(np.column_stack([(xx * 0.62).ravel(), (th * 15).ravel()]), k=2)
    arali = (d[:, 1] - d[:, 0]).reshape(Y, G); tonu = rg.uniform(0.75, 1.3, 1500)[ix[:, 0]].reshape(Y, G)
    bump = 0.75 * np.clip(arali / 1.1, 0, 1) ** 0.6 + 0.25 * _gurultu((Y, G), 5, 3)
    halka = 1.1 * np.exp(-(((xx % 24) - 12) / 2.0) ** 2); bump = bump + halka * 1.2
    c = golgele(gaussian_filter(bump, 1.2), [0.085, 0.066, 0.058], np.full((Y, G), 1.0), np.full((Y, G), 1.0)) * tonu[..., None]
    c *= (0.35 + 0.65 * np.clip(arali / 0.35, 0, 1))[..., None]
    kenara = np.clip((1 - np.abs(u)) * R[None, :] * 2.2, 0, 1)
    ucpay = np.clip(xx / 1.5, 0, 1) * np.clip((EN - xx) / 1.5, 0, 1)
    kaydet(np.dstack([c, kenara * ic * ucpay]), "tunel-deri.webp", (400, 140))
    dam = np.exp(-(arali / 0.30) ** 2) * np.clip(_gurultu((Y, G), 30, 8) * 0.75 + 0.1, 0, 1) * np.cos(th) * ic * ucpay
    dam = np.clip(dam + 0.5 * gaussian_filter(dam, 7), 0, 1)
    kaydet(np.dstack([np.full((Y, G), 1.0), 0.42 + 0.34 * dam, 0.1 + 0.4 * dam, dam]), "tunel-damar.webp", (300, 105))
    # ag: birbirine dolanan kas telleri (arka yarı koyu, ön yarı parlak)
    ck = np.zeros((Y, G, 3)); ak = np.zeros((Y, G))
    for arka in (True, False):
        for i in range(17):
            a, b, w, fz = rg.uniform(-1.9, 1.9), rg.uniform(-0.012, 0.012), rg.uniform(0.7, 2.1), rg.uniform(0, 6)
            tt = a + b * (x1 - 100) + 0.42 * np.sin(x1 / rg.uniform(11, 24) + fz) + 0.16 * np.sin(x1 / rg.uniform(4, 7) + fz)
            kal = w * (0.75 + 0.35 * np.sin(x1 / 6 + fz)) * (1 + 0.7 * np.exp(-(EN - x1) / 14))
            m = R * np.sin(tt) * (0.96 if arka else 1); on = np.cos(tt)
            v = (yy - m[None, :]) / np.maximum(kal, 0.35)[None, :]
            ma = np.clip((1 - np.abs(v)) * kal[None, :] * 3, 0, 1) * (on > -0.05)[None, :] * ucpay
            nz = np.sqrt(np.clip(1 - v * v, 0, 1)); dif = np.clip(-v * 0.72 + nz * 0.6, 0, 1)
            col = np.array([0.075, 0.058, 0.05]) * (0.25 + dif)[..., None] * (0.5 if arka else 1)
            col = col + (np.array([1, .95, .88]) * (0.65 * np.exp(-((v + 0.45) / 0.2) ** 2))[..., None] + np.array([1, .5, .16]) * (0.5 * np.clip(v, 0, 1) ** 3)[..., None]) * (0.35 if arka else 1)
            ck = ck * (1 - ma[..., None]) + col * ma[..., None]; ak = ak + ma * (1 - ak)
    kaydet(np.dstack([np.where(ak[..., None] > 1e-3, ck / np.maximum(ak, 1e-3)[..., None], 0), ak]), "tunel-ag.webp", (400, 140))


def kapi() -> None:
    """Kapı çenesi (üst yarı): 30 x 30 birim, alt kenarı eksen. Yan görünüş: kalın bilezik, içe basamaklı ağız, kilit dişleri."""
    S, EN, BOY = 16, 30, 30
    im = Image.new("RGBA", (EN * S, BOY * S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im, "RGBA")
    n = lambda p: [(x * S, y * S) for x, y in p]
    def serit(poly, koyu, acik):                # silindir gibi dikey geçiş: üstü parlak, eksene doğru koyu değil yumuşak
        mas = Image.new("L", im.size, 0); ImageDraw.Draw(mas).polygon(n(poly), fill=255)
        ys = [p[1] for p in poly]; t = np.clip((np.arange(BOY * S) / S - min(ys)) / (max(ys) - min(ys)), 0, 1)
        g = 0.10 + 0.9 * np.exp(-((t - 0.16) / 0.13) ** 2) + 0.22 * np.exp(-((t - 0.62) / 0.3) ** 2)
        g = np.clip(g, 0, 1)[:, None, None]
        c = np.array(koyu) * (1 - g) + np.array(acik) * g
        arr = np.broadcast_to(c, (BOY * S, EN * S, 3)).astype(np.uint8)
        im.paste(Image.fromarray(arr, "RGB"), (0, 0), mas)
    K, A = (9, 7, 7), (150, 122, 96)
    serit([(17, 13), (29, 14.5), (29, 30), (17, 30)], K, (112, 88, 66))         # tünele giren boyun
    serit([(3, 17), (9, 15), (9, 30), (3, 30)], K, (126, 104, 84))              # gemiye oturan ağız
    serit([(0.6, 20.5), (3.4, 20), (3.4, 30), (0.6, 30)], (6, 5, 5), (196, 164, 126))
    serit([(8, 8), (10, 6), (17, 6), (19, 8), (19, 30), (8, 30)], K, A)         # ana bilezik
    serit([(11, 3.4), (12, 2.4), (15, 2.4), (16, 3.4), (16, 30), (11, 30)], (14, 11, 10), (186, 154, 120))
    maske = np.asarray(im)[..., 3] / 255
    d = ImageDraw.Draw(im, "RGBA")
    for x in (9, 11, 16, 18.6): d.line(n([(x, 4), (x, 30)]), fill=(2, 1, 1, 230), width=5)
    for y in (9.6, 14, 19, 24.6): d.line(n([(8.4, y), (18.6, y)]), fill=(2, 1, 1, 190), width=4)
    for y in (11.8, 16.5, 21.8, 27.2): d.rounded_rectangle([12.4 * S, (y - 1.3) * S, 14.6 * S, (y + 1.3) * S], 8, fill=(3, 2, 2, 255))
    for y in (18.8, 23, 27.2): d.rectangle([4.6 * S, (y - .5) * S, 7.4 * S, (y + .5) * S], fill=(2, 1, 1, 230))
    a = np.asarray(im).astype(float) / 255; a = a.copy(); a[..., 3] *= maske
    gr = 1 + 0.12 * _gurultu(a.shape[:2], 3, 2); a = a.copy(); a[..., :3] *= gr[..., None] * 0.9
    kaydet(a, "kapi-ust.webp", (110, 110), 80)
    b = a[::-1].copy(); b[..., :3] = b[..., :3] * np.array([0.5, 0.44, 0.4])     # alt yarı gölgede, altta kor kenar
    yy = np.arange(b.shape[0])[:, None] / S
    kor = gaussian_filter(b[..., 3], 4); b[..., :3] += (np.clip((yy - 20) / 8, 0, 1) * np.clip(1.15 - kor, 0, 1))[..., None] * np.array([1.0, .5, .16]) * 1.6
    kaydet(b, "kapi-alt.webp", (110, 110), 80)


def los_hail() -> None:
    """Hail Mary'nin loş hali: ışık soldan ve üstten az gelir."""
    a = np.asarray(Image.open(FOTO / "hail-mary.webp").convert("RGBA")).astype(float) / 255
    H, W = a.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
    g = 0.56 - 0.22 * (xx / W); a = a.copy()
    a[..., :3] = (a[..., :3] ** 1.25) * g[..., None] * np.array([0.88, 0.95, 1.08])
    kaydet(a, "hail-mary-los.webp", (402, 322))


# ---------------------------------------------------------------- Hail Mary
def hail() -> None:
    G, Y = 1800, 1440              # sahnede 150 x 120 birim, 12 kat; burun solda, panel direği sağda
    r = random.Random(9)
    im = Image.new("RGBA", (G, Y), (0, 0, 0, 0))

    def silindir(x0, x1, y, yr0, yr1=None, ton=1.0, dikis=True):
        """Yatay silindir (yarıçap soldan sağa yr0 -> yr1): üstten ışık, altta sert gölge, panel dikişleri, kir."""
        yr1 = yr1 if yr1 is not None else yr0
        g, h = int(x1 - x0), int(2 * max(yr0, yr1)) + 4
        u = np.linspace(0, 1, g)[None, :]
        yar = yr0 + (yr1 - yr0) * u
        yy = (np.arange(h) - h / 2)[:, None]
        n = yy / yar
        ic = np.abs(n) <= 1
        nz = np.sqrt(np.clip(1 - n * n, 0, 1))
        isik = np.clip(-n * 0.78 + nz * 0.62, 0, None)          # ışık yukarı önden
        isik = 0.05 + 0.92 * np.clip(isik, 0, 1) ** 1.15 + 0.06 * np.clip(n, 0, 1) ** 3
        isik = np.broadcast_to(isik, (h, g)).copy()
        kir = gaussian_filter(np.random.default_rng(int(x0 + y)).normal(size=(h, g)), (3, 40)) * 2.2
        isik *= 1 + np.clip(kir, -0.10, 0.10)
        if dikis:
            x = r.uniform(30, 70)
            while x < g - 20:
                isik[:, int(x):int(x) + 3] *= 0.62
                x += r.uniform(46, 130)
            for k in (-0.45, 0.2):
                yk = int(h / 2 + k * min(yr0, yr1)); isik[yk:yk + 2, :] *= 0.75
        renk = np.stack([isik * 0.985, isik * 0.975, isik * 0.955], -1) * ton
        kr = np.dstack([renk, ic.astype(float)])
        parca = Image.fromarray((np.clip(kr, 0, 1) * 255).astype(np.uint8), "RGBA")
        im.alpha_composite(parca, (int(x0), int(y - h / 2)))

    dr = lambda: ImageDraw.Draw(im, "RGBA")
    kutu = lambda x0, y0, x1, y1, c: dr().rectangle([x0, y0, x1, y1], fill=c)

    def detay(x0, x1, y, yr, n):
        for _ in range(n):
            x, t = r.uniform(x0, x1), r.uniform(-0.9, 0.9)
            g = r.choice((34, 60, 92, 150, 205)); w, h = r.uniform(5, 22), r.uniform(4, 14)
            s = 0.45 + 0.55 * (1 - (t + 1) / 2)
            c = int(g * s)
            kutu(x, y + t * yr, x + w, y + t * yr + h, (c, c, int(c * .97), 255))

    # güneş paneli direği (arkada): sağda, dikey, iki uzun kanat; yukarı ve aşağı
    px = 1500
    for yon in (-1, 1):
        for dx in (-74, 14):
            y0, y1 = Y / 2 + yon * 40, Y / 2 + yon * 700
            ya, yb = min(y0, y1), max(y0, y1)
            kutu(px + dx, ya, px + dx + 60, yb, (24, 27, 36, 255))
            for k in range(26):                         # göz göz hücre, ışığı değişken
                h = (yb - ya) / 26
                for s in range(3):
                    v = r.uniform(0.55, 1.15) * (1.15 if yon < 0 else 0.6)
                    c = (int(64 * v), int(62 * v), int(60 * v), 255) if r.random() < 0.75 else (int(84 * v), int(74 * v), int(58 * v), 255)
                    kutu(px + dx + 3 + s * 19, ya + k * h + 2, px + dx + 3 + s * 19 + 16, ya + (k + 1) * h - 3, c)
            kutu(px + dx - 4, ya, px + dx, yb, (206, 192, 160, 255) if yon < 0 else (104, 94, 78, 255))
            kutu(px + dx + 60, ya, px + dx + 63, yb, (150, 138, 112, 255) if yon < 0 else (70, 64, 54, 255))
    # panel ortasındaki kafes direk
    for y in range(20, Y - 20, 46):
        c = (172, 168, 158, 255) if y < Y / 2 else (86, 84, 80, 255)
        dr().line([(px - 8, y), (px + 10, y + 46)], fill=c, width=4); dr().line([(px + 10, y), (px - 8, y + 46)], fill=c, width=4)

    def yan(y, olc=1.0):
        """Yan itici: uzun beyaz silindir, altın kuşak, sağda kafesle gövdeye doğru incelen koni."""
        yr = 66 * olc
        silindir(70, 92, y, yr * 0.5, yr * 0.72, 0.55, False)       # kapak
        silindir(90, 240, y, yr, yr)
        kutu(236, y - yr, 252, y + yr, (24, 23, 22, 255))
        silindir(250, 278, y, yr, yr, 1, False)
        kusak = Image.new("RGBA", (30, int(2 * yr)), (190, 138, 52, 105)); im.alpha_composite(kusak, (250, int(y - yr)))
        silindir(276, 800, y, yr, yr)
        kutu(798, y - yr * 1.04, 822, y + yr * 1.04, (30, 29, 28, 255)); detay(790, 826, y, yr, 16)
        silindir(820, 1010, y, yr * 1.06, yr * 1.06)
        kutu(1006, y - yr, 1022, y + yr, (40, 39, 37, 255))
        silindir(1020, 1330, y, yr * 1.0, yr * 0.42, 0.97)
        detay(820, 1010, y, yr, 12)
        # bayrak ve yazı izleri
        kutu(420, y - 24, 470, y + 2, (150, 40, 40, 200)); kutu(420, y - 24, 440, y - 10, (36, 54, 110, 220))
        for k in range(8):
            kutu(540 + k * 18, y - 18, 552 + k * 18, y - 6, (60, 60, 62, 150))

    # arkadaki (üst) itici, orta gövde, öndeki (alt) itici
    yan(Y / 2 - 150, 0.94)
    # orta gövde: solda ince yaşam modülü, sonra kalın silindirler ve kafes
    m = Y / 2 + 6
    silindir(300, 470, m, 30, 30); kutu(468, m - 36, 486, m + 36, (46, 45, 44, 255))
    silindir(484, 560, m, 40, 40, 1.0)
    kusak = Image.new("RGBA", (34, 84), (206, 140, 44, 150)); im.alpha_composite(kusak, (500, int(m - 42)))
    silindir(560, 700, m, 34, 34, 0.9); detay(480, 720, m, 40, 40)
    for x in range(700, 900, 34):
        dr().line([(x, m - 30), (x + 34, m + 30)], fill=(150, 148, 142, 255), width=6)
        dr().line([(x, m + 30), (x + 34, m - 30)], fill=(98, 96, 92, 255), width=6)
    dr().line([(696, m - 31), (910, m - 31)], fill=(196, 194, 188, 255), width=7)
    dr().line([(696, m + 31), (910, m + 31)], fill=(84, 82, 80, 255), width=7)
    detay(690, 900, m, 34, 26)
    silindir(905, 1075, m, 74, 80)
    kutu(1072, m - 84, 1096, m + 84, (26, 25, 24, 255))
    silindir(1094, 1230, m, 78, 70); detay(1060, 1240, m, 76, 36)
    silindir(1230, 1400, m, 58, 58, 0.85); detay(1230, 1400, m, 56, 46)
    # arka motor bloğu
    kutu(1396, m - 150, 1440, m + 150, (30, 29, 28, 255)); detay(1390, 1440, m, 145, 60)
    for k in (-1, 0, 1):
        silindir(1438, 1476, m + k * 84, 26, 36, 0.5, False)
    silindir(1470, 1560, m, 44, 34, 0.75, False); detay(1470, 1560, m, 40, 14)
    kutu(px - 80, m - 26, px + 80, m + 26, (64, 62, 58, 255)); detay(px - 80, px + 70, m - 10, 22, 22)
    for y0 in (Y / 2 - 150, Y / 2 + 168):           # yan iticilerin uçları motor bloğuna bağlanır
        yk = m + (y0 - m) * 0.72
        dr().line([(1250, y0 + (m - y0) * 0.08), (1420, yk)], fill=(58, 56, 54, 255), width=26)
        dr().line([(1250, y0 + (m - y0) * 0.08 - 8), (1420, yk - 8)], fill=(150, 148, 142, 255), width=8)
    # bağlantı kafesleri
    for s in (-1, 1):
        for x in (860, 1180, 1300):
            dr().line([(x, m + s * 40), (x + 30, m + s * 110)], fill=(120, 118, 112, 255), width=9)
    yan(Y / 2 + 168, 1.0)
    # alt itici üste gölge düşürür, robot kol ve antenler
    dr().line([(640, m - 30), (600, m - 70), (520, m - 78)], fill=(214, 212, 204, 255), width=7)
    dr().line([(905, Y / 2 + 110), (860, Y / 2 + 60)], fill=(180, 178, 170, 255), width=6)
    a = np.asarray(im).astype(float) / 255
    kaydet(a, "hail-mary.webp", (600, 480), 80)


# ---------------------------------------------------------------- Endurance
def endurance() -> None:
    O = 10; G = 96 * O             # sahnede 96 x 96 birim, 10 kat; önden görünüş (sahnede basılarak eğilir)
    r = random.Random(4)
    im = Image.new("RGBA", (G, G), (0, 0, 0, 0))
    c = G / 2
    dr = ImageDraw.Draw(im, "RGBA")
    R = 34 * O
    for w, t in ((36, 60), (26, 140), (12, 205)):
        dr.ellipse([c - R - w / 2, c - R - w / 2, c + R + w / 2, c + R + w / 2], outline=(t, t, int(t * 1.03), 255), width=w)
    def cokgen(nok, aci, renk):
        k, z = np.cos(aci), np.sin(aci)
        dr.polygon([(c + x * k - y * z, c + x * z + y * k) for x, y in nok], fill=renk)
    for k in range(4):                                  # dört kol
        a = np.pi / 2 * k + 0.26
        cokgen([(0, -16), (R, -16), (R, 16), (0, 16)], a, (104, 106, 110, 255))
        cokgen([(0, -16), (R, -16), (R, -6), (0, -6)], a, (200, 202, 206, 255))
    for k in range(12):                                 # on iki bölme; ışık sol üstten
        a = np.pi / 6 * k
        isik = 0.66 + 0.44 * max(0, np.cos(a - np.radians(225))) + 0.06 * r.random()
        t = lambda m: tuple(int(255 * min(1, isik * m)) for _ in range(3)) + (255,)
        w, h = (58, 104) if k % 3 == 0 else (50, 92) if k % 3 == 1 else (54, 78)
        cokgen([(R - w, -h), (R + w * .8, -h * .9), (R + w * 1.15, -h * .3), (R + w * 1.15, h * .3), (R + w * .8, h * .9), (R - w, h)], a, t(0.80))
        cokgen([(R - w * .7, -h * .82), (R + w * .65, -h * .74), (R + w * .65, -h * .1), (R - w * .7, -h * .1)], a, t(1.02))
        cokgen([(R - w * .7, h * .06), (R + w * .65, h * .06), (R + w * .65, h * .72), (R - w * .7, h * .8)], a, t(0.66))
        cokgen([(R - w, -6), (R + w * 1.1, -6), (R + w * 1.1, 6), (R - w, 6)], a, t(0.34))
        for _ in range(5):
            x, y = R + r.uniform(-w * .6, w * .6), r.uniform(-h * .7, h * .7)
            cokgen([(x, y), (x + 12, y), (x + 12, y + 8), (x, y + 8)], a, t(r.choice((0.25, 0.45, 1.2))))
    dr.ellipse([c - 92, c - 92, c + 92, c + 92], fill=(96, 98, 102, 255))
    dr.ellipse([c - 80, c - 84, c + 72, c + 68], fill=(186, 188, 192, 255))
    cokgen([(-52, -150), (52, -150), (70, 20), (0, 90), (-70, 20)], np.radians(40), (222, 224, 226, 255))
    cokgen([(0, -150), (52, -150), (70, 20), (0, 90)], np.radians(40), (132, 134, 140, 255))
    cokgen([(-22, -138), (22, -138), (26, -104), (-26, -104)], np.radians(40), (22, 24, 30, 255))
    kaydet(np.asarray(im).astype(float) / 255, "endurance.webp", (288, 288), 80)


if __name__ == "__main__":
    for ad in sys.argv[1:] or ("gargantua", "golge_gemi", "tunel", "kapi", "hail", "los_hail", "endurance"):
        globals()[ad]()
