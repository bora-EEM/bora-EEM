"""Kuzey Labs uzay sahnesi: tek dosyalık, JavaScript'siz, yordamsal üretilmiş animasyonlu SVG.

GitHub README'de <img> içinde oynar (yalnız SVG + SMIL; dış kaynak, yazı tipi, betik yok).
Katmanlar arkadan öne:
  1. derin uzay zemini ve iki ayrı hızda kayan yıldız alanı (paralaks)
  2. Samanyolu: çok katmanlı fraktal gürültüden bulutsu, koyu toz yarıkları ve pembe H-II bölgeleri,
     şeride Gauss dağılımıyla serpilmiş, kara cisim renk sıcaklığına göre boyanmış yıldızlar
  3. kırınım çivili parlak yıldızlar
  4. Küçük Ayı takımyıldızı (çizgi çizgi çizilir) ve Kuzey Yıldızı'nın etrafında dönen gösterge halkaları
  5. yörüngede halkalı gezegen, kayan yıldızlar
  6. motor parçacıkları geride iz bırakan, takla atan roket
Çalıştırma: python uzay_uret.py  ->  kuzey-uzay.svg
"""
from __future__ import annotations

import math
import random
from pathlib import Path

W, H = 880, 300
TOHUM = 1907                      # aynı tohum, aynı gökyüzü
BANT_MERKEZ = (440.0, 150.0)
BANT_ACI = -math.degrees(math.atan2(H, W))   # sol alttan Kuzey Yıldızı'na doğru
KUTUP = (720.0, 96.0)             # Kuzey Yıldızı
ROKET_YOLU = ("M-80,252 C120,292 262,204 404,238 C506,264 566,186 522,156 "
              "C478,126 436,204 522,234 C646,278 768,216 980,188")
ROKET_SURE = 9.0

# Yıldız renkleri: tayf sınıfına göre yaklaşık kara cisim rengi ve gökyüzündeki payı
TAYF = [("#9bb0ff", 0.06), ("#aabfff", 0.10), ("#cad7ff", 0.16), ("#f8f7ff", 0.30),
        ("#fff4ea", 0.18), ("#ffd2a1", 0.12), ("#ffb36b", 0.08)]


def tayf_sec(r: random.Random) -> str:
    x, toplam = r.random(), 0.0
    for renk, pay in TAYF:
        toplam += pay
        if x <= toplam:
            return renk
    return TAYF[-1][0]


def parlaklik(r: random.Random, en_kucuk: float, en_buyuk: float, us: float = 2.6) -> float:
    """Güç yasası: sönük yıldız çok, parlak yıldız az."""
    return en_kucuk + (en_buyuk - en_kucuk) * (r.random() ** us)


