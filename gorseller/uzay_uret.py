"""Kuzey Labs uzay sahnesi: tek dosyalık, JavaScript'siz, yordamsal üretilmiş animasyonlu SVG.

GitHub README'de <img> içinde oynar (yalnız SVG + SMIL; dış kaynak, yazı tipi, betik yok).
Katmanlar arkadan öne:
  1. derin uzay zemini ve iki ayrı hızda kayan yıldız alanı (paralaks)
  2. Samanyolu: çok katmanlı fraktal gürültüden bulutsu, koyu toz yarıkları ve pembe H-II bölgeleri,
     şeride Gauss dağılımıyla serpilmiş, kara cisim renk sıcaklığına göre boyanmış yıldızlar
  3. kırınım çivili parlak yıldızlar
  4. arkada sönük duran Kuzey Yıldızı; arada Büyük Ayı çizgi çizgi birleşir, kepçenin ağzı Kuzey Yıldızı'nı
     gösterir ve o an yıldız bütün gösterge halkalarıyla parlar
  5. kayan yıldızlar
  6. 60 saniyelik senaryo: önce takla atan roket geçer, sonra üstten Apollo süzülür, ardından bir uçan daire
     yazıyı çekici ışınla tarar, bir avcıyla karşılaşır, ışıkla selamlaşırlar, avcı ışık hızına atlar
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
ROKET_SURE = 9.0                  # roketin sahneyi geçtiği süre
DONGU = 60.0                      # senaryonun tamamı; roket döngünün başında bir kez geçer
BUYUK_AYI = (17.0, 48.2)          # Büyük Ayı’nın birleştiği anlar (ikincisi avcının ışık hızına atladığı an)
KOLAY = "0.45 0 0.55 1"           # yumuşak hızlanıp yavaşlama
DUZ = "0 0 1 1"                   # sabit hız

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


def cizelge(noktalar: list[tuple], d: float = DONGU) -> str:
    """[(saniye, değer[, eğri])] -> SMIL values/keyTimes/keySplines; döngünün başı ve sonu kendiliğinden tutulur."""
    n = [(t, v, e[0] if e else KOLAY) for t, v, *e in noktalar]
    if n[0][0] > 0:
        n.insert(0, (0.0, n[0][1], DUZ))
    if n[-1][0] < d:
        n.append((d, n[-1][1], DUZ))
    kt = ";".join(f"{t / d:.5f}" for t, _, _ in n)
    return (f'values="{";".join(str(v) for _, v, _ in n)}" keyTimes="{kt}" calcMode="spline" '
            f'keySplines="{";".join(e for _, _, e in n[1:])}" dur="{d:g}s" repeatCount="indefinite"')


def tasi(noktalar: list[tuple]) -> str:
    return f'<animateTransform attributeName="transform" type="translate" {cizelge(noktalar)}/>'


def dondur(noktalar: list[tuple]) -> str:
    return f'<animateTransform attributeName="transform" type="rotate" {cizelge(noktalar)}/>'


def olcekle(noktalar: list[tuple]) -> str:
    return f'<animateTransform attributeName="transform" type="scale" {cizelge(noktalar)}/>'


def degistir(nitelik: str, noktalar: list[tuple]) -> str:
    return f'<animate attributeName="{nitelik}" {cizelge(noktalar)}/>'


def gorun(noktalar: list[tuple]) -> str:
    return degistir("opacity", noktalar)


def sallan(dy: float, sure: float) -> str:
    return (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {dy};0 0" '
            f'dur="{sure}s" repeatCount="indefinite"/>')


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

    # ---------- 4. Büyük Ayı ve Kuzey Yıldızı ----------
    def takimyildiz(self) -> None:
        kx, ky = KUTUP
        # Büyük Ayı'nın gökteki yaklaşık biçimi (Dubhe'ye göre); kepçenin ağzı Merak'tan Dubhe'ye doğru Kuzey Yıldızı'nı gösterir
        bicim = {"dubhe": (0, 0), "merak": (2, 26), "phecda": (-32, 34), "megrez": (-38, 12),
                 "alioth": (-60, 8), "mizar": (-80, 10), "alkaid": (-104, 24)}
        dubhe = (790.0, 195.0)
        hedef = math.atan2(ky - dubhe[1], kx - dubhe[0])
        donus = hedef - math.atan2(-26, -2)        # Merak->Dubhe yönünü Kuzey Yıldızı'na çevir
        c, sn = math.cos(donus), math.sin(donus)
        yer = {ad: (dubhe[0] + x * c - y * sn, dubhe[1] + x * sn + y * c) for ad, (x, y) in bicim.items()}
        merak, phecda, megrez, alioth, mizar, alkaid = (yer[a] for a in ("merak", "phecda", "megrez", "alioth", "mizar", "alkaid"))
        kenar = [(alkaid, mizar), (mizar, alioth), (alioth, megrez), (megrez, dubhe),
                 (dubhe, merak), (merak, phecda), (phecda, megrez)]

        def her_olayda(parca) -> list[tuple]:
            return [nk for s0 in BUYUK_AYI for nk in parca(s0)]

        # çizgiler sırayla çizilir, kepçenin ağzından Kuzey Yıldızı'na kesik bir çizgi uzanır, sonra hepsi söner
        self.ekle(f'<g stroke="#b9d3ff" stroke-width="1.1" stroke-linecap="round" opacity="0">'
                  + gorun(her_olayda(lambda s0: [(s0, 0), (s0 + 0.05, 0.85), (s0 + 6.4, 0.85), (s0 + 7.4, 0)])))
        for k, ((x1, y1), (x2, y2)) in enumerate(kenar):
            L = math.dist((x1, y1), (x2, y2))
            ciz = her_olayda(lambda s0: [(s0 + 0.3 * k, round(L)), (s0 + 0.3 * k + 0.35, 0),
                                         (s0 + 7.45, 0), (s0 + 7.5, round(L), DUZ)])
            self.ekle(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke-dasharray="{L:.0f}" '
                      f'stroke-dashoffset="{L:.0f}">{degistir("stroke-dashoffset", ciz)}</line>')
        isaret = [(eksen, her_olayda(lambda s0, a=a, b=b: [(s0 + 2.3, f(a)), (s0 + 3.2, f(b)), (s0 + 7.45, f(b)), (s0 + 7.5, f(a), DUZ)]))
                  for eksen, a, b in (("x2", dubhe[0], kx), ("y2", dubhe[1], ky))]
        self.ekle(f'<line x1="{f(dubhe[0])}" y1="{f(dubhe[1])}" x2="{f(dubhe[0])}" y2="{f(dubhe[1])}" stroke="#dbe7ff" '
                  f'stroke-dasharray="3 3.5" stroke-width="1.2">' + "".join(degistir(e, nk) for e, nk in isaret) + "</line></g>")
        # yıldızlar hep yerinde, olayda parlar; Mizar'ın yanında sönük eşi Alcor
        self.ekle('<g opacity="0.5">' + gorun(her_olayda(lambda s0: [(s0, 0.5), (s0 + 0.6, 1), (s0 + 6.4, 1), (s0 + 7.4, 0.5)])))
        for (x, yy), r in zip((dubhe, merak, phecda, megrez, alioth, mizar, alkaid), (2.4, 2.1, 2.0, 1.6, 2.2, 2.1, 2.1)):
            self.ekle(f'<circle cx="{f(x)}" cy="{f(yy)}" r="{r}" fill="#f4f7ff" filter="url(#isik)"/>')
        self.ekle(f'<circle cx="{f(mizar[0] + 3.4)}" cy="{f(mizar[1] - 3.6)}" r="0.8" fill="#dfe8ff"/></g>')

        # Kuzey Yıldızı: tek başına sönük bir yıldız; göstergeleri yalnız Büyük Ayı ona uzandığında yanar
        altigen = " ".join(f"{f(58 * math.cos(math.radians(60 * i - 90)))},{f(58 * math.sin(math.radians(60 * i - 90)))}" for i in range(6))
        yan = gorun(her_olayda(lambda s0: [(s0 + 3.0, 0.1), (s0 + 3.5, 1), (s0 + 6.4, 1), (s0 + 7.4, 0.1)]))
        dalga = her_olayda(lambda s0: [(s0 + 3.2, 4), (s0 + 4.4, 70, "0.2 0.6 0.4 1")])
        dalga_op = her_olayda(lambda s0: [(s0 + 3.15, 0), (s0 + 3.25, 0.9), (s0 + 4.4, 0)])
        self.ekle(f'''<g transform="translate({kx} {ky})">
  <circle r="5" fill="url(#cekirdekIsik)" opacity="0.6"/><circle r="1.7" fill="#fff" filter="url(#isik)" opacity="0.85"/>
  <circle r="4" fill="none" stroke="#cfe6ff" stroke-width="1.4" opacity="0">{degistir("r", dalga)}{gorun(dalga_op)}</circle>
  <g opacity="0.1">{yan}
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
  <g font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="9.5" font-weight="700" fill="#c9d8ff">
    <text y="76" text-anchor="middle" letter-spacing="1.2">POLARIS · α UMi</text>
    <text y="88" text-anchor="middle" fill="#9fb0d6">+89° 15′ 51″</text></g>
  </g>
</g>''')

    # ---------- 5. kayan yıldızlar ----------
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
        # döngünün yalnız ilk ROKET_SURE saniyesinde yolu baştan sona geçer, kalan sürede sahne dışında bekler
        gecis = (f'dur="{DONGU:g}s" repeatCount="indefinite" calcMode="linear" keyPoints="0;1;1" '
                 f'keyTimes="0;{ROKET_SURE / DONGU:.4f};1"')
        self.ekle('<g filter="url(#duman)">')
        for k in range(1, 19):
            gecikme = k * 0.045
            rr = 1.6 + k * 0.32
            renk = "#ffd27a" if k < 5 else ("#ff9b54" if k < 10 else "#8792a6")
            op = max(0.05, 0.85 - k * 0.045)
            self.ekle(f'<circle r="{f(rr)}" fill="{renk}" opacity="{op:.2f}"><animateMotion {gecis} '
                      f'begin="-{DONGU - gecikme:.3f}s"><mpath href="#roketYolu"/></animateMotion></circle>')
        self.ekle("</g>")
        self.ekle(f'''<g><animateMotion {gecis} rotate="auto"><mpath href="#roketYolu"/></animateMotion>
  <g transform="translate(-24 0)"><path d="M0,-4 L-14,0 L0,4 Z" fill="#ffcf6b"><animateTransform attributeName="transform" type="scale"
    values="1 1;1.45 0.8;0.85 1.1;1 1" dur="0.22s" repeatCount="indefinite"/></path>
    <path d="M0,-2.2 L-7,0 L0,2.2 Z" fill="#fff"/></g>
  <path d="M-21,-6 L-27,-15 L-15,-6 Z M-21,6 L-27,15 L-15,6 Z" fill="#34e0a1"/>
  <path d="M-24,-7 L-10,-7 C4,-7 12,-3.4 17,0 C12,3.4 4,7 -10,7 L-24,7 Z" fill="url(#govde)"/>
  <path d="M8,-4.6 C12,-3 14,-1.4 17,0 C14,1.4 12,3 8,4.6 Z" fill="#ff6b6b"/>
  <circle cx="-2" cy="0" r="3.4" fill="#0b1424" stroke="#58a6ff" stroke-width="1.5"/>
  <circle cx="-3" cy="-1" r="1" fill="#cfe6ff"/>
</g>''')

    # ---------- 7. olaylar: 60 saniyelik senaryo ----------
    # 0-9 sn roket geçer, 11-30 sn Apollo süzülür, 31-38 sn uçan daire yazıyı çekici ışınla tarar,
    # 38-47 sn bir avcıyla karşılaşır ve ışıkla selamlaşırlar, avcı Kuzey Yıldızı'na doğru ışık hızına atlar,
    # uçan daire de hızla uzaklaşır.
    DAIRE = (530, 234)                 # karşılaşmada uçan dairenin durduğu yer
    AVCI = (392, 252)                  # avcının durduğu yer

    def olaylar(self) -> None:
        self.ekle('''<defs>
  <linearGradient id="metal" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f6f8fc"/><stop offset="0.45" stop-color="#c3cad6"/><stop offset="1" stop-color="#5d6573"/>
  </linearGradient>
  <linearGradient id="nozul" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#2a2e37"/><stop offset="1" stop-color="#7b8392"/>
  </linearGradient>
  <linearGradient id="kubbe" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#e0fbff" stop-opacity="0.95"/><stop offset="0.6" stop-color="#58d5ff" stop-opacity="0.55"/><stop offset="1" stop-color="#1d4ed8" stop-opacity="0.45"/>
  </linearGradient>
  <linearGradient id="cekim" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#b6ffe4" stop-opacity="0.7"/><stop offset="1" stop-color="#34e0a1" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="parlama" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff"/><stop offset="0.35" stop-color="#cfe6ff" stop-opacity="0.8"/><stop offset="1" stop-color="#58a6ff" stop-opacity="0"/>
  </radialGradient>
  <clipPath id="koni"><path d="M-10,6 L10,6 L78,132 L-78,132 Z"/></clipPath>
  <clipPath id="servisKesit"><rect x="-13.3" y="-10" width="30" height="20"/></clipPath>
</defs>''')
        self.apollo(); self.daire(); self.avci(); self.selamlasma()

    def apollo(self) -> None:
        """Komuta ve servis modülü: üstten sabit hızla süzülür, yavaşça döner, ara ara yön iticileri püskürür."""
        puf = lambda anlar: (gorun([nk for t in anlar for nk in [(t - 0.05, 0), (t, 0.9), (t + 0.6, 0)]])
                             + degistir("r", [nk for t in anlar for nk in [(t - 0.05, 0.6), (t + 0.6, 5)]]))
        self.ekle(f'''<g opacity="0">{gorun([(10.8, 0), (11.3, 1), (29.3, 1), (29.8, 0)])}
<g>{tasi([(11, "960 40"), (29.8, "-90 22", DUZ)])}
 <text y="-17" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="7.5" font-weight="700"
   letter-spacing="1.2" fill="#9fb0d6">APOLLO · CSM</text>
 <g>{dondur([(11, -10), (29.8, 18, DUZ)])}<g transform="scale(0.9)">
  <circle cx="-7" cy="-15" r="1" fill="#fff" opacity="0">{puf([15.6, 23.2])}</circle>
  <circle cx="-7" cy="15" r="1" fill="#fff" opacity="0">{puf([19.4, 26.4])}</circle>
  <path d="M16.7,-5 L29,-9.5 L29,9.5 L16.7,5 Z" fill="url(#nozul)"/>
  <path d="M12,10 L15.5,18.5" stroke="#aab2c0" stroke-width="0.9"/>
  <g fill="#dfe4ec"><circle cx="13.6" cy="18.6" r="1.8"/><circle cx="17.4" cy="18.6" r="1.8"/><circle cx="13.6" cy="22.4" r="1.8"/><circle cx="17.4" cy="22.4" r="1.8"/></g>
  <rect x="-13.3" y="-10" width="30" height="20" fill="url(#metal)"/>
  <rect x="-1" y="-10" width="7" height="20" fill="#f1f4f9" opacity="0.5"/>
  <path d="M-6,-10 V10 M3,-10 V10 M11,-10 V10" stroke="#7d8696" stroke-width="0.6"/>
  <g clip-path="url(#servisKesit)"><rect x="-20" y="-10" width="3" height="20" fill="#fff" opacity="0.55">
    <animate attributeName="x" values="-20;20" dur="3.4s" repeatCount="indefinite"/></rect></g>
  <rect x="-9" y="-12.6" width="4" height="2.6" fill="#a9b1bf"/><rect x="-9" y="10" width="4" height="2.6" fill="#a9b1bf"/>
  <rect x="-15.5" y="-11.5" width="2.2" height="23" rx="1" fill="#8a6a4a"/>
  <path d="M-31,-3 Q-32.2,0 -31,3 L-15,11 L-15,-11 Z" fill="url(#metal)"/>
  <rect x="-24" y="-3.5" width="2.4" height="2.4" fill="#1b2433"/><circle cx="-22.8" cy="-2.3" r="0.6" fill="#ffd27a"/>
 </g></g>
</g></g>''')

    def daire(self) -> None:
        """Uçan daire: yukarıdan iner, yazıyı çekici ışınla iki kez tarar, karşılaşma yerine geçer, sonunda sallanıp kaçar."""
        dx, dy = self.DAIRE
        isiklar = "".join(
            f'<circle cx="{x}" cy="2.2" r="1.4" fill="{"#ffd27a" if i % 2 else "#58d5ff"}" opacity="0.3">'
            f'<animate attributeName="opacity" values="0.25;1;0.25" dur="1.05s" begin="-{i * 0.15:.2f}s" repeatCount="indefinite"/></circle>'
            for i, x in enumerate(range(-21, 22, 7)))
        tara = [(33.5, 10), (35.3, 130, DUZ), (35.35, 10, DUZ), (37.2, 130, DUZ)]
        self.ekle(f'''<g opacity="0">{gorun([(30.9, 0), (31.1, 1), (50.2, 1), (50.5, 0)])}
<g>{tasi([(31, "150 -50"), (33, "150 64"), (38, "150 64"), (39.4, "350 84", "0.4 0 1 1"), (41, f"{dx} {dy}", "0 0 0.4 1"),
          (49.6, f"{dx} {dy}"), (50.4, "1010 150", "0.6 0 1 1")])}
 <g>{dondur([(48.4, 0), (48.7, -9), (49, 8), (49.3, -5), (49.6, 0)])}
 <g>{olcekle([(49.6, "1 1"), (50.4, "0.25 0.25", "0.6 0 1 1")])}
 <g>{sallan(-2.5, 2.6)}
  <g opacity="0">{gorun([(33.1, 0), (33.5, 0.9), (35.3, 0.6), (35.9, 0.9), (37.2, 0.9), (37.7, 0)])}
    <path d="M-10,6 L10,6 L78,132 L-78,132 Z" fill="url(#cekim)"/>
    <g clip-path="url(#koni)"><rect x="-80" y="10" width="160" height="2.2" fill="#e6fff5" opacity="0.85">{degistir("y", tara)}</rect></g>
  </g>
  <ellipse cy="5.5" rx="16" ry="4" fill="#34e0a1" opacity="0.35" filter="url(#isik)"/>
  <path d="M-11,-4 A11,10 0 0,1 11,-4 Z" fill="url(#kubbe)"/>
  <circle cx="0" cy="-8.2" r="2.6" fill="#34e0a1"/><circle cx="-0.9" cy="-8.6" r="0.55" fill="#05130d"/><circle cx="0.9" cy="-8.6" r="0.55" fill="#05130d"/>
  <ellipse rx="27" ry="7.5" fill="url(#metal)"/>
  <ellipse cy="1.2" rx="26" ry="3" fill="none" stroke="#5d6573" stroke-width="0.8"/>
  {isiklar}
 </g></g></g>
</g></g>''')

    def avci(self) -> None:
        """Dört kanatlı avcı: soldan süzülür, selamlaşmadan sonra burnunu Kuzey Yıldızı'na çevirip ışık hızına atlar."""
        ax, ay = self.AVCI
        aci = math.degrees(math.atan2(KUTUP[1] - ay, KUTUP[0] - ax))
        self.ekle(f'''<g opacity="0">{gorun([(38.4, 0), (38.6, 1), (47.7, 1), (47.85, 0)])}
<g>{tasi([(38.5, "-70 264"), (41.5, f"{ax} {ay}", "0.2 0.6 0.4 1")])}
 <g>{dondur([(46.0, 0), (46.9, f"{aci:.1f}")])}
 <g>{tasi([(47.25, "0 0"), (47.8, "950 0", "0.8 0 1 1")])}
 <g>{olcekle([(47.1, "1 1"), (47.3, "2.6 0.55")])}
 <g>{sallan(1.5, 3.1)}
  <ellipse cx="-18" rx="6" ry="4.5" fill="#ff7a59" opacity="0.55" filter="url(#isik)">
    {degistir("rx", [(46.3, 6), (47.2, 15)])}<animate attributeName="ry" values="4.5;5.5;4.5" dur="0.3s" repeatCount="indefinite"/></ellipse>
  <path d="M-12,-2 L-6,-2 L-2,-13 L-10,-13 Z M-12,2 L-6,2 L-2,13 L-10,13 Z" fill="#9aa1ae"/>
  <rect x="-11" y="-14" width="20" height="1.2" fill="#7f8796"/><rect x="-11" y="12.8" width="20" height="1.2" fill="#7f8796"/>
  <path d="M-16,-3 L6,-2.6 L24,-0.8 L25,0 L24,0.8 L6,2.6 L-16,3 Z" fill="url(#metal)"/>
  <path d="M10,-2.2 L13,-1.9 L13,1.9 L10,2.2 Z" fill="#e2483d"/>
  <path d="M-2,-2.9 L5,-2.5 L3,-1.1 L-2,-1.1 Z" fill="#1b2433"/>
  <path d="M-13,-2 L-5,-2 L1,-17 L-9,-17 Z M-13,2 L-5,2 L1,17 L-9,17 Z" fill="#e6e9ef"/>
  <path d="M-10.4,-7 L-3.4,-7 L-2.6,-9 L-9.8,-9 Z M-10.4,7 L-3.4,7 L-2.6,9 L-9.8,9 Z" fill="#e2483d"/>
  <rect x="-10" y="-18" width="24" height="1.3" fill="#c9ced8"/><rect x="-10" y="16.7" width="24" height="1.3" fill="#c9ced8"/>
  <circle cx="-16" cy="-1.6" r="1.5" fill="#ffb199"/><circle cx="-16" cy="1.6" r="1.5" fill="#ffb199"/>
 </g></g></g></g>
</g></g>''')
        # ışık hızı: yıldızlar avcının gidiş yönünde çizgiye uzar, kalkış noktasında parlama ve şok halkası
        r = random.Random(TOHUM + 7)
        cizgiler = []
        for _ in range(26):
            yy, x0, L = r.uniform(-36, 36), r.uniform(-70, 40), r.uniform(70, 240)
            cizgiler.append(f'<line x1="{f(x0)}" y1="{f(yy)}" x2="{f(x0)}" y2="{f(yy)}" stroke-width="{r.uniform(0.5, 1.3):.1f}">'
                            + degistir("x2", [(47.2, f(x0)), (47.65, f(x0 + L), "0.6 0 1 1"), (48.4, f(x0 + L)), (48.5, f(x0), DUZ)]) + "</line>")
        self.ekle(f'<g transform="translate({ax} {ay}) rotate({aci:.1f})" stroke="#dbeaff" stroke-linecap="round" opacity="0">'
                  + gorun([(47.15, 0), (47.3, 0.9), (47.75, 0.9), (48.3, 0)]) + "".join(cizgiler) + "</g>")
        self.ekle(f'<circle cx="{ax}" cy="{ay}" r="2" fill="url(#parlama)" opacity="0">'
                  + degistir("r", [(47.25, 2), (47.6, 34, "0.2 0.6 0.4 1")]) + gorun([(47.2, 0), (47.3, 1), (47.9, 0)]) + "</circle>")
        self.ekle(f'<circle cx="{ax}" cy="{ay}" r="4" fill="none" stroke="#cfe6ff" stroke-width="1.2" opacity="0">'
                  + degistir("r", [(47.3, 4), (48.1, 64, "0.2 0.6 0.4 1")]) + gorun([(47.28, 0), (47.35, 0.6), (48.1, 0)]) + "</circle>")

    def selamlasma(self) -> None:
        """Avcı üç ışık atar, uçan daire halkalarla cevap verir ve avcıya yeşil bir küre fırlatır."""
        (ax, ay), (dx, dy) = self.AVCI, self.DAIRE
        for i in range(3):
            t = 41.6 + 0.42 * i
            self.ekle(f'<circle cx="{ax + 25}" cy="{ay}" r="2.2" fill="#ffd27a" filter="url(#isik)" opacity="0">'
                      + degistir("cx", [(t, ax + 25), (t + 0.55, dx - 27, DUZ)]) + degistir("cy", [(t, ay), (t + 0.55, dy + 2, DUZ)])
                      + gorun([(t - 0.02, 0), (t, 1), (t + 0.5, 1), (t + 0.56, 0)]) + "</circle>")
        for i in range(3):
            t = 43.2 + 0.4 * i
            self.ekle(f'<circle cx="{dx}" cy="{dy}" r="4" fill="none" stroke="#34e0a1" stroke-width="1.5" opacity="0">'
                      + degistir("r", [(t, 4), (t + 0.9, 38, "0.2 0.6 0.4 1")]) + gorun([(t - 0.02, 0), (t, 0.9), (t + 0.9, 0)]) + "</circle>")
        self.ekle(f'<g opacity="0">' + gorun([(44.5, 0), (44.6, 1), (45.95, 1), (46.05, 0)])
                  + f'<animateMotion path="M{dx},{dy + 6} Q{(ax + dx) / 2},{dy - 40} {ax + 22},{ay}" dur="{DONGU:g}s" repeatCount="indefinite" '
                  f'calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;{44.6 / DONGU:.5f};{46 / DONGU:.5f};1"/>'
                  '<circle r="7" fill="url(#parlama)" opacity="0.6"/><circle r="2.8" fill="#34e0a1" filter="url(#isik)"/></g>')
        self.ekle(f'<circle cx="{ax + 6}" cy="{ay}" r="3" fill="url(#parlama)" opacity="0">'
                  + degistir("r", [(46, 3), (46.5, 20)]) + gorun([(45.98, 0), (46.02, 0.8), (46.5, 0)]) + "</circle>")

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
                  '<text x="50" y="184" font-size="15" font-weight="600" fill="#7fb4ff">kuzeylabs.com</text>'
                  '<text x="48" y="152" font-size="42" font-weight="800" fill="#7dffcf" letter-spacing="0.5" opacity="0" filter="url(#isik)">'
                  + gorun([(33.6, 0), (34.4, 0.6), (35.3, 0.15), (36.2, 0.6), (37.5, 0)]) + 'Kuzey Labs</text>'
                  '<text x="50" y="104" font-size="11.5" font-style="italic" fill="#4bd5ee" letter-spacing="0.6" opacity="0">'
                  + gorun([(38.3, 0), (38.9, 1), (42.2, 1), (43, 0)]) + 'Çok çok uzak bir galakside…</text></g>')

    def yaz(self, yol: Path) -> int:
        self.ekle(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
                  'aria-label="Kuzey Labs: Samanyolu, Kuzey Yıldızı\'nı gösteren Büyük Ayı, geçen bir roket ve Apollo, ışıkla selamlaşan bir uçan daire ile bir avcı.">',
                  '<!-- uzay_uret.py ile yordamsal üretildi; elle düzenlenmez -->',
                  f'<clipPath id="kose"><rect width="{W}" height="{H}" rx="16"/></clipPath>')
        self.tanimlar()
        self.ekle('<g clip-path="url(#kose)">')
        self.zemin(); self.samanyolu(); self.parlaklar(); self.uydu_izi(); self.takimyildiz()
        self.kayan_yildizlar(); self.roket(); self.olaylar(); self.isik_oyunlari(); self.yazi()
        self.ekle("</g>", f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#30363d"/>', "</svg>")
        metin = "\n".join(self.parca)
        yol.write_text(metin, encoding="utf-8")
        return len(metin.encode("utf-8"))


if __name__ == "__main__":
    hedef = Path(__file__).with_name("kuzey-uzay.svg")
    print(f"{hedef.name}: {Sahne().yaz(hedef) / 1024:.0f} KB")