def f(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


class Sahne:
    def __init__(self) -> None:
        self.r = random.Random(TOHUM)
        self.parca: list[str] = []

    def ekle(self, *satirlar: str) -> None:
        self.parca.extend(satirlar)

    # ---------- tanımlar ----------
    def tanimlar(self) -> None:
        self.ekle(f'''<defs>
  <radialGradient id="zemin" cx="0.72" cy="0.28" r="1.05">
    <stop offset="0" stop-color="#2e2850"/><stop offset="0.5" stop-color="#1d1936"/><stop offset="1" stop-color="#0c0a1a"/>
  </radialGradient>
  <radialGradient id="bantMaske" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.75"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </radialGradient>
  <mask id="bant" maskUnits="userSpaceOnUse" x="-300" y="-300" width="1500" height="900">
    <ellipse cx="{BANT_MERKEZ[0]}" cy="{BANT_MERKEZ[1]}" rx="600" ry="74" fill="url(#bantMaske)"/>
  </mask>
  <mask id="cekirdek" maskUnits="userSpaceOnUse" x="-300" y="-300" width="1500" height="900">
    <ellipse cx="{BANT_MERKEZ[0] + 60}" cy="{BANT_MERKEZ[1]}" rx="420" ry="34" fill="url(#bantMaske)"/>
  </mask>
  <filter id="bulutsu" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.0045 0.026" numOctaves="5" seed="11"/>
    <feColorMatrix values="0 0 0 0 0.88  0 0 0 0 0.84  0 0 0 0 0.98  1.8 0 0 0 -0.72"/>
  </filter>
  <filter id="sicak" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.008 0.04" numOctaves="4" seed="5"/>
    <feColorMatrix values="0 0 0 0 1  0 0 0 0 0.86  0 0 0 0 0.72  2.4 0 0 0 -1.0"/>
  </filter>
  <filter id="toz" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.016 0.075" numOctaves="6" seed="3"/>
    <feColorMatrix values="0 0 0 0 0.20  0 0 0 0 0.15  0 0 0 0 0.22  2.4 0 0 0 -1.12"/>
    <feGaussianBlur stdDeviation="0.8"/>
  </filter>
  <filter id="tozInce" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.03 0.12" numOctaves="4" seed="8"/>
    <feColorMatrix values="0 0 0 0 0.26  0 0 0 0 0.2  0 0 0 0 0.28  2.2 0 0 0 -1.05"/>
  </filter>
  <filter id="hii" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.02 0.07" numOctaves="3" seed="21"/>
    <feColorMatrix values="0 0 0 0 1  0 0 0 0 0.42  0 0 0 0 0.72  5 0 0 0 -3.05"/>
    <feGaussianBlur stdDeviation="1.4"/>
  </filter>
  <filter id="yildizTozu" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.62" numOctaves="1" seed="42"/>
    <feColorMatrix values="0 0 0 0 0.95  0 0 0 0 0.93  0 0 0 0 1  16 0 0 0 -10.6"/>
  </filter>
  <filter id="yildizTozu2" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="1" seed="77"/>
    <feColorMatrix values="0 0 0 0 0.85  0 0 0 0 0.88  0 0 0 0 1  14 0 0 0 -8.9"/>
  </filter>
  <filter id="duman" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.8"/></filter>
  <filter id="pus" x="-50%" y="-300%" width="200%" height="700%"><feGaussianBlur stdDeviation="24"/></filter>
  <filter id="pus2" x="-50%" y="-300%" width="200%" height="700%"><feGaussianBlur stdDeviation="9"/></filter>
  <filter id="isik" x="-150%" y="-150%" width="400%" height="400%">
    <feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <radialGradient id="cekirdekIsik" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff"/><stop offset="0.16" stop-color="#cfe0ff"/><stop offset="0.5" stop-color="#4d7dff" stop-opacity="0.45"/><stop offset="1" stop-color="#4d7dff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="cicekIsik" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff" stop-opacity="0.95"/><stop offset="0.3" stop-color="#cfd8ff" stop-opacity="0.5"/><stop offset="1" stop-color="#cfd8ff" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="civi" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="galxe" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#8b5cf6"/><stop offset="0.5" stop-color="#58a6ff"/><stop offset="1" stop-color="#34e0a1"/>
  </linearGradient>
  <linearGradient id="kuyruk" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="0.95"/>
  </linearGradient>
  <linearGradient id="govde" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.55" stop-color="#d7dee8"/><stop offset="1" stop-color="#8b95a5"/>
  </linearGradient>
  <radialGradient id="gezegen" cx="0.35" cy="0.35" r="0.75">
    <stop offset="0" stop-color="#b9ffe3"/><stop offset="0.5" stop-color="#34e0a1"/><stop offset="1" stop-color="#0b5d45"/>
  </radialGradient>
  <radialGradient id="yaziGolge" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#04060e" stop-opacity="0.7"/><stop offset="1" stop-color="#04060e" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="kenarMor1" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#8b5cf6" stop-opacity="0.85"/><stop offset="0.45" stop-color="#6d28d9" stop-opacity="0.38"/><stop offset="1" stop-color="#3b0764" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="kenarMor2" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#c084fc" stop-opacity="0.6"/><stop offset="0.5" stop-color="#7e22ce" stop-opacity="0.26"/><stop offset="1" stop-color="#4c1d95" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="kenarMavi" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#4f46e5" stop-opacity="0.6"/><stop offset="1" stop-color="#312e81" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="vinyet" cx="0.5" cy="0.5" r="0.75">
    <stop offset="0.6" stop-color="#05030c" stop-opacity="0"/><stop offset="1" stop-color="#05030c" stop-opacity="0.55"/>
  </radialGradient>
  <linearGradient id="huzme" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#e9d5ff" stop-opacity="0"/><stop offset="0.5" stop-color="#e9d5ff" stop-opacity="0.22"/><stop offset="1" stop-color="#e9d5ff" stop-opacity="0"/>
  </linearGradient>
  <g id="cicek">
    <circle r="7" fill="url(#cicekIsik)"/>
    <rect x="-13" y="-0.45" width="26" height="0.9" fill="url(#civi)"/>
    <rect x="-13" y="-0.45" width="26" height="0.9" fill="url(#civi)" transform="rotate(90)"/>
    <circle r="1.3" fill="#fff"/>
  </g>
  <path id="roketYolu" d="{ROKET_YOLU}"/>
  <path id="yorunge" d="M{f(KUTUP[0] - 118)},{f(KUTUP[1])} a118,38 0 1,1 236,0 a118,38 0 1,1 -236,0"/>
</defs>''')

    # ---------- 1. zemin ve paralaks yıldızlar ----------
    def zemin(self) -> None:
        self.ekle(f'<rect width="{W}" height="{H}" fill="url(#zemin)"/>',
                  f'<rect width="{W}" height="{H}" filter="url(#yildizTozu)" opacity="0.75"/>')
        for katman, (adet, hiz, en_buyuk) in enumerate([(620, 160, 0.85), (260, 90, 1.25), (45, 60, 1.7)]):
            daireler = []
            for _ in range(adet):
                x, y = self.r.uniform(0, W), self.r.uniform(0, H)
                rr = parlaklik(self.r, 0.35, en_buyuk)
                op = 0.25 + 0.6 * self.r.random()
                daireler.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr)}" fill="{tayf_sec(self.r)}" opacity="{op:.2f}"/>')
            govde = "".join(daireler)
            # aynı yıldız alanı iki kez, yan yana: sola kaydıkça dikişsiz döner
            self.ekle(f'<g><animateTransform attributeName="transform" type="translate" from="0 0" to="-{W} 0" '
                      f'dur="{hiz}s" repeatCount="indefinite"/><g>{govde}</g><g transform="translate({W} 0)">{govde}</g></g>')
        # göz kırpan yıldızlar
        for _ in range(26):
            x, y = self.r.uniform(0, W), self.r.uniform(0, H)
            sure, bas = self.r.uniform(1.8, 5.5), self.r.uniform(0, 5)
            self.ekle(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(self.r.uniform(0.7, 1.4))}" fill="{tayf_sec(self.r)}">'
                      f'<animate attributeName="opacity" values="0.9;0.1;0.9" dur="{sure:.1f}s" begin="{bas:.1f}s" repeatCount="indefinite"/></circle>')

    # ---------- 2. Samanyolu ----------
    def samanyolu(self) -> None:
        cx, cy = BANT_MERKEZ
        self.ekle(f'<g transform="rotate({BANT_ACI:.2f} {cx} {cy})">')
        self.ekle(
            f'<ellipse cx="{cx}" cy="{cy}" rx="620" ry="86" fill="#5b4f8f" opacity="0.5" filter="url(#pus)">'
            '<animate attributeName="opacity" values="0.42;0.58;0.42" dur="10s" repeatCount="indefinite"/></ellipse>',
            f'<ellipse cx="{cx + 40}" cy="{cy}" rx="460" ry="40" fill="#a99bd6" opacity="0.26" filter="url(#pus2)"/>',
            f'<ellipse cx="{cx + 90}" cy="{cy - 2}" rx="160" ry="24" fill="#efe2d2" opacity="0.22" filter="url(#pus2)"/>',
            f'<rect x="-200" y="20" width="1300" height="260" filter="url(#bulutsu)" mask="url(#bant)" opacity="0.8"/>',
            f'<rect x="-200" y="20" width="1300" height="260" filter="url(#sicak)" mask="url(#cekirdek)" opacity="0.75"/>',
            f'<rect x="-200" y="20" width="1300" height="260" filter="url(#hii)" mask="url(#bant)" opacity="0.22"/>',
        )
        # şeride yoğunlaşan yıldızlar: kalınlık boyunca Gauss, çekirdeğe doğru sıklaşır
        yildizlar = []
        for _ in range(1400):
            x = self.r.uniform(-160, 1040)
            yogun = math.exp(-((x - (cx + 90)) / 420) ** 2)
            if self.r.random() > 0.35 + 0.65 * yogun:
                continue
            y = cy + self.r.gauss(0, 16 + 10 * (1 - yogun))
            rr = parlaklik(self.r, 0.3, 1.25, 3.2)
            yildizlar.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr)}" fill="{tayf_sec(self.r)}" opacity="{0.35 + 0.6 * self.r.random():.2f}"/>')
        self.ekle("<g>" + "".join(yildizlar) + "</g>")
        self.ekle('<rect x="-200" y="20" width="1300" height="260" filter="url(#yildizTozu2)" mask="url(#bant)"/>')
        # koyu toz yarıkları en üstte: yıldızların bir kısmını örter, derinlik verir
        self.ekle(f'<rect x="-200" y="20" width="1300" height="260" filter="url(#toz)" mask="url(#cekirdek)" opacity="0.8"/>',
                  f'<rect x="-200" y="20" width="1300" height="260" filter="url(#tozInce)" mask="url(#cekirdek)" opacity="0.5"/>')
        # yarıkların arasından sızan ışık: tozun önünde sönük, sıcak bir parıltı
        self.ekle(f'<ellipse cx="{cx + 90}" cy="{cy}" rx="230" ry="14" fill="#f4e7da" opacity="0.13" filter="url(#pus2)"/>')
        self.ekle("</g>")

    # ---------- 3. kırınım çivili parlak yıldızlar ----------
    def parlaklar(self) -> None:
        for _ in range(4):
            x = self.r.uniform(60, 860)
            y = BANT_MERKEZ[1] - (x - BANT_MERKEZ[0]) * math.tan(math.radians(-BANT_ACI)) + self.r.gauss(0, 40)
            s = self.r.uniform(0.45, 0.8)
            sure = self.r.uniform(3, 6)
            self.ekle(f'<g transform="translate({f(x)} {f(y)})"><g><use href="#cicek"/>'
                      f'<animateTransform attributeName="transform" type="scale" values="{s:.2f};{s * 0.7:.2f};{s:.2f}" '
                      f'dur="{sure:.1f}s" repeatCount="indefinite"/></g></g>')

    # ---------- 4. Küçük Ayı ve Kuzey Yıldızı ----------
    def takimyildiz(self) -> None:
        y = [(520, 172), (506, 214), (562, 226), (568, 180), (612, 150), (662, 122), KUTUP]
        kenar = [(0, 1), (1, 2), (2, 3), (3, 0), (3, 4), (4, 5), (5, 6)]
        T = 12.0
        self.ekle('<g stroke="#b9d3ff" stroke-width="1.1" stroke-linecap="round" opacity="0.85">')
        for k, (i, j) in enumerate(kenar):
            (x1, y1), (x2, y2) = y[i], y[j]
            L = math.dist((x1, y1), (x2, y2))
            bas, son = (0.4 + 0.45 * k) / T, (0.85 + 0.45 * k) / T
            self.ekle(f'<line x1="{x1}" y1="{y1}" x2="{f(x2)}" y2="{f(y2)}" stroke-dasharray="{L:.0f}" stroke-dashoffset="{L:.0f}">'
                      f'<animate attributeName="stroke-dashoffset" dur="{T}s" repeatCount="indefinite" '
                      f'values="{L:.0f};{L:.0f};0;0;{L:.0f}" keyTimes="0;{bas:.3f};{son:.3f};0.93;1"/></line>')
        self.ekle("</g>")
        for x, yy in y[:-1]:
            self.ekle(f'<circle cx="{x}" cy="{yy}" r="2.4" fill="#f4f7ff" filter="url(#isik)"/>')

        kx, ky = KUTUP
        altigen = " ".join(f"{f(58 * math.cos(math.radians(60 * i - 90)))},{f(58 * math.sin(math.radians(60 * i - 90)))}" for i in range(6))
        self.ekle(f'''<g transform="translate({kx} {ky})">
  <g opacity="0.75"><polygon points="{altigen}" fill="none" stroke="url(#galxe)" stroke-width="1.2"/>
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="48s" repeatCount="indefinite"/></g>
  <g opacity="0.55"><circle r="45" fill="none" stroke="#58a6ff" stroke-width="1.4" stroke-dasharray="48 22 8 22"/>
    <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="22s" repeatCount="indefinite"/></g>
  <g opacity="0.6"><circle r="33" fill="none" stroke="#34e0a1" stroke-width="3" stroke-dasharray="0.8 4.4"/>
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="36s" repeatCount="indefinite"/></g>
  <circle r="26" fill="url(#cekirdekIsik)" opacity="0.8"><animate attributeName="r" values="22;30;22" dur="3.2s" repeatCount="indefinite"/></circle>
  <g filter="url(#isik)"><path d="M0,-19 L2.6,-2.6 L19,0 L2.6,2.6 L0,19 L-2.6,2.6 L-19,0 L-2.6,-2.6 Z" fill="#fff"/>
    <path d="M0,-9 L1.2,-1.2 L9,0 L1.2,1.2 L0,9 L-1.2,1.2 L-9,0 L-1.2,-1.2 Z" fill="#fff" transform="rotate(45)"/>
    <animateTransform attributeName="transform" type="rotate" values="0;12;0" dur="7s" repeatCount="indefinite"/></g>
</g>''')
        self.ekle(f'<g font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="9.5" font-weight="700" fill="#c9d8ff">'
                  f'<text x="{kx}" y="{ky + 76}" text-anchor="middle" letter-spacing="1.2">POLARIS · α UMi</text>'
                  f'<text x="{kx}" y="{ky + 88}" text-anchor="middle" fill="#9fb0d6">+89° 15′ 51″</text></g>')

    # ---------- 5. gezegen ve kayan yıldızlar ----------
    def gezegen(self) -> None:
        self.ekle('<ellipse cx="%s" cy="%s" rx="118" ry="38" fill="none" stroke="#34e0a1" stroke-opacity="0.18" stroke-dasharray="2 6">'
                  '<animate attributeName="stroke-dashoffset" values="0;80" dur="8s" repeatCount="indefinite"/></ellipse>' % KUTUP)
        self.ekle('<g><animateMotion dur="14s" repeatCount="indefinite"><mpath href="#yorunge"/></animateMotion>'
                  '<circle r="7" fill="url(#gezegen)"/>'
                  '<ellipse rx="13" ry="3.4" fill="none" stroke="#d9fff1" stroke-width="1.1" stroke-opacity="0.85" transform="rotate(-20)"/></g>')

    def kayan_yildizlar(self) -> None:
        for bas, (x0, y0), (x1, y1), sure in [(1.5, (250, 20), (430, 92), 11), (6.8, (560, 250), (760, 300), 13), (9.2, (60, 40), (210, 110), 17)]:
            aci = math.degrees(math.atan2(y1 - y0, x1 - x0))
            self.ekle(f'<g opacity="0"><animate attributeName="opacity" dur="{sure}s" begin="{bas}s" repeatCount="indefinite" '
                      f'values="0;1;0;0" keyTimes="0;0.02;0.07;1"/>'
                      f'<g><animateTransform attributeName="transform" type="translate" dur="{sure}s" begin="{bas}s" repeatCount="indefinite" '
                      f'values="{x0} {y0};{x1} {y1};{x1} {y1}" keyTimes="0;0.07;1"/>'
                      f'<rect x="-80" y="-0.9" width="80" height="1.8" rx="0.9" fill="url(#kuyruk)" transform="rotate({aci:.1f})"/></g></g>')

    def uydu_izi(self) -> None:
        """Uzun pozlamalı fotoğraftaki gibi gökyüzünü boydan geçen ince, sönük bir uydu çizgisi."""
        x0, y0, x1, y1 = 300, -10, 470, 310
        L = math.dist((x0, y0), (x1, y1))
        self.ekle(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="#e8e4ff" stroke-width="0.8" stroke-opacity="0.45" '
                  f'stroke-dasharray="{L:.0f}" stroke-dashoffset="{L:.0f}"><animate attributeName="stroke-dashoffset" '
                  f'values="{L:.0f};0;0;-{L:.0f}" keyTimes="0;0.45;0.75;1" dur="16s" repeatCount="indefinite"/></line>')

    # ---------- 6. roket ve motor izi ----------
    def roket(self) -> None:
        # motor izi: aynı yolu biraz geriden izleyen parçacıklar; negatif başlangıç gecikme verir
        self.ekle('<g filter="url(#duman)">')
        for k in range(1, 19):
            gecikme = k * 0.045
            rr = 1.6 + k * 0.32
            renk = "#ffd27a" if k < 5 else ("#ff9b54" if k < 10 else "#8792a6")
            op = max(0.05, 0.85 - k * 0.045)
            self.ekle(f'<circle r="{f(rr)}" fill="{renk}" opacity="{op:.2f}"><animateMotion dur="{ROKET_SURE}s" '
                      f'begin="-{ROKET_SURE - gecikme:.3f}s" repeatCount="indefinite"><mpath href="#roketYolu"/></animateMotion></circle>')
        self.ekle("</g>")
        self.ekle(f'''<g><animateMotion dur="{ROKET_SURE}s" repeatCount="indefinite" rotate="auto"><mpath href="#roketYolu"/></animateMotion>
  <g transform="translate(-24 0)"><path d="M0,-4 L-14,0 L0,4 Z" fill="#ffcf6b"><animateTransform attributeName="transform" type="scale"
    values="1 1;1.45 0.8;0.85 1.1;1 1" dur="0.22s" repeatCount="indefinite"/></path>
    <path d="M0,-2.2 L-7,0 L0,2.2 Z" fill="#fff"/></g>
  <path d="M-21,-6 L-27,-15 L-15,-6 Z M-21,6 L-27,15 L-15,6 Z" fill="#34e0a1"/>
  <path d="M-24,-7 L-10,-7 C4,-7 12,-3.4 17,0 C12,3.4 4,7 -10,7 L-24,7 Z" fill="url(#govde)"/>
  <path d="M8,-4.6 C12,-3 14,-1.4 17,0 C14,1.4 12,3 8,4.6 Z" fill="#ff6b6b"/>
  <circle cx="-2" cy="0" r="3.4" fill="#0b1424" stroke="#58a6ff" stroke-width="1.5"/>
  <circle cx="-3" cy="-1" r="1" fill="#cfe6ff"/>
</g>''')

    # ---------- ışık oyunları ----------
    def isik_oyunlari(self) -> None:
        """Kenarlardan sızan, nefes alır gibi kayan mor ışıklar; sahneyi yavaşça tarayan bir ışık hüzmesi; sinema vinyeti."""
        isiklar = [  # (degrade, merkez yolu, yarıçap, süre, opaklık aralığı)
            ("kenarMor1", "-40,330;60,300;-40,330", (300, 170), 13, "0.55;0.95;0.55"),
            ("kenarMor2", "900,-30;820,10;900,-30", (260, 150), 11, "0.5;0.9;0.5"),
            ("kenarMavi", "440,-60;520,-40;440,-60", (330, 90), 17, "0.4;0.75;0.4"),
            ("kenarMor1", "920,330;860,300;920,330", (240, 130), 15, "0.4;0.8;0.4"),
        ]
        self.ekle(f'<rect width="{W}" height="{H}" fill="url(#vinyet)"/>', '<g style="mix-blend-mode:screen">')
        for degrade, yol, (rx, ry), sure, op in isiklar:
            x, y = yol.split(";")[0].split(",")
            self.ekle(f'<ellipse cx="0" cy="0" rx="{rx}" ry="{ry}" fill="url(#{degrade})" transform="translate({x} {y})">'
                      f'<animateTransform attributeName="transform" type="translate" values="{yol.replace(",", " ")}" dur="{sure}s" repeatCount="indefinite"/>'
                      f'<animate attributeName="opacity" values="{op}" dur="{sure * 0.7:.1f}s" repeatCount="indefinite"/></ellipse>')
        # ışık hüzmesi: eğik, geniş, sönük; 16 saniyede bir sahneyi soldan sağa tarar
        self.ekle('<rect x="-160" y="-200" width="160" height="700" fill="url(#huzme)" transform="rotate(24 0 150)">'
                  '<animate attributeName="x" values="-260;-260;1100" keyTimes="0;0.55;1" dur="16s" repeatCount="indefinite"/></rect>')
        self.ekle("</g>")

    # ---------- yazı ----------
    def yazi(self) -> None:
        self.ekle('<ellipse cx="160" cy="160" rx="190" ry="70" fill="url(#yaziGolge)"/>',
                  '<g font-family="\'Segoe UI\',Ubuntu,\'Helvetica Neue\',Arial,sans-serif">'
                  '<text x="48" y="152" font-size="42" font-weight="800" fill="#f5f7ff" letter-spacing="0.5">Kuzey Labs</text>'
                  '<text x="50" y="184" font-size="15" font-weight="600" fill="#7fb4ff">kuzeylabs.com</text></g>')

    def yaz(self, yol: Path) -> int:
        self.ekle(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
                  'aria-label="Kuzey Labs: Samanyolu boyunca Kuzey Yıldızı\'na uzanan takımyıldız, yörüngede bir gezegen ve takla atan bir roket.">',
                  '<!-- uzay_uret.py ile yordamsal üretildi; elle düzenlenmez -->',
                  f'<clipPath id="kose"><rect width="{W}" height="{H}" rx="16"/></clipPath>')
        self.tanimlar()
        self.ekle('<g clip-path="url(#kose)">')
        self.zemin(); self.samanyolu(); self.parlaklar(); self.uydu_izi(); self.takimyildiz()
        self.gezegen(); self.kayan_yildizlar(); self.roket(); self.isik_oyunlari(); self.yazi()
        self.ekle("</g>", f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#30363d"/>', "</svg>")
        metin = "\n".join(self.parca)
        yol.write_text(metin, encoding="utf-8")
        return len(metin.encode("utf-8"))


if __name__ == "__main__":
    hedef = Path(__file__).with_name("kuzey-uzay.svg")
    print(f"{hedef.name}: {Sahne().yaz(hedef) / 1024:.0f} KB")
