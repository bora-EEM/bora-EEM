"""Kuzey Labs uzay sahnesi: tek dosyalık, JavaScript'siz, yordamsal üretilmiş animasyonlu SVG.

GitHub README'de <img> içinde oynar (yalnız SVG + SMIL; dış kaynak, yazı tipi, betik yok).
Sürekli duran arka plan, arkadan öne:
  1. derin uzay zemini ve iki ayrı hızda kayan yıldız alanı (paralaks)
  2. Samanyolu: çok katmanlı fraktal gürültüden bulutsu, koyu toz yarıkları ve pembe H-II bölgeleri,
     şeride Gauss dağılımıyla serpilmiş, kara cisim renk sıcaklığına göre boyanmış yıldızlar
  3. kırınım çivili parlak yıldızlar, uydu izi, kayan yıldızlar, ışık oyunları
  4. sönük duran Büyük Ayı ve Kuzey Yıldızı, "Kuzey Labs" yazısı
Açılışta takla atan roket bir kez geçer (saati `kroket`). Ardından 10 anomali gelir; her biri kendi saatine
(`k_<ad>`) bağlıdır ve bir öncekinin bitişinden birkaç saniye sonra başlar, sonuncunun bitişi ilkini yeniden başlatır.
Sırayı ve aralıkları kuzeylabs.com worker'ı her istekte karıştırır; bu betik parçaları ve sabit sıralı yedek dosyayı üretir.

Çalıştırma: python uzay_uret.py  ->  kuzey-uzay.svg (yedek, sabit sıra) ve
            ../../kuzey-labs/site/worker/uzay_parcalar.js (BAS, ANOMALILER, SON)
"""
from __future__ import annotations

import base64
import json
import math
import random
from contextlib import contextmanager
from pathlib import Path

W, H = 880, 300
TOHUM = 1907                      # aynı tohum, aynı gökyüzü
BANT_MERKEZ = (440.0, 150.0)
BANT_ACI = -math.degrees(math.atan2(H, W))   # sol alttan Kuzey Yıldızı'na doğru
KUTUP = (720.0, 96.0)             # Kuzey Yıldızı
ROKET_YOLU = ("M-80,252 C120,292 262,204 404,238 C506,264 566,186 522,156 "
              "C478,126 436,204 522,234 C646,278 768,216 980,188")
ROKET_BASLA = 0.4                 # açılışta roketin kalktığı an
ROKET_SURE = 9.0                  # roketin sahneyi geçtiği süre
DONGU = 60.0                      # arka plandaki uzun döngülerin süresi
KOLAY = "0.45 0 0.55 1"           # yumuşak hızlanıp yavaşlama
DUZ = "0 0 1 1"                   # sabit hız
YEDEK_TOHUM = 7                   # yedek dosyanın sabit sırası
ARA = (2.0, 5.0)                  # iki anomali arasındaki bekleme, saniye
YER_TUTUCU = "__BASLA__"
ETIKET = ('font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="20" font-weight="700" '
          'letter-spacing="0.4" fill="#dce4f8" stroke="#090816" stroke-width="4" stroke-opacity="0.72" paint-order="stroke"')
ALT = 15                          # ikinci satırın yazı boyu (telefonda resim yaklaşık 0,4 kata iner: 20 -> 8 px)

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


# Etkin saat: None iken animasyonlar DONGU'yla sonsuz döner; bir anomalinin içinde (kimlik, süre) olur ve
# her animasyon o saatin başlangıcına bağlanır, bir kez oynar, son değerinde kalır.
_SAAT: tuple[str, float] | None = None


@contextmanager
def saat(kimlik: str, sure: float):
    global _SAAT
    eski, _SAAT = _SAAT, (kimlik, sure)
    try:
        yield
    finally:
        _SAAT = eski


def _seri(noktalar: list[tuple], d: float) -> list[tuple]:
    n = [(t, v, e[0] if e else KOLAY) for t, v, *e in noktalar]
    if n[0][0] > 0:
        n.insert(0, (0.0, n[0][1], DUZ))
    if n[-1][0] < d:
        n.append((d, n[-1][1], DUZ))
    assert n[-1][0] <= d + 1e-9 and all(a[0] <= b[0] for a, b in zip(n, n[1:])), (d, noktalar)
    return n


def _zaman(d: float) -> str:
    if _SAAT:
        return f'dur="{d:g}s" begin="{_SAAT[0]}.begin" fill="freeze"'
    return f'dur="{d:g}s" repeatCount="indefinite"'


def cizelge(noktalar: list[tuple], d: float | None = None) -> str:
    """[(saniye, değer[, eğri])] -> SMIL values/keyTimes/keySplines; başı ve sonu kendiliğinden tutulur.
    Etkin bir saat varsa süre onun süresidir ve animasyon o saatin başlangıcına bağlanır."""
    d = _SAAT[1] if _SAAT else (d or DONGU)
    n = _seri(noktalar, d)
    kt = ";".join(f"{t / d:.5f}" for t, _, _ in n)
    return (f'values="{";".join(str(v) for _, v, _ in n)}" keyTimes="{kt}" calcMode="spline" '
            f'keySplines="{";".join(e for _, _, e in n[1:])}" {_zaman(d)}')


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


def yolda(yol: str, noktalar: list[tuple], yone_don: bool = False) -> str:
    """Bir yol boyunca hareket: [(saniye, yolun kesri 0..1[, eğri])]; etkin saate bağlıdır."""
    assert _SAAT, "yolda yalnız bir saatin içinde kullanılır"
    d = _SAAT[1]
    n = _seri(noktalar, d)
    don = ' rotate="auto"' if yone_don else ""
    return (f'<animateMotion path="{yol}" keyPoints="{";".join(f"{v:g}" for _, v, _ in n)}" '
            f'keyTimes="{";".join(f"{t / d:.5f}" for t, _, _ in n)}" calcMode="spline" '
            f'keySplines="{";".join(e for _, _, e in n[1:])}" {_zaman(d)}{don}/>')


def titres(bas: float, son: float, adim: float, a, b) -> list[tuple]:
    """Alev gibi titreşen değerler: bas..son arasında adim aralıkla a ve b arasında gidip gelir."""
    n, t, i = [], bas, 0
    while t <= son + 1e-9:
        n.append((round(t, 3), a if i % 2 == 0 else b, DUZ))
        t += adim; i += 1
    return n


def sallan(dy: float, sure: float) -> str:
    return (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {dy};0 0" '
            f'dur="{sure}s" repeatCount="indefinite"/>')


FOTO = Path(__file__).resolve().parent / "foto"
KART_YAZI = 'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" text-anchor="middle"'


def foto_karti(dosya: str, baslik: str, kaynak: str, merkez: tuple, cikis: tuple, donus: tuple,
               t0: float, t1: float, t2: float, t3: float, ek: str = "") -> str:
    """Gerçek fotoğraf kartı: çıkış noktasından büyüyerek merkezde açılır, t1..t2 durur, küçülerek dönüş noktasına gider.
    Fotoğraf data URI olarak gömülür (GitHub resim içinden dış adres yüklemez)."""
    veri = base64.b64encode((FOTO / dosya).read_bytes()).decode("ascii")
    ac, kapa = "0.2 0.7 0.3 1", "0.6 0 0.85 0.4"
    m, c, d = (f"{f(x)} {f(y)}" for x, y in (merkez, cikis, donus))
    return (f'<g opacity="0">{gorun([(t0, 0), (t0 + 0.25, 1), (t3 - 0.25, 1), (t3, 0)])}'
            f'<g>{tasi([(t0, c), (t1, m, ac), (t2, m, DUZ), (t3, d, kapa)])}'
            f'<g>{olcekle([(t0, "0.04 0.04"), (t1, "1.3 1.3", ac), (t2, "1.3 1.3", DUZ), (t3, "0.04 0.04", kapa)])}\n'
            f'  <rect x="-82" y="-88" width="164" height="184" rx="4" fill="#070914" fill-opacity="0.93" stroke="#9fb0d6" stroke-width="0.6" stroke-opacity="0.75"/>\n'
            f'  <image x="-70" y="-80" width="140" height="140" href="data:image/jpeg;base64,{veri}"/>\n'
            f'  <rect x="-70" y="-80" width="140" height="140" fill="none" stroke="#dbe7ff" stroke-width="0.4" stroke-opacity="0.45"/>{ek}\n'
            f'  <text y="76" {KART_YAZI} font-size="13" font-weight="700" letter-spacing="0.2" fill="#e3eaff">{baslik}</text>\n'
            f'  <text y="89" {KART_YAZI} font-size="10" fill="#a9b6da">{kaynak}</text>\n'
            f'</g></g></g>')


def etiket(metin: str, x: float = 0, y: float = 0, hiza: str = "middle", boyut: float | None = None, renk: str | None = None,
           alt: str | None = None) -> str:
    """Anın adı; alt verilirse altına daha küçük, sönük ikinci satır (uzun adı iki satıra bölmek için)."""
    if alt:
        return (etiket(metin, x, y, hiza, boyut, renk)
                + etiket(alt, x, y + (boyut or 20) * 0.5 + ALT * 0.85, hiza, ALT, "#b4c1e4").replace('font-weight="700"', 'font-weight="600"'))
    stil = ETIKET if boyut is None else ETIKET.replace('font-size="20"', f'font-size="{boyut:g}"')
    if renk:
        stil = stil.replace('fill="#d3ddf5"', f'fill="{renk}"')
    return f'<text x="{f(x)}" y="{f(y)}" text-anchor="{hiza}" {stil}>{metin}</text>'


# Gizli takımyıldızlar: gerçek konum (J2000; sağ açıklık saat, dik açıklık derece) ve kadir.
# Yıldızlar hep yerinde, biraz parlak; çizgi ve ad kendi uzun döngüsünde birkaç saniye çok soluk belirir.
GOK_BUYUKAYI = {"dubhe": (11.0621, 61.7508), "merak": (11.0307, 56.3825), "phecda": (11.8972, 53.6947),
                "megrez": (12.2571, 57.0325), "alioth": (12.9005, 55.9597), "mizar": (13.3988, 54.9253),
                "alkaid": (13.7923, 49.3133), "polaris": (2.5303, 89.2642)}
# ad: (etiket, yıldızlar [(ad, sa, da, kadir, renk)], çizgiler, çerçeve, döngü sn, beliriş sn, etiket yeri)
TAKIMYILDIZLAR = {
    "kucukayi": ("KÜÇÜK AYI", [
        ("kochab", 14.8451, 74.1556, 2.08, "#ffcf9a"), ("pherkad", 15.3455, 71.8339, 3.05, "#eef2ff"),
        ("eta", 16.2918, 75.7553, 4.95, "#f4f6ff"), ("zeta", 15.7343, 77.7944, 4.32, "#f4f6ff"),
        ("eps", 16.7662, 82.0372, 4.21, "#ffe9c4"), ("delta", 17.5369, 86.5864, 4.36, "#f4f6ff")],
        [("polaris", "delta"), ("delta", "eps"), ("eps", "zeta"), ("zeta", "kochab"), ("kochab", "pherkad"),
         ("pherkad", "eta"), ("eta", "zeta")], "kutup", 67, 45, "sol"),
    "avci": ("AVCI", [
        ("betelgeuse", 5.9195, 7.4069, 0.50, "#ffb070"), ("rigel", 5.2423, -8.2017, 0.13, "#cfe0ff"),
        ("bellatrix", 5.4189, 6.3497, 1.64, "#dbe6ff"), ("saiph", 5.7959, -9.6697, 2.06, "#d6e2ff"),
        ("alnitak", 5.6793, -1.9428, 1.77, "#d6e2ff"), ("alnilam", 5.6036, -1.2019, 1.69, "#d6e2ff"),
        ("mintaka", 5.5334, -0.2992, 2.23, "#d6e2ff"), ("meissa", 5.5856, 9.9342, 3.33, "#dbe6ff")],
        [("betelgeuse", "meissa"), ("meissa", "bellatrix"), ("betelgeuse", "bellatrix"), ("betelgeuse", "alnitak"),
         ("bellatrix", "mintaka"), ("alnitak", "alnilam"), ("alnilam", "mintaka"), ("alnitak", "saiph"),
         ("mintaka", "rigel")], ((468, 53), ("avci",)), 47, 15, "sag"),
    "kralice": ("KRALİÇE", [
        ("caph", 0.1530, 59.1497, 2.27, "#fff4dc"), ("schedar", 0.6751, 56.5372, 2.24, "#ffcf9a"),
        ("navi", 0.9451, 60.7167, 2.47, "#dbe6ff"), ("ruchbah", 1.4303, 60.2353, 2.68, "#f4f6ff"),
        ("segin", 1.9066, 63.6700, 3.38, "#dbe6ff")],
        [("caph", "schedar"), ("schedar", "navi"), ("navi", "ruchbah"), ("ruchbah", "segin")],
        ((112, 46), ("kralice",)), 59, 33, "alt"),
    "kugu": ("KUĞU", [
        ("deneb", 20.6905, 45.2803, 1.25, "#f4f6ff"), ("sadr", 20.3705, 40.2567, 2.23, "#fff1d6"),
        ("gienah", 20.7702, 33.9703, 2.48, "#ffe0b0"), ("fawaris", 19.7496, 45.1308, 2.87, "#e6eeff"),
        ("eta", 19.9384, 35.0834, 3.89, "#ffe9c4"), ("albireo", 19.5120, 27.9597, 3.08, "#ffd690")],
        [("deneb", "sadr"), ("sadr", "eta"), ("eta", "albireo"), ("fawaris", "sadr"), ("sadr", "gienah")],
        ((122, 248), ("kugu", "calgi")), 53, 24, "sol"),
    "calgi": ("ÇALGI", [
        ("vega", 18.6156, 38.7836, 0.03, "#dfe8ff"), ("eps", 18.7389, 39.6667, 4.67, "#f4f6ff"),
        ("zeta", 18.7462, 37.6050, 4.36, "#f4f6ff"), ("delta", 18.9084, 36.8986, 4.30, "#ffcf9a"),
        ("gamma", 18.9824, 32.6894, 3.24, "#e6eeff"), ("beta", 18.8347, 33.3628, 3.52, "#e6eeff")],
        [("vega", "eps"), ("vega", "zeta"), ("eps", "zeta"), ("zeta", "delta"), ("delta", "gamma"),
         ("gamma", "beta"), ("beta", "zeta")], ((122, 248), ("kugu", "calgi")), 41, 7, "sag"),
}
GOK_OLCEK = 4.0                    # piksel / derece; Büyük Ayı'nın sahnedeki ölçeğine yakın


def izdusum(sa: float, da: float, sa0: float, da0: float) -> tuple[float, float]:
    """Gnomonik izdüşüm, derece: doğu solda, kuzey yukarıda (gökyüzüne bakar gibi)."""
    a, d, a0, d0 = math.radians(sa * 15), math.radians(da), math.radians(sa0 * 15), math.radians(da0)
    c = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a - a0)
    xi = math.cos(d) * math.sin(a - a0) / c
    eta = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a - a0)) / c
    return -math.degrees(xi), -math.degrees(eta)


def _merkez(yildizlar: list[tuple]) -> tuple[float, float]:
    x = sum(math.cos(math.radians(s[1] * 15)) * math.cos(math.radians(s[2])) for s in yildizlar)
    y = sum(math.sin(math.radians(s[1] * 15)) * math.cos(math.radians(s[2])) for s in yildizlar)
    z = sum(math.sin(math.radians(s[2])) for s in yildizlar)
    return (math.degrees(math.atan2(y, x)) / 15) % 24, math.degrees(math.atan2(z, math.hypot(x, y)))


class Sahne:
    def __init__(self) -> None:
        self.r = random.Random(TOHUM)
        self.parca: list[str] = []
        self.durgun: list[str] = []   # hiç kıpırdamayan katmanlar: bir kez resme pişirilir (resme_pisir)

    def ekle(self, *satirlar: str) -> None:
        self.parca.extend(satirlar)

    def durgun_ekle(self, *satirlar: str) -> None:
        self.durgun.extend(satirlar)

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
        self.ekle(ARKA_YER)
        self.durgun_ekle(f'<rect width="{W}" height="{H}" fill="url(#zemin)"/>',
                         f'<rect width="{W}" height="{H}" filter="url(#yildizTozu)" opacity="0.75"/>')
        # uzak katman durur (arka plan resminde); orta ve yakın katman saydam birer resim olarak kayar:
        # her karede yüzlerce daire yerine tek resim çizilir
        for katman, (adet, hiz, en_buyuk) in enumerate([(620, None, 0.85), (260, 90, 1.25), (45, 60, 1.7)]):
            daireler = []
            for _ in range(adet):
                x, y = self.r.uniform(0, W), self.r.uniform(0, H)
                rr = parlaklik(self.r, 0.35, en_buyuk)
                op = 0.25 + 0.6 * self.r.random()
                daireler.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr)}" fill="{tayf_sec(self.r)}" opacity="{op:.2f}"/>')
            govde = "".join(daireler)
            if hiz is None:
                self.durgun_ekle(f"<g>{govde}</g>")
                continue
            # aynı yıldız alanı iki kez, yan yana: sola kaydıkça dikişsiz döner
            uri = resme_pisir(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{govde}</svg>',
                              FOTO / f"yildiz-katmani-{katman}.png")
            self.ekle(f'<defs><image id="yk{katman}" width="{W}" height="{H}" href="{uri}"/></defs>'
                      f'<g><animateTransform attributeName="transform" type="translate" from="0 0" to="-{W} 0" '
                      f'dur="{hiz}s" repeatCount="indefinite"/><use href="#yk{katman}"/><use href="#yk{katman}" x="{W}"/></g>')
        # göz kırpan yıldızlar
        for _ in range(26):
            x, y = self.r.uniform(0, W), self.r.uniform(0, H)
            sure, bas = self.r.uniform(1.8, 5.5), self.r.uniform(0, 5)
            self.ekle(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(self.r.uniform(0.7, 1.4))}" fill="{tayf_sec(self.r)}">'
                      f'<animate attributeName="opacity" values="0.9;0.1;0.9" dur="{sure:.1f}s" begin="{bas:.1f}s" repeatCount="indefinite"/></circle>')

    # ---------- 2. Samanyolu ----------
    def samanyolu(self) -> None:
        cx, cy = BANT_MERKEZ
        ekle = self.durgun_ekle          # Samanyolu kıpırdamaz: bütünü arka plan resmine pişer
        ekle(f'<g transform="rotate({BANT_ACI:.2f} {cx} {cy})">')
        ekle(
            f'<ellipse cx="{cx}" cy="{cy}" rx="620" ry="86" fill="#5b4f8f" opacity="0.5" filter="url(#pus)"/>',
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
        ekle("<g>" + "".join(yildizlar) + "</g>")
        ekle('<rect x="-200" y="20" width="1300" height="260" filter="url(#yildizTozu2)" mask="url(#bant)"/>')
        # koyu toz yarıkları en üstte: yıldızların bir kısmını örter, derinlik verir
        ekle(f'<rect x="-200" y="20" width="1300" height="260" filter="url(#toz)" mask="url(#cekirdek)" opacity="0.8"/>',
                  f'<rect x="-200" y="20" width="1300" height="260" filter="url(#tozInce)" mask="url(#cekirdek)" opacity="0.5"/>')
        # yarıkların arasından sızan ışık: tozun önünde sönük, sıcak bir parıltı
        ekle(f'<ellipse cx="{cx + 90}" cy="{cy}" rx="230" ry="14" fill="#f4e7da" opacity="0.13" filter="url(#pus2)"/>')
        ekle("</g>")

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

    # ---------- 4. Büyük Ayı ve Kuzey Yıldızı (arka plan) ----------
    def buyuk_ayi_yerleri(self) -> tuple[dict, list]:
        kx, ky = KUTUP
        # Büyük Ayı'nın gökteki yaklaşık biçimi (Dubhe'ye göre); kepçenin ağzı Merak'tan Dubhe'ye doğru Kuzey Yıldızı'nı gösterir
        bicim = {"dubhe": (0, 0), "merak": (2, 26), "phecda": (-32, 34), "megrez": (-38, 12),
                 "alioth": (-60, 8), "mizar": (-80, 10), "alkaid": (-104, 24)}
        dubhe = (790.0, 195.0)
        hedef = math.atan2(ky - dubhe[1], kx - dubhe[0])
        donus = hedef - math.atan2(-26, -2)        # Merak->Dubhe yönünü Kuzey Yıldızı'na çevir
        c, sn = math.cos(donus), math.sin(donus)
        yer = {ad: (dubhe[0] + x * c - y * sn, dubhe[1] + x * sn + y * c) for ad, (x, y) in bicim.items()}
        kenar = [(yer["alkaid"], yer["mizar"]), (yer["mizar"], yer["alioth"]), (yer["alioth"], yer["megrez"]),
                 (yer["megrez"], yer["dubhe"]), (yer["dubhe"], yer["merak"]), (yer["merak"], yer["phecda"]),
                 (yer["phecda"], yer["megrez"])]
        return yer, kenar

    def takimyildiz(self) -> None:
        """Yıldızlar ve sönük Kuzey Yıldızı hep yerinde; parlamaları buyukayi anomalisinin saatine bağlı."""
        kx, ky = KUTUP
        yer, _ = self.buyuk_ayi_yerleri()
        with saat("k_buyukayi", SURELER["buyukayi"]):
            parla = gorun([(0.4, 0.5), (1.0, 1), (6.8, 1), (7.8, 0.5)])
            yan = gorun([(3.4, 0.1), (3.9, 1), (6.8, 1), (7.8, 0.1)])
        self.ekle('<g opacity="0.5">' + parla)
        for ad, r in zip(("dubhe", "merak", "phecda", "megrez", "alioth", "mizar", "alkaid"), (2.4, 2.1, 2.0, 1.6, 2.2, 2.1, 2.1)):
            x, yy = yer[ad]
            self.ekle(f'<circle cx="{f(x)}" cy="{f(yy)}" r="{f(r * 3.2)}" fill="url(#hale)"/>'
                      f'<circle cx="{f(x)}" cy="{f(yy)}" r="{r}" fill="#f4f7ff"/>')
        mizar = yer["mizar"]
        self.ekle(f'<circle cx="{f(mizar[0] + 3.4)}" cy="{f(mizar[1] - 3.6)}" r="0.8" fill="#dfe8ff"/></g>')

        # Kuzey Yıldızı: tek başına sönük bir yıldız; göstergeleri yalnız Büyük Ayı ona uzandığında yanar
        altigen = " ".join(f"{f(58 * math.cos(math.radians(60 * i - 90)))},{f(58 * math.sin(math.radians(60 * i - 90)))}" for i in range(6))
        self.ekle(f'''<g transform="translate({kx} {ky})">
  <circle r="5" fill="url(#cekirdekIsik)" opacity="0.6"/><circle r="5.4" fill="url(#hale)" opacity="0.85"/><circle r="1.7" fill="#fff" opacity="0.85"/>
  <g opacity="0.1">{yan}
  <g opacity="0.75"><polygon points="{altigen}" fill="none" stroke="url(#galxe)" stroke-width="1.2"/>
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="48s" repeatCount="indefinite"/></g>
  <g opacity="0.55"><circle r="45" fill="none" stroke="#58a6ff" stroke-width="1.4" stroke-dasharray="48 22 8 22"/>
    <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="22s" repeatCount="indefinite"/></g>
  <g opacity="0.6"><circle r="33" fill="none" stroke="#34e0a1" stroke-width="3" stroke-dasharray="0.8 4.4"/>
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="36s" repeatCount="indefinite"/></g>
  <circle r="26" fill="url(#cekirdekIsik)" opacity="0.8"><animate attributeName="r" values="22;30;22" dur="3.2s" repeatCount="indefinite"/></circle>
  <g><path d="M0,-19 L2.6,-2.6 L19,0 L2.6,2.6 L0,19 L-2.6,2.6 L-19,0 L-2.6,-2.6 Z" fill="#fff"/>
    <path d="M0,-9 L1.2,-1.2 L9,0 L1.2,1.2 L0,9 L-1.2,1.2 L-9,0 L-1.2,-1.2 Z" fill="#fff" transform="rotate(45)"/>
    <animateTransform attributeName="transform" type="rotate" values="0;12;0" dur="7s" repeatCount="indefinite"/></g>
  <g font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="18" font-weight="700" fill="#dce4f8" stroke="#090816" stroke-width="3.8" stroke-opacity="0.7" paint-order="stroke">
    <text y="82" text-anchor="middle" letter-spacing="0.4">KUZEY YILDIZI</text>
    <text y="101" text-anchor="middle" font-size="14" font-weight="600" fill="#aebbe0">yaklaşık 430 ışık yılı</text></g>
  </g>
</g>''')

    def takimyildiz_yerleri(self) -> dict[str, dict[str, tuple]]:
        """Her takımyıldızın sahnedeki yıldız yerleri. Küçük Ayı, gerçek Büyük Ayı'nın sahnedeki Büyük Ayı ve
        Kuzey Yıldızı'na en küçük kareler benzerlik uydurmasıyla yerleşir; ötekiler kendi çerçevesinde, kuzey yukarıda."""
        yer, _ = self.buyuk_ayi_yerleri()
        yer = dict(yer, polaris=KUTUP)
        sa0, da0 = 12.0, 70.0
        z = [complex(*izdusum(*GOK_BUYUKAYI[ad], sa0, da0)) for ad in GOK_BUYUKAYI]
        w = [complex(*yer[ad]) for ad in GOK_BUYUKAYI]
        zm, wm = sum(z) / len(z), sum(w) / len(w)
        A = sum((wi - wm) * (zi - zm).conjugate() for zi, wi in zip(z, w)) / sum(abs(zi - zm) ** 2 for zi in z)
        sonuc: dict[str, dict[str, tuple]] = {}
        for ad, (_, yildizlar, _, cerceve, *_) in TAKIMYILDIZLAR.items():
            if cerceve == "kutup":
                p = {s[0]: A * (complex(*izdusum(s[1], s[2], sa0, da0)) - zm) + wm for s in yildizlar}
                sonuc[ad] = {k: (v.real, v.imag) for k, v in p.items()} | {"polaris": KUTUP}
                continue
            (mx, my), grup = cerceve
            hepsi = [s for g in grup for s in TAKIMYILDIZLAR[g][1]]
            sa_m, da_m = _merkez(hepsi)
            ham = [izdusum(s[1], s[2], sa_m, da_m) for s in hepsi]
            ox = (min(x for x, _ in ham) + max(x for x, _ in ham)) / 2
            oy = (min(y for _, y in ham) + max(y for _, y in ham)) / 2
            sonuc[ad] = {s[0]: (mx + GOK_OLCEK * (izdusum(s[1], s[2], sa_m, da_m)[0] - ox),
                                my + GOK_OLCEK * (izdusum(s[1], s[2], sa_m, da_m)[1] - oy)) for s in yildizlar}
        return sonuc

    def gizli_takimyildizlar(self) -> None:
        """Gerçek takımyıldızlar sürpriz olarak arka planda: yıldızlar hep yerinde, çizgi ve ad kendi döngüsünde
        4,6 saniyeliğine çok soluk belirir; döngüler farklı uzunlukta olduğundan sırayla, seyrek görünürler."""
        yerler = self.takimyildiz_yerleri()
        for ad, (etiket_metni, yildizlar, cizgiler, _, donem, bas, etiket_yeri) in TAKIMYILDIZLAR.items():
            yer = yerler[ad]
            for s in yildizlar:
                x, y = yer[s[0]]
                r = max(0.7, 1.75 - 0.21 * s[3])
                self.durgun_ekle(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{s[4]}" opacity="0.9"/>')
            yol = []
            for a, b in cizgiler:
                (x1, y1), (x2, y2) = yer[a], yer[b]
                L = math.dist((x1, y1), (x2, y2)) or 1
                ux, uy = (x2 - x1) / L, (y2 - y1) / L
                yol.append(f"M{f(x1 + 2.6 * ux)},{f(y1 + 2.6 * uy)} L{f(x2 - 2.6 * ux)},{f(y2 - 2.6 * uy)}")
            xs, ys = [p[0] for p in yer.values()], [p[1] for p in yer.values()]
            ex, ey, hiza = {"alt": ((min(xs) + max(xs)) / 2, max(ys) + 11, "middle"),
                            "sol": (min(xs) - 7, (min(ys) + max(ys)) / 2 + 3, "end"),
                            "sag": (max(xs) + 7, (min(ys) + max(ys)) / 2 + 3, "start")}[etiket_yeri]
            a, b = bas / donem, (bas + 4.6) / donem
            self.ekle(f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" '
                      f'keyTimes="0;{a:.4f};{a + 0.9 / donem:.4f};{b - 0.9 / donem:.4f};{b:.4f};1" dur="{donem}s" repeatCount="indefinite"/>'
                      f'<path d="{" ".join(yol)}" stroke="#b7c6ee" stroke-width="0.6" stroke-opacity="0.25" fill="none"/>'
                      f'<text x="{f(ex)}" y="{f(ey)}" text-anchor="{hiza}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
                      f'font-size="13" letter-spacing="0.8" fill="#aebbe0" opacity="0.6">{etiket_metni}</text></g>')

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

    # ---------- 6. açılış: roket bir kez geçer ----------
    def roket(self) -> None:
        gecis = (f'dur="{ROKET_SURE:g}s" calcMode="linear" keyPoints="0;1" keyTimes="0;1" fill="freeze"')
        self.ekle(f'<rect width="0" height="0"><animate id="kroket" attributeName="opacity" values="0;0" '
                  f'dur="{ROKET_SURE:g}s" begin="{ROKET_BASLA:g}s" fill="remove"/></rect>')
        # motor izi: aynı yolu biraz geriden izleyen parçacıklar; her biri kendi gecikmesiyle kalkar, kalkana dek görünmez
        self.ekle('<g>')
        for k in range(1, 19):
            gecikme = k * 0.045
            rr = 1.6 + k * 0.32
            renk = "url(#izSari)" if k < 5 else ("url(#izTuruncu)" if k < 10 else "url(#izGri)")
            rr *= 1.6                      # degrade kenarı yumuşattığı için biraz büyük
            op = max(0.05, 0.85 - k * 0.045)
            self.ekle(f'<circle r="{f(rr)}" fill="{renk}" opacity="0"><animate attributeName="opacity" values="{op:.2f};{op:.2f}" '
                      f'dur="{ROKET_SURE:g}s" begin="kroket.begin+{gecikme:.3f}s" fill="remove"/>'
                      f'<animateMotion {gecis} begin="kroket.begin+{gecikme:.3f}s"><mpath href="#roketYolu"/></animateMotion></circle>')
        self.ekle("</g>")
        self.ekle(f'''<g opacity="0"><animate attributeName="opacity" values="1;1" dur="{ROKET_SURE:g}s" begin="kroket.begin" fill="remove"/>
 <animateMotion {gecis} begin="kroket.begin" rotate="auto"><mpath href="#roketYolu"/></animateMotion>
  <g transform="translate(-24 0)"><path d="M0,-4 L-14,0 L0,4 Z" fill="#ffcf6b"><animateTransform attributeName="transform" type="scale"
    values="1 1;1.45 0.8;0.85 1.1;1 1" dur="0.22s" repeatCount="indefinite"/></path>
    <path d="M0,-2.2 L-7,0 L0,2.2 Z" fill="#fff"/></g>
  <path d="M-21,-6 L-27,-15 L-15,-6 Z M-21,6 L-27,15 L-15,6 Z" fill="#34e0a1"/>
  <path d="M-24,-7 L-10,-7 C4,-7 12,-3.4 17,0 C12,3.4 4,7 -10,7 L-24,7 Z" fill="url(#govde)"/>
  <path d="M8,-4.6 C12,-3 14,-1.4 17,0 C14,1.4 12,3 8,4.6 Z" fill="#ff6b6b"/>
  <circle cx="-2" cy="0" r="3.4" fill="#0b1424" stroke="#58a6ff" stroke-width="1.5"/>
  <circle cx="-3" cy="-1" r="1" fill="#cfe6ff"/>
</g>''')

    def ortak_tanimlar(self) -> None:
        """Anomalilerin paylaştığı degradeler."""
        self.ekle('''<defs>
  <linearGradient id="metal" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f6f8fc"/><stop offset="0.45" stop-color="#c3cad6"/><stop offset="1" stop-color="#5d6573"/>
  </linearGradient>
  <linearGradient id="nozul" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#2a2e37"/><stop offset="1" stop-color="#7b8392"/>
  </linearGradient>
  <radialGradient id="parlama" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff"/><stop offset="0.35" stop-color="#cfe6ff" stop-opacity="0.8"/><stop offset="1" stop-color="#58a6ff" stop-opacity="0"/>
  </radialGradient>
  <filter id="yumusak" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="0.35"/></filter>
  <radialGradient id="hale"><stop offset="0" stop-color="#f4f7ff" stop-opacity="0.75"/><stop offset="0.35" stop-color="#dfe8ff" stop-opacity="0.25"/><stop offset="1" stop-color="#dfe8ff" stop-opacity="0"/></radialGradient>
  <radialGradient id="izSari"><stop offset="0" stop-color="#ffd27a"/><stop offset="0.5" stop-color="#ffd27a" stop-opacity="0.6"/><stop offset="1" stop-color="#ffd27a" stop-opacity="0"/></radialGradient>
  <radialGradient id="izTuruncu"><stop offset="0" stop-color="#ff9b54"/><stop offset="0.5" stop-color="#ff9b54" stop-opacity="0.55"/><stop offset="1" stop-color="#ff9b54" stop-opacity="0"/></radialGradient>
  <radialGradient id="izGri"><stop offset="0" stop-color="#8792a6"/><stop offset="0.5" stop-color="#8792a6" stop-opacity="0.5"/><stop offset="1" stop-color="#8792a6" stop-opacity="0"/></radialGradient>
</defs>''')

    # ================= anomaliler =================
    def anomali(self, ad: str, ciz) -> None:
        """Bir anomaliyi kendi saatiyle paketler: saat boyutsuz bir elemandaki boş animasyondur,
        __BASLA__ yerine zincirdeki başlangıç yazılır; içteki her animasyon bu saatin başlangıcına bağlıdır."""
        sure = SURELER[ad]
        with saat(f"k_{ad}", sure):
            govde = ciz()
        svg = (f'<g id="a_{ad}"><rect width="0" height="0"><animate id="k_{ad}" attributeName="opacity" values="0;0" '
               f'dur="{sure:g}s" begin="{YER_TUTUCU}" fill="remove"/></rect>\n'
               # gövde yalnız kendi süresince çizilir: saydam ama çizimde duran on dört gövde her kareyi iki kat pahalı yapıyordu
               f'<g display="none"><set attributeName="display" to="inline" begin="k_{ad}.begin" end="k_{ad}.end"/>\n'
               f'{govde}\n</g></g>\n')
        assert svg.count(YER_TUTUCU) == 1 and "repeatCount" not in govde, ad
        self.anomaliler.append({"ad": ad, "sure": sure, "svg": svg})

    # 1. Sputnik 1 · 1957
    def sputnik(self) -> str:
        yol = "M-50,98 Q430,-24 930,72"
        hiz = [(0.2, 0), (10.8, 1, DUZ)]
        halkalar = []
        for h in range(2):
            anlar = [t for t in (0.9 + h + 2.0 * i for i in range(6)) if t + 1.5 <= SURELER["sputnik"] - 0.2]
            r_n = [nk for t in anlar for nk in [(t, 5.6, DUZ), (t + 1.5, 30, "0.2 0.6 0.4 1")]]
            o_n = [nk for t in anlar for nk in [(t, 0, DUZ), (t + 0.06, 0.85, DUZ), (t + 1.5, 0)]]
            halkalar.append(f'<circle r="5.6" fill="none" stroke="#9fe7ff" stroke-width="0.9" opacity="0">'
                            f'{degistir("r", r_n)}{gorun(o_n)}</circle>')
        isilti = gorun([nk for t in (2.6, 6.2, 9.0) for nk in [(t, 0), (t + 0.25, 1), (t + 0.8, 0)]])
        antenler = "M-3.2,-3 L-37,-11 M-3.8,-1.3 L-33,-4.6 M-3.8,1.3 L-33,4.6 M-3.2,3 L-37,11"
        return f'''<defs>
  <radialGradient id="spKure" cx="0.38" cy="0.32" r="0.72">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.22" stop-color="#e6ebf1"/><stop offset="0.6" stop-color="#8f98a8"/><stop offset="1" stop-color="#2b313c"/>
  </radialGradient>
</defs>
<g opacity="0">{gorun([(0, 0), (0.3, 1), (10.6, 1), (10.9, 0)])}
 <g>{yolda(yol, hiz, True)}
  <path d="{antenler}" stroke="#4f5766" stroke-width="1.2" stroke-linecap="round"/>
  <path d="{antenler}" stroke="#eef2f7" stroke-width="0.45" stroke-linecap="round"/>
  <path d="M-3.5,-3.4 l-2.4,-0.6 M-4,-1.4 l-2.4,-0.3 M-4,1.4 l-2.4,0.3 M-3.5,3.4 l-2.4,0.6" stroke="#2b313c" stroke-width="1.6" stroke-linecap="round"/>
 </g>
 <g>{yolda(yol, hiz)}
  {"".join(halkalar)}
  <circle r="5.8" fill="url(#spKure)"/>
  <path d="M-5.7,0.4 Q0,2.8 5.7,0.4" fill="none" stroke="#4a5260" stroke-width="0.45"/>
  <circle cx="-2.1" cy="-2.3" r="1.1" fill="#fff"/>
  <g transform="translate(-2.1 -2.3) scale(0.5)" opacity="0">{isilti}<use href="#cicek"/></g>
  {etiket("SPUTNIK 1 · 1957", 0, -15)}
 </g>
</g>'''

    # 2. Apollo 11 · 1969
    def apollo(self) -> str:
        """Komuta ve servis modülü: üstten sabit hızla süzülür, yavaşça döner, ara ara yön iticileri püskürür."""
        puf = lambda anlar: (gorun([nk for t in anlar for nk in [(t - 0.05, 0), (t, 0.9), (t + 0.6, 0)]])
                             + degistir("r", [nk for t in anlar for nk in [(t - 0.05, 0.6), (t + 0.6, 5)]]))
        parilti = [nk for i in range(4) for nk in [(0.2 + 3.2 * i, -20, DUZ), (0.2 + 3.2 * i + 2.6, 20, DUZ)]]
        return f'''<g opacity="0">{gorun([(0, 0), (0.3, 1), (12.5, 1), (12.9, 0)])}
<g>{tasi([(0.2, "960 54"), (12.8, "-90 38", DUZ)])}
 {etiket("APOLLO 11 · 1969", 0, -19)}
 <g>{dondur([(0.2, -10), (12.8, 18, DUZ)])}<g transform="scale(0.9)">
  <circle cx="-7" cy="-15" r="1" fill="#fff" opacity="0">{puf([3.3, 8.4])}</circle>
  <circle cx="-7" cy="15" r="1" fill="#fff" opacity="0">{puf([5.8, 10.5])}</circle>
  <path d="M16.7,-5 L29,-9.5 L29,9.5 L16.7,5 Z" fill="url(#nozul)"/>
  <path d="M12,10 L15.5,18.5" stroke="#aab2c0" stroke-width="0.9"/>
  <g fill="#dfe4ec"><circle cx="13.6" cy="18.6" r="1.8"/><circle cx="17.4" cy="18.6" r="1.8"/><circle cx="13.6" cy="22.4" r="1.8"/><circle cx="17.4" cy="22.4" r="1.8"/></g>
  <rect x="-13.3" y="-10" width="30" height="20" fill="url(#metal)"/>
  <rect x="-1" y="-10" width="7" height="20" fill="#f1f4f9" opacity="0.5"/>
  <path d="M-6,-10 V10 M3,-10 V10 M11,-10 V10" stroke="#7d8696" stroke-width="0.6"/>
  <g clip-path="url(#servisKesit)"><rect x="-20" y="-10" width="3" height="20" fill="#fff" opacity="0.55">{degistir("x", parilti)}</rect></g>
  <rect x="-9" y="-12.6" width="4" height="2.6" fill="#a9b1bf"/><rect x="-9" y="10" width="4" height="2.6" fill="#a9b1bf"/>
  <rect x="-15.5" y="-11.5" width="2.2" height="23" rx="1" fill="#8a6a4a"/>
  <path d="M-31,-3 Q-32.2,0 -31,3 L-15,11 L-15,-11 Z" fill="url(#metal)"/>
  <rect x="-24" y="-3.5" width="2.4" height="2.4" fill="#1b2433"/><circle cx="-22.8" cy="-2.3" r="0.6" fill="#ffd27a"/>
 </g></g>
</g></g>
<defs><clipPath id="servisKesit"><rect x="-13.3" y="-10" width="30" height="20"/></clipPath></defs>'''

    # 3. Voyager 1 · 1977 ve Soluk Mavi Nokta fotoğrafı · 1990
    def voyager(self) -> str:
        egri = "0.25 0.1 0.55 1"
        yol = [(0, "404 240"), (7.2, "600 92", egri), (15, "622 80", DUZ)]
        olc = [(0, "1.5 1.5"), (7.2, "0.32 0.32", egri), (15, "0.24 0.24", DUZ)]
        yazi_yolu = [(0, "404 282"), (7.2, "600 108", egri), (15, "622 94", DUZ)]
        isilti = gorun([nk for t in (2.4, 6.6) for nk in [(t, 0), (t + 0.3, 1), (t + 1.0, 0)]])
        # Dünya fotoğrafta (111, 110) pikselde; 220 px kare 140 px gösterilir -> kartta (0.6, -10)
        dunya = (f'\n  <g opacity="0">{gorun([(8.1, 0), (8.6, 1), (11.3, 1), (11.6, 0)])}'
                 f'<circle cx="0.6" cy="-10" r="5.5" fill="none" stroke="#9fd0ff" stroke-width="0.6"/>'
                 f'<path d="M5,-13.5 L14,-21" stroke="#9fd0ff" stroke-width="0.45"/>'
                 f'<text x="15.5" y="-21.5" {KART_YAZI.replace("middle", "start")} font-size="10" font-weight="700" '
                 f'fill="#cfe6ff" stroke="#070914" stroke-width="2.2" stroke-opacity="0.7" paint-order="stroke">Dünya</text></g>')
        kart = foto_karti("voyager-soluk-mavi-nokta.jpg", "SOLUK MAVİ NOKTA", "NASA/JPL · 1990",
                          (460, 140), (598, 94), (614, 85), 7.0, 7.9, 11.6, 12.5, dunya)
        rtg = "".join(f'<g transform="translate({f(-12 - 5.2 * i)} {f(10 + 2.6 * i)}) rotate(-26.6)">'
                      f'<rect x="-2.4" y="-1.6" width="4.8" height="3.2" rx="0.6" fill="url(#metal)"/>'
                      f'<path d="M-1.6,-2.4 V2.4 M0,-2.4 V2.4 M1.6,-2.4 V2.4" stroke="#5d6573" stroke-width="0.4"/></g>' for i in range(3))
        return f'''<defs>
  <radialGradient id="vyCanak" cx="0.42" cy="0.38" r="0.7">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.45" stop-color="#e2e7ee"/><stop offset="1" stop-color="#959eac"/>
  </radialGradient>
  <radialGradient id="vyAltin" cx="0.4" cy="0.35" r="0.7">
    <stop offset="0" stop-color="#fff4c4"/><stop offset="0.45" stop-color="#e2b23f"/><stop offset="1" stop-color="#7a5514"/>
  </radialGradient>
  <linearGradient id="vyIsin" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#eadbc2" stop-opacity="0"/><stop offset="0.5" stop-color="#eadbc2" stop-opacity="0.2"/><stop offset="1" stop-color="#eadbc2" stop-opacity="0"/>
  </linearGradient>
</defs>
<g opacity="0">{gorun([(0, 0), (1.2, 1), (13.4, 1), (14.6, 0)])}
<g>{tasi(yol)}<g>{olcekle(olc)}<g>{dondur([(0, -8), (15, 8, DUZ)])}
  <path d="M3,1 L46,-30" stroke="#7f8897" stroke-width="0.7"/><path d="M3,1 L46,-30" stroke="#eef2f7" stroke-width="0.25" opacity="0.8"/>
  <circle cx="24.5" cy="-14.4" r="0.9" fill="#c9ced6"/><rect x="44" y="-32.2" width="4" height="3" rx="1" fill="#c9ced6" transform="rotate(-36 46 -30.7)"/>
  <path d="M-5,5 L-24,15" stroke="#7d8696" stroke-width="1"/>{rtg}
  <path d="M6,5 L22,14" stroke="#7d8696" stroke-width="1"/>
  <rect x="19.5" y="12.5" width="7" height="5" fill="#6b7381"/><rect x="23" y="10" width="7" height="2.8" fill="#c3cad6"/>
  <circle cx="30" cy="11.4" r="1.1" fill="#141a26"/>
  <rect x="-8" y="0" width="5" height="7" fill="#8a93a2"/><rect x="-3" y="0" width="6" height="7" fill="#c9ced6"/><rect x="3" y="0" width="5" height="7" fill="#626a78"/>
  <path d="M-8,0 H8" stroke="#eef2f7" stroke-width="0.5"/>
  <circle cx="-5.5" cy="3.6" r="2.2" fill="url(#vyAltin)" stroke="#6b4a10" stroke-width="0.3"/><circle cx="-5.5" cy="3.6" r="0.5" fill="#6b4a10"/>
  <ellipse cx="0" cy="-2.8" rx="16.6" ry="6.6" fill="#59616f"/>
  <ellipse cx="0" cy="-4" rx="16" ry="6.2" fill="url(#vyCanak)"/>
  <ellipse cx="0" cy="-4" rx="16" ry="6.2" fill="none" stroke="#f7f9fc" stroke-width="0.5"/>
  <path d="M-9.5,-6.4 L0,-13.2 M9.5,-6.4 L0,-13.2 M0,-1.6 L0,-13.2" stroke="#aeb6c2" stroke-width="0.45"/>
  <ellipse cx="0" cy="-13.4" rx="2.5" ry="0.9" fill="#eef2f7"/>
  <path d="M-12,-6.6 Q-3,-10.4 9,-9.2" stroke="#fff" stroke-width="0.7" opacity="0.55" fill="none"/>
  <g transform="translate(-5.5 3.6) scale(0.55)" opacity="0">{isilti}<use href="#cicek"/></g>
</g></g></g>
<g>{tasi(yazi_yolu)}<g opacity="0">{gorun([(1.0, 0), (1.8, 1), (5.8, 1), (6.4, 0)])}{etiket("VOYAGER 1 · 1977")}</g></g>
</g>
{kart}'''

    # 4. Hubble · 1990 ve Ultra Derin Alan fotoğrafı (2004)
    def hubble(self) -> str:
        ax, ay = 515, 236                      # çekim anında açıklığın yeri
        kx, ky = 628, 130                      # fotoğraf kartının ortası (yazının sağında)
        kart = foto_karti("hubble-ultra-derin-alan.jpg", "ULTRA DERİN ALAN",
                          "NASA/ESA · 2004", (kx, ky), (ax, ay), (466, 234), 5.1, 5.9, 9.6, 10.4)
        izgara = " ".join(f"M-1,{f(y)} H9" for y in (-39.4, -35.8, -32.2, -28.6, -25, -21.4, -17.8)) + " M4,-43 V-14"
        izgara += " " + " ".join(f"M-1,{f(-y)} H9" for y in (-39.4, -35.8, -32.2, -28.6, -25, -21.4, -17.8)) + " M4,43 V14"
        return f'''<defs>
  <linearGradient id="hbFolyo" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.3" stop-color="#e1e6ec"/><stop offset="0.68" stop-color="#a7afbb"/><stop offset="1" stop-color="#5f6775"/>
  </linearGradient>
  <linearGradient id="hbPanel" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#3a52a8"/><stop offset="0.55" stop-color="#1d2a62"/><stop offset="1" stop-color="#111a3d"/>
  </linearGradient>
</defs>
<g opacity="0">{gorun([(0, 0), (0.2, 1), (13.1, 1), (13.4, 0)])}
<g>{tasi([(0, "930 238"), (4.4, "548 236", "0.2 0.5 0.4 1"), (9.8, "500 234", DUZ), (13.3, "-90 230", "0.6 0 0.9 0.6")])}
 {etiket("HUBBLE · 1990", 33, 3, "start")}
 <g>{dondur([(0, -3), (13.5, 3, DUZ)])}
  <path d="M4,-9.6 V-14 M4,9.6 V14" stroke="#aab2be" stroke-width="0.9"/>
  <rect x="-1" y="-43" width="10" height="29" fill="url(#hbPanel)" stroke="#c9a55a" stroke-width="0.5"/>
  <rect x="-1" y="14" width="10" height="29" fill="url(#hbPanel)" stroke="#c9a55a" stroke-width="0.5"/>
  <path d="{izgara}" stroke="#7c93d8" stroke-width="0.3" opacity="0.8"/>
  <rect x="-1" y="-43" width="10" height="29" fill="#cfe0ff" opacity="0">{gorun([(4.3, 0), (4.8, 0.35), (5.6, 0)])}</rect>
  <path d="M14,-9.6 L19,-17 M14,9.6 L19,17" stroke="#aab2be" stroke-width="0.6"/>
  <ellipse cx="19.6" cy="-18" rx="3" ry="1.1" fill="#dfe4ea" transform="rotate(30 19.6 -18)"/>
  <ellipse cx="19.6" cy="18" rx="3" ry="1.1" fill="#dfe4ea" transform="rotate(-30 19.6 18)"/>
  <rect x="6" y="-9.6" width="20" height="19.2" rx="1" fill="url(#hbFolyo)"/>
  <rect x="25" y="-8.6" width="2.8" height="17.2" rx="0.8" fill="#6f7886"/>
  <rect x="-27" y="-8.2" width="34" height="16.4" fill="url(#hbFolyo)"/>
  <rect x="-21" y="-8.2" width="7" height="16.4" fill="#cfd5dd" opacity="0.35"/><rect x="-5" y="-8.2" width="5" height="16.4" fill="#8f98a6" opacity="0.25"/>
  <path d="M-18,-8.2 V8.2 M-9,-8.2 V8.2 M0,-8.2 V8.2 M12,-9.6 V9.6 M19,-9.6 V9.6" stroke="#6f7886" stroke-width="0.35" opacity="0.75"/>
  <path d="M8,-6.4 H23 M8,6.4 H23" stroke="#e2c46a" stroke-width="0.5" stroke-dasharray="1.6 1"/>
  <rect x="-27" y="-5.8" width="53" height="1.4" fill="#fff" opacity="0.4"/>
  <ellipse cx="-27" cy="0" rx="2.2" ry="8.2" fill="#0a0d16" stroke="#9aa3b0" stroke-width="0.4"/>
  <path d="M-27,-8.2 L-37.5,-18.5" stroke="#5f6775" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M-27,-8.2 L-37.5,-18.5" stroke="#e6eaf0" stroke-width="1.2" stroke-linecap="round"/>
  <circle cx="-31" cy="0" r="2" fill="url(#parlama)" opacity="0">{degistir("r", [(4.95, 2), (5.5, 20, "0.2 0.6 0.4 1")])}{gorun([(4.9, 0), (5.0, 1), (5.8, 0)])}</circle>
 </g>
</g></g>
<path d="M{ax},{ay} L{kx - 82},{ky + 92} M{ax},{ay} L{kx - 82},{ky - 88}" stroke="#cfe0ff" stroke-width="0.5" stroke-dasharray="2 2" opacity="0">{gorun([(5.0, 0), (5.3, 0.6), (6.3, 0)])}</path>
{kart}'''

    # 5. Starman · Falcon Heavy · 2018
    def starman(self) -> str:
        govde = ("M-27.5,0.5 C-27.8,-2.6 -26.6,-4.6 -23.5,-5.2 L-9,-5.6 C-7.4,-5.6 -6.8,-3.6 -5,-3.6 L4.5,-3.6 "
                 "C6,-3.6 7,-5.4 9,-5.6 C16,-5.4 23,-4.2 27,-1.6 C28.4,-0.6 28.6,2 27.4,3.4 L22.1,3.6 "
                 "A5.6,5.6 0 0 0 10.9,3.6 L-11.4,3.6 A5.6,5.6 0 0 0 -22.6,3.6 L-26.2,3.4 C-27.2,2.8 -27.6,1.8 -27.5,0.5 Z")
        teker = lambda x: (f'<g transform="translate({x} 3.6)"><circle r="4.7" fill="#121418"/><circle r="3" fill="url(#metal)"/>'
                           f'<path d="M0,-2.6 V2.6 M-2.5,-0.8 L2.5,0.8 M-2.5,0.8 L2.5,-0.8" stroke="#6f7886" stroke-width="0.45"/>'
                           f'<circle r="0.9" fill="#2a2d33"/></g>')
        return f'''<defs>
  <linearGradient id="smKirmizi" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff8a86"/><stop offset="0.3" stop-color="#e3242b"/><stop offset="0.72" stop-color="#a3121c"/><stop offset="1" stop-color="#560a10"/>
  </linearGradient>
</defs>
<g opacity="0">{gorun([(0, 0), (0.3, 1), (13.0, 1), (13.4, 0)])}
<g>{tasi([(0.2, "-80 88"), (13.3, "960 52", DUZ)])}
 <g opacity="0">{gorun([(0.4, 0), (1.0, 1), (8.6, 1), (9.4, 0)])}{etiket("STARMAN · 2018", 40, -4, "start", alt="Falcon Heavy ile fırlatıldı")}</g>
 <g>{dondur([(0.2, 8), (13.3, -190, DUZ)])}<g transform="scale(1.15)">
  <path d="M-6.4,-3.6 L-7,-9.6 Q-6.8,-11.2 -5.2,-11 L-3.8,-3.6 Z" fill="#1d1f24"/>
  <path d="M-5.2,-3.8 C-5.5,-7.5 -4.4,-9.6 -1.8,-9.8 C0.2,-9.9 1,-8 0.8,-6 L0.4,-3.8 Z" fill="#f3f5f8"/>
  <path d="M-5,-5 C-4.6,-7.6 -3.6,-9 -2,-9.4" stroke="#b9c0ca" stroke-width="0.7" fill="none"/>
  <path d="M-1,-8 C1.5,-7.4 3.6,-6.2 5.4,-4.6" stroke="#eef1f5" stroke-width="1.9" stroke-linecap="round" fill="none"/>
  <circle cx="5.7" cy="-4.4" r="0.85" fill="#2a2d33"/>
  <circle cx="-2.4" cy="-12.6" r="3.3" fill="#f6f8fb" stroke="#b8bec8" stroke-width="0.3"/>
  <path d="M-1.4,-14.9 C1.3,-14.8 1.6,-11.1 0.1,-10.5 C-1.1,-10.7 -1.7,-13.7 -1.4,-14.9 Z" fill="#14161b"/>
  <path d="M-0.6,-14.2 Q0.6,-13.6 0.7,-12.4" stroke="#fff" stroke-width="0.4" opacity="0.8" fill="none"/>
  <polygon points="9.4,-5.4 5.2,-11.2 3.9,-11 8,-5.4" fill="#a9dcff" opacity="0.35"/>
  <path d="M9.6,-5.4 L5.2,-11.2" stroke="#1c1f25" stroke-width="1.1" stroke-linecap="round"/>
  <path d="{govde}" fill="url(#smKirmizi)"/>
  <path d="M-23,-4.7 L-9.4,-5.1 M9.6,-5.1 C16,-4.9 22,-3.9 26,-1.9" stroke="#ffd0cc" stroke-width="0.6" fill="none" opacity="0.85"/>
  <path d="M-11,3.1 L10.5,3.1" stroke="#3a0508" stroke-width="1"/>
  <path d="M-4.4,-3.2 L-5.2,3" stroke="#6b0b12" stroke-width="0.4"/>
  <path d="M-9.5,-0.6 L-6.5,-0.6" stroke="#3a0508" stroke-width="0.8" stroke-linecap="round"/>
  <rect x="-27.6" y="-3.4" width="1.3" height="1.7" rx="0.4" fill="#ff3b3b"/><rect x="25.6" y="-2.2" width="1.6" height="1.2" rx="0.4" fill="#ffe6a0"/>
  {teker(16.5)}{teker(-17)}
 </g></g>
</g></g>'''

    # 6. Starship · Mars yolunda
    def starship(self) -> str:
        # yığının yeri (ara kademe = 0,0) ve eğimi; 4.9 sn'de sıcak ayrılma
        ortak = [(0, "440 372"), (1.0, "440 330", "0.5 0 0.8 1"), (3.0, "452 236", DUZ), (4.9, "486 166", DUZ)]
        egim = [(0, 0), (1.0, 0, DUZ), (3.0, 8), (4.9, 24)]
        gemi_yeri = ortak + [(5.6, "500 152", DUZ), (8.0, "560 110", "0.3 0 0.6 1"), (12.8, "652 42", "0.2 0 0.5 1")]
        gemi_egim = egim + [(5.6, 30), (8.0, 48), (12.8, 53)]
        gemi_olcek = [(4.9, "1 1"), (12.8, "0.18 0.18", "0.15 0.6 0.4 1")]
        itici_yeri = ortak + [(5.6, "492 162", "0.2 0.6 0.4 1"), (7.4, "488 164"), (11.6, "420 392", "0.5 0 0.9 0.6")]
        itici_egim = egim + [(11.6, 24)]
        itici_don = [(5.0, "0 0 28"), (5.4, "0 0 28", DUZ), (7.2, "160 0 28"), (11.6, "176 0 28", DUZ)]
        alev_op = [(0, 1), (4.9, 1, DUZ), (4.96, 0, DUZ), (7.6, 0, DUZ), (7.9, 0.85), (9.0, 0.85, DUZ), (9.3, 0)]
        alev_olcek = titres(0.0, 4.9, 0.11, "1 1", "1.08 0.9") + [(5.0, "0.55 0.55", DUZ)] + titres(7.6, 9.3, 0.11, "0.55 0.5", "0.6 0.56")
        gemi_alev_olcek = titres(5.0, 12.8, 0.13, "1 1", "1.1 0.88")
        kaynak = " ".join(f"M-1.1,{-4.5 * i:g} H3.5" for i in range(1, 7))
        kaynak_itici = " ".join(f"M-3.5,{3 + 5.5 * i:g} H3.5" for i in range(1, 9))
        return f'''<defs>
  <linearGradient id="ssCelik" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#5a6069"/><stop offset="0.22" stop-color="#c7ccd4"/><stop offset="0.46" stop-color="#f8fafc"/><stop offset="0.64" stop-color="#d3d8df"/><stop offset="1" stop-color="#686e78"/>
  </linearGradient>
  <linearGradient id="ssAlev" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.12" stop-color="#fff1c2"/><stop offset="0.38" stop-color="#ffb347" stop-opacity="0.9"/>
    <stop offset="0.72" stop-color="#ff6a2b" stop-opacity="0.45"/><stop offset="1" stop-color="#ff3d1f" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="ssIs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2b2622" stop-opacity="0"/><stop offset="1" stop-color="#2b2622" stop-opacity="0.8"/></linearGradient>
  <radialGradient id="ssKor" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffe2b0" stop-opacity="0.9"/><stop offset="0.4" stop-color="#ff8a3d" stop-opacity="0.35"/><stop offset="1" stop-color="#ff6a2b" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="ssMars" cx="0.38" cy="0.34" r="0.72">
    <stop offset="0" stop-color="#f6b086"/><stop offset="0.45" stop-color="#c8582e"/><stop offset="1" stop-color="#4f1a0d"/>
  </radialGradient>
</defs>
<g opacity="0">{gorun([(0, 0), (0.1, 1), (13.5, 1), (13.9, 0)])}
 <ellipse cx="440" cy="304" rx="96" ry="30" fill="url(#ssKor)" opacity="0">{gorun([(0, 0), (0.4, 0.9), (1.6, 0.9), (2.8, 0)])}</ellipse>
 <g opacity="0">{gorun([(5.4, 0), (6.6, 1), (13.2, 1), (13.8, 0)])}
  <circle cx="664" cy="34" r="13" fill="url(#ssKor)" opacity="0.45"/>
  <circle cx="664" cy="34" r="6.5" fill="url(#ssMars)"/>
  <ellipse cx="663.4" cy="28.6" rx="2" ry="0.8" fill="#fff" opacity="0.75"/>
  {etiket("STARSHIP", 676, 37, "start", alt="Mars yolunda")}
 </g>
 <g>{tasi(itici_yeri)}<g>{dondur(itici_egim)}<g>{dondur(itici_don)}
  <g opacity="0">{gorun(alev_op)}<g transform="translate(0 57)"><g>{olcekle(alev_olcek)}
   <path d="M-4,0 C-6,10 -3.5,24 0,36 C3.5,24 6,10 4,0 Z" fill="url(#ssAlev)"/>
   <path d="M-2,0 C-2.6,6 -1.4,13 0,19 C1.4,13 2.6,6 2,0 Z" fill="#fff" opacity="0.85"/></g></g></g>
  <path d="M-3.5,54 L-4.4,57.2 L4.4,57.2 L3.5,54 Z" fill="#33373e"/>
  <rect x="-3.5" y="2.8" width="7" height="51.4" fill="url(#ssCelik)"/>
  <rect x="-3.5" y="38" width="7" height="16.2" fill="url(#ssIs)"/>
  <path d="{kaynak_itici}" stroke="#7d838c" stroke-width="0.25" opacity="0.6"/>
  <path d="M1.3,4 V53" stroke="#fff" stroke-width="0.5" opacity="0.45"/>
  <rect x="-3.6" y="0" width="7.2" height="2.9" fill="#3a3e45"/>
  <path d="M-2.6,0.5 V2.4 M-1.3,0.5 V2.4 M0,0.5 V2.4 M1.3,0.5 V2.4 M2.6,0.5 V2.4" stroke="#121317" stroke-width="0.55"/>
  <g fill="#41464e" stroke="#1b1d22" stroke-width="0.25"><rect x="3.5" y="4.2" width="3.2" height="3"/><rect x="-6.7" y="4.2" width="3.2" height="3"/></g>
  <path d="M3.5,5.2 H6.7 M3.5,6.2 H6.7 M4.6,4.2 V7.2 M5.6,4.2 V7.2 M-6.7,5.2 H-3.5 M-6.7,6.2 H-3.5 M-5.6,4.2 V7.2 M-4.6,4.2 V7.2" stroke="#1b1d22" stroke-width="0.25"/>
 </g></g></g>
 <g>{tasi(gemi_yeri)}<g>{dondur(gemi_egim)}<g>{olcekle(gemi_olcek)}
  <g opacity="0">{gorun([(4.9, 0), (5.0, 1), (12.8, 1)])}<g transform="translate(0 1.6)"><g>{olcekle(gemi_alev_olcek)}
   <path d="M-2.6,0 C-3.4,6 -1.6,13 0,18 C1.6,13 3.4,6 2.6,0 Z" fill="url(#ssAlev)"/>
   <path d="M-1.2,0 C-1.5,4 -0.7,7 0,9.5 C0.7,7 1.5,4 1.2,0 Z" fill="#fff" opacity="0.85"/></g></g></g>
  <path d="M-2.6,0 L-3,1.8 L-1,1.8 L-0.9,0 Z M0.9,0 L1,1.8 L3,1.8 L2.6,0 Z" fill="#2a2d33"/>
  <path d="M3.4,-9 L7.4,-5.2 L7.4,-0.6 L3.4,-0.6 Z M-3.4,-9 L-7.4,-5.2 L-7.4,-0.6 L-3.4,-0.6 Z" fill="#25282e"/>
  <path d="M-3.5,0 L-3.5,-33 C-3.5,-38.5 -1.8,-42.6 0,-44.2 C1.8,-42.6 3.5,-38.5 3.5,-33 L3.5,0 Z" fill="url(#ssCelik)"/>
  <path d="M-3.5,0 L-3.5,-33 C-3.5,-38.2 -2.4,-41.6 -1.1,-43.3 L-1.1,0 Z" fill="#16181d" opacity="0.94"/>
  <path d="{kaynak}" stroke="#7d838c" stroke-width="0.25" opacity="0.6"/>
  <path d="M1.4,-1 V-38" stroke="#fff" stroke-width="0.5" opacity="0.5"/>
  <path d="M3.2,-36.5 L6,-34 L6,-30 L3.4,-30 Z M-3.2,-36.5 L-6,-34 L-6,-30 L-3.4,-30 Z" fill="#23262c"/>
 </g></g></g>
 <g transform="translate(486 166) rotate(24)">
  <ellipse rx="3" ry="2" fill="#ffb347" opacity="0" filter="url(#isik)">{degistir("rx", [(4.9, 3), (5.5, 20, "0.2 0.6 0.4 1")])}{degistir("ry", [(4.9, 2), (5.5, 6)])}{gorun([(4.88, 0), (4.96, 1), (5.8, 0)])}</ellipse>
  <circle r="2" fill="url(#parlama)" opacity="0">{degistir("r", [(4.9, 2), (5.4, 14)])}{gorun([(4.88, 0), (4.96, 1), (5.5, 0)])}</circle>
 </g>
</g>'''

    # 7. Halley · 1986 · sıradaki 2061
    def halley(self) -> str:
        return f'''<defs>
  <linearGradient id="hlIyon" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#c4e8ff" stop-opacity="0.95"/><stop offset="0.25" stop-color="#7cc4ff" stop-opacity="0.6"/><stop offset="1" stop-color="#3a7bff" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="hlToz" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#fff6dc" stop-opacity="0.85"/><stop offset="0.35" stop-color="#f3d79a" stop-opacity="0.45"/><stop offset="1" stop-color="#e8b866" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="hlKoma" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff"/><stop offset="0.2" stop-color="#e8f6ff" stop-opacity="0.9"/><stop offset="0.55" stop-color="#9fd0ff" stop-opacity="0.3"/><stop offset="1" stop-color="#9fd0ff" stop-opacity="0"/>
  </radialGradient>
  <filter id="hlBulan" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="1.4"/></filter>
</defs>
<g opacity="0">{gorun([(0, 0), (1.8, 1), (10.0, 1), (11.8, 0)])}
<g>{tasi([(0, "560 56"), (12, "100 34", DUZ)])}
 <g>{dondur([(0, -5), (12, 4, DUZ)])}
  <path d="M0,-3 C50,-4 110,2 172,22 L174,46 C110,27 50,10 0,4 Z" fill="url(#hlToz)" filter="url(#hlBulan)"/>
  <path d="M0,-1.8 L215,-13 L215,-4 L0,1.8 Z" fill="url(#hlIyon)" filter="url(#hlBulan)"/>
  <path d="M2,-0.5 L205,-15 M2,0.6 L190,-1.5 M2,0 L160,-8" stroke="#bfe4ff" stroke-width="0.45" opacity="0.4"/>
  <circle r="11" fill="url(#hlKoma)"/>
  <circle r="1.7" fill="#fff" filter="url(#isik)"/>
 </g>
 <g opacity="0">{gorun([(2.0, 0), (2.8, 1), (10.0, 1), (11.4, 0)])}{etiket("HALLEY", -6, 30, "start", alt="son geçiş 1986, dönüş 2061")}</g>
</g></g>'''

    # 8. Büyük Ayı birleşir, Kuzey Yıldızı parlar
    def buyukayi(self) -> str:
        kx, ky = KUTUP
        yer, kenar = self.buyuk_ayi_yerleri()
        dubhe = yer["dubhe"]
        s0 = 0.4
        parca = [f'<g stroke="#b9d3ff" stroke-width="1.1" stroke-linecap="round" opacity="0">'
                 + gorun([(s0, 0), (s0 + 0.05, 0.85), (s0 + 6.4, 0.85), (s0 + 7.4, 0)])]
        for k, ((x1, y1), (x2, y2)) in enumerate(kenar):
            L = math.dist((x1, y1), (x2, y2))
            ciz = [(s0 + 0.3 * k, round(L)), (s0 + 0.3 * k + 0.35, 0)]
            parca.append(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke-dasharray="{L:.0f}" '
                         f'stroke-dashoffset="{L:.0f}">{degistir("stroke-dashoffset", ciz)}</line>')
        isaret = "".join(degistir(e, [(s0 + 2.3, f(a)), (s0 + 3.2, f(b))]) for e, a, b in (("x2", dubhe[0], kx), ("y2", dubhe[1], ky)))
        parca.append(f'<line x1="{f(dubhe[0])}" y1="{f(dubhe[1])}" x2="{f(dubhe[0])}" y2="{f(dubhe[1])}" stroke="#dbe7ff" '
                     f'stroke-dasharray="3 3.5" stroke-width="1.2">{isaret}</line></g>')
        dalga = degistir("r", [(s0 + 3.2, 4), (s0 + 4.4, 70, "0.2 0.6 0.4 1")])
        dalga_op = gorun([(s0 + 3.15, 0), (s0 + 3.25, 0.9), (s0 + 4.4, 0)])
        parca.append(f'<circle cx="{kx}" cy="{ky}" r="4" fill="none" stroke="#cfe6ff" stroke-width="1.4" opacity="0">{dalga}{dalga_op}</circle>')
        return "\n".join(parca)

    # 9. 2001: Bir Uzay Destanı · 1968
    def monolit(self) -> str:
        X = 500
        hiza = 6.0
        isinlar = "".join(f'<rect x="-{L}" y="-0.35" width="{2 * L}" height="0.7" fill="url(#civi)" transform="rotate({a})"/>'
                          for a, L in ((0, 58), (30, 34), (60, 46), (90, 40), (120, 30), (150, 44)))
        return f'''<defs>
  <radialGradient id="mnGunes" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.14" stop-color="#fff4d0" stop-opacity="0.95"/><stop offset="0.45" stop-color="#ffd27a" stop-opacity="0.35"/><stop offset="1" stop-color="#ffb347" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="mnAy" cx="0.5" cy="0.2" r="0.85">
    <stop offset="0" stop-color="#f4f3ee"/><stop offset="0.42" stop-color="#a7a6a0"/><stop offset="1" stop-color="#1f1f23"/>
  </radialGradient>
  <radialGradient id="mnGezegen" cx="0.5" cy="0.02" r="0.86">
    <stop offset="0" stop-color="#c4e2ff"/><stop offset="0.3" stop-color="#4f86e0"/><stop offset="0.62" stop-color="#13224a"/><stop offset="1" stop-color="#060a16"/>
  </radialGradient>
  <linearGradient id="mnKenar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f2f5ff"/><stop offset="0.5" stop-color="#8f9bc4" stop-opacity="0.6"/><stop offset="1" stop-color="#4a5478" stop-opacity="0.25"/>
  </linearGradient>
  <linearGradient id="mnIsik" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff4d0" stop-opacity="0.32"/><stop offset="1" stop-color="#fff4d0" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="mnGolge" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#03020a" stop-opacity="0.75"/><stop offset="1" stop-color="#03020a" stop-opacity="0"/></radialGradient>
</defs>
<g opacity="0">{gorun([(0, 0), (0.6, 1), (10.8, 1), (11.8, 0)])}
 <ellipse cx="{X}" cy="150" rx="70" ry="110" fill="url(#mnGolge)"/>
 <path d="M{X - 6},76 L{X - 15},166 L{X + 15},166 L{X + 6},76 Z" fill="url(#mnIsik)" opacity="0">{gorun([(hiza + 0.2, 0), (hiza + 1.0, 1), (9.6, 1), (10.6, 0)])}</path>
 <g>{tasi([(1.0, f"{X + 34} 98"), (hiza, f"{X} 70", "0.3 0 0.3 1")])}
  <g opacity="0">{gorun([(0.6, 0), (2.6, 0.55), (hiza - 0.2, 0.7), (hiza + 0.3, 1)])}
   <circle r="30" fill="url(#mnGunes)"><animate attributeName="r" {cizelge([(hiza - 0.2, 26), (hiza + 0.4, 44, "0.2 0.6 0.4 1"), (9.0, 36)])}/></circle>
   <g opacity="0">{gorun([(hiza - 0.1, 0), (hiza + 0.4, 0.9), (9.4, 0.7), (10.4, 0)])}
    <rect x="-130" y="-0.8" width="260" height="1.6" fill="url(#civi)"/>
    <g>{dondur([(hiza, 0), (11, 22, DUZ)])}{isinlar}</g>
   </g>
   <circle r="4.6" fill="#fff" filter="url(#isik)"/>
  </g>
 </g>
 <g>{tasi([(1.2, f"{X - 50} 112"), (hiza, f"{X} 106", "0.3 0 0.3 1")])}
  <g opacity="0">{gorun([(1.0, 0), (2.6, 1)])}
   <circle r="8.5" fill="url(#mnAy)"/>
   <circle cx="-2.6" cy="-1.6" r="1.4" fill="#000" opacity="0.18"/><circle cx="2.4" cy="1.8" r="1" fill="#000" opacity="0.2"/><circle cx="0.6" cy="-4.4" r="0.8" fill="#000" opacity="0.15"/>
  </g>
 </g>
 <g>{tasi([(1.2, f"{X + 54} 144"), (hiza, f"{X} 140", "0.3 0 0.3 1")])}
  <g opacity="0">{gorun([(1.0, 0), (2.6, 1)])}
   <circle r="15" fill="url(#mnGezegen)"/>
   <path d="M-14.2,-4.8 A15,15 0 0 1 14.2,-4.8" fill="none" stroke="#9fd8ff" stroke-width="1" opacity="0.7" filter="url(#isik)"/>
  </g>
 </g>
 <g>{tasi([(0.3, "0 8"), (1.8, "0 0", "0.2 0.6 0.4 1")])}
  <g opacity="0">{gorun([(0.3, 0), (1.8, 1)])}
   <rect x="{X - 12}" y="166" width="24" height="54" fill="#030306"/>
   <rect x="{X - 9}" y="166" width="3" height="54" fill="#9fb0ff" opacity="0.06"/>
   <rect x="{X - 12}" y="166" width="24" height="54" fill="none" stroke="url(#mnKenar)" stroke-width="0.7"/>
   <rect x="{X - 12}" y="166" width="24" height="54" fill="none" stroke="#fff4d0" stroke-width="0.9" opacity="0" filter="url(#isik)">{gorun([(hiza + 0.1, 0), (hiza + 0.8, 0.9), (9.4, 0.6), (10.4, 0)])}</rect>
  </g>
 </g>
 <g opacity="0">{gorun([(1.8, 0), (2.6, 1)])}{etiket("2001: BİR UZAY DESTANI · 1968", X, 236)}</g>
</g>'''

    # 10. Yıldız Savaşları · 1977: bir yük gemisi ışık hızından çıkar, süzülür, yeniden atlar
    def hiperuzay(self) -> str:
        cx, cy = 560, 172
        r = random.Random(TOHUM + 7)
        cizgiler = []
        for _ in range(120):
            aci, r0 = r.uniform(0, 360), r.uniform(10, 430)
            L = r0 * r.uniform(0.55, 1.05) + 18
            w = 0.5 + 1.2 * (r0 / 430)
            # gelişte uzun çizgiler noktaya toplanır, gidişte yeniden uzar, sonra her şey yerine döner
            uza = [(3.5, f(r0 + L)), (4.6, f(r0), "0 0 0.3 1"), (9.9, f(r0), DUZ), (10.9, f(r0 + L), "0.7 0 1 1"),
                   (12.0, f(r0 + L), DUZ), (13.0, f(r0), "0 0 0.3 1")]
            cizgiler.append(f'<g transform="rotate({aci:.0f})"><line x1="{f(r0)}" y1="0" x2="{f(r0)}" y2="0" stroke-width="{w:.1f}">'
                            f'{degistir("x2", uza)}</line></g>')
        vx, vy = 522, 180                      # geminin ışık hızından çıktığı yer
        gx, gy = 640, 157                      # yeniden atladığı yer
        # gemi: yassı, oval gövde; önde iki çatal, sancakta kokpit tüpü, arkada mavi motor ışığı
        dikis = " ".join(f"M{f(19 * math.cos(math.radians(a)))},{f(7.2 * math.sin(math.radians(a)))} "
                         f"L{f(29.6 * math.cos(math.radians(a)))},{f(11.3 * math.sin(math.radians(a)))}"
                         for a in (35, 70, 110, 150, 210, 250, 290))
        a1 = (f(30 * math.cos(math.radians(138))), f(11.5 * math.sin(math.radians(138))))
        a2 = (f(30 * math.cos(math.radians(222))), f(11.5 * math.sin(math.radians(222))))
        motor = f"M{a1[0]},{a1[1]} A30,11.5 0 0 1 {a2[0]},{a2[1]}"
        catal = "M19,-8.6 L44.5,-6.4 Q47.2,-5.6 46.4,-3.4 L25,-2.8 Z M19,8.6 L44.5,6.4 Q47.2,5.6 46.4,3.4 L25,2.8 Z"
        gemi = f'''<defs>
  <linearGradient id="gmGovde" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f3f5f8"/><stop offset="0.45" stop-color="#c4cad3"/><stop offset="1" stop-color="#737b88"/>
  </linearGradient>
  <radialGradient id="gmMotor" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#e6fbff" stop-opacity="0.95"/><stop offset="0.4" stop-color="#5fd0ff" stop-opacity="0.5"/><stop offset="1" stop-color="#2a7bff" stop-opacity="0"/>
  </radialGradient>
</defs>
<g opacity="0">{gorun([(4.45, 0), (4.5, 1), (10.95, 1), (11.0, 0)])}
<g>{tasi([(4.45, "430 196"), (4.75, f"{vx} {vy}", "0.1 0.8 0.3 1"), (10.3, "612 162", DUZ), (10.75, f"{gx} {gy}", "0.4 0 0.8 0.6"), (11.0, "1200 58", "0.8 0 1 1")])}
 <g transform="rotate(-10)"><g>{dondur([(4.75, 0), (7.6, 3), (10.3, -1)])}<g>{olcekle([(4.45, "7 0.4"), (4.75, "1.25 1.25", "0.1 0.8 0.3 1"), (10.6, "1.25 1.25", DUZ), (10.75, "1.12 1.32"), (11.0, "8 0.5", "0.8 0 1 1")])}
  <ellipse cx="-31" cy="0" rx="9" ry="12" fill="url(#gmMotor)" opacity="0.8">{gorun([(4.6, 0.6), (9.8, 0.7), (10.6, 1)])}</ellipse>
  <path d="{catal}" fill="#3e444f" transform="translate(0 2.2)"/>
  <ellipse cx="0" cy="2.6" rx="30" ry="11.5" fill="#3e444f"/>
  <path d="{catal}" fill="url(#gmGovde)" stroke="#5b626e" stroke-width="0.4"/>
  <ellipse rx="30" ry="11.5" fill="url(#gmGovde)"/>
  <path d="M20.6,-3.4 L29.7,-1.3 L29.7,1.3 L20.6,3.4 Z" fill="#2a2f38"/>
  <ellipse rx="19" ry="7.2" fill="none" stroke="#7d8593" stroke-width="0.45"/>
  <path d="{dikis}" stroke="#7d8593" stroke-width="0.4"/>
  <ellipse rx="7.5" ry="3" fill="#dfe4ea" stroke="#7d8593" stroke-width="0.4"/><ellipse cx="0.6" cy="-0.4" rx="3" ry="1.1" fill="#fff" opacity="0.7"/>
  <g fill="#8a929e" opacity="0.8"><rect x="-17" y="-8.4" width="5" height="2.2"/><rect x="-24" y="2.6" width="4" height="3"/><rect x="9" y="-9.2" width="6" height="1.8"/><rect x="-6" y="7.4" width="7" height="1.8"/></g>
  <path d="M-12,-11 Q10,-11.8 25,-7.2" stroke="#fff" stroke-width="0.7" opacity="0.6" fill="none"/>
  <path d="M6,8.4 L19,14 Q23,15.4 22.4,17.9 Q21.6,19.8 18.6,19 L4.6,12.6 Z" fill="url(#gmGovde)" stroke="#5b626e" stroke-width="0.4"/>
  <path d="M19.4,15.2 L21.8,16.2 M18.4,16.6 L21.2,17.8" stroke="#16202e" stroke-width="1"/>
  <circle cx="21" cy="16.4" r="0.5" fill="#9fe0ff"/>
  <path d="{motor}" fill="none" stroke="#4fc3ff" stroke-width="3" stroke-linecap="round" filter="url(#isik)"/>
  <path d="{motor}" fill="none" stroke="#eafcff" stroke-width="0.9" stroke-linecap="round"/>
 </g></g></g>
</g></g>'''
        return f'''<g opacity="0">{gorun([(0, 0), (0.1, 1), (14.6, 1), (14.9, 0)])}
 <text x="50" y="104" font-family="'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif" font-size="19" font-style="italic" fill="#4bd5ee" letter-spacing="0.4" opacity="0">{gorun([(0.2, 0), (0.9, 1), (2.8, 1), (3.5, 0)])}Çok çok uzak bir galakside…</text>
 <rect width="{W}" height="{H}" fill="#05040d" opacity="0">{gorun([(3.0, 0), (3.6, 0.55), (12.8, 0.55), (14.2, 0)])}</rect>
 <g transform="translate({cx} {cy})" stroke="#dbeaff" stroke-linecap="round" opacity="0">{gorun([(3.2, 0), (3.6, 1), (4.8, 1), (5.8, 0.4), (9.4, 0.4), (9.9, 1), (12.8, 1), (13.8, 0)])}{"".join(cizgiler)}</g>
 <circle cx="{vx}" cy="{vy}" r="4" fill="none" stroke="#cfe6ff" stroke-width="1.2" opacity="0">{degistir("r", [(4.6, 4), (5.8, 120, "0.2 0.6 0.4 1")])}{gorun([(4.55, 0), (4.65, 0.7), (5.8, 0)])}</circle>
 <circle cx="{vx}" cy="{vy}" r="3" fill="url(#parlama)" opacity="0">{degistir("r", [(4.5, 3), (4.9, 44, "0.2 0.6 0.4 1")])}{gorun([(4.48, 0), (4.56, 1), (5.3, 0)])}</circle>
 {gemi}
 <circle cx="{gx + 12}" cy="{gy - 2}" r="3" fill="url(#parlama)" opacity="0">{degistir("r", [(10.9, 3), (11.4, 70, "0.2 0.6 0.4 1")])}{gorun([(10.88, 0), (10.98, 1), (11.8, 0)])}</circle>
 <circle cx="{gx + 12}" cy="{gy - 2}" r="4" fill="none" stroke="#cfe6ff" stroke-width="1.2" opacity="0">{degistir("r", [(11.0, 4), (12.2, 180, "0.2 0.6 0.4 1")])}{gorun([(10.95, 0), (11.05, 0.7), (12.2, 0)])}</circle>
 <rect width="{W}" height="{H}" fill="#e6f0ff" opacity="0">{gorun([(10.9, 0), (11.0, 0.25), (11.7, 0)])}</rect>
 <g opacity="0">{gorun([(4.8, 0), (5.4, 1), (12.0, 1), (12.7, 0)])}{etiket("YILDIZ SAVAŞLARI · 1977", 560, 272)}</g>
</g>'''

    # 11. Major Tom · Space Oddity · 1969
    def majortom(self) -> str:
        def uzuv(d: str, w: float) -> str:
            return (f'<path d="{d}" stroke="#7d8593" stroke-width="{w + 1:g}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
                    f'<path d="{d}" stroke="#f3f5f8" stroke-width="{w:g}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
        ip = "M-4,4 C-14,10 -20,-2 -30,2 C-38,5 -42,-2 -48,0"
        yol = [(0, "430 96"), (13, "590 226", "0.35 0 0.65 1")]
        yazi_yolu = [(0, "430 134"), (13, "590 266", "0.35 0 0.65 1")]
        return f'''<defs>
  <linearGradient id="mtVizor" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#ffe29a"/><stop offset="0.4" stop-color="#b9842a"/><stop offset="1" stop-color="#2a1a08"/>
  </linearGradient>
  <linearGradient id="mtKapsul" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#2b3038"/><stop offset="0.45" stop-color="#8f98a6"/><stop offset="1" stop-color="#23272e"/>
  </linearGradient>
</defs>
<g opacity="0">{gorun([(0, 0), (1.2, 1), (11.6, 1), (12.8, 0)])}
 <g>{tasi([(0, "372 58"), (13, "362 53", DUZ)])}<g>{dondur([(0, -24), (13, -10, DUZ)])}<g transform="scale(0.9)">
  <path d="M6,0 C10,2 12,-1 15,1 M15,1 l2.4,-1.4 M15,1 l2.6,0.6 M15,1 l1.6,2" stroke="#d8c79c" stroke-width="0.7" fill="none"/>
  <rect x="-3" y="-10" width="6" height="4.4" fill="#3a3f48"/>
  <path d="M-9,5 L-3.6,-6 L3.6,-6 L9,5 Z" fill="url(#mtKapsul)"/>
  <path d="M-2.6,-3.4 L-0.6,-3.4 L-0.9,-1 L-3.2,-1 Z" fill="#141820"/><circle cx="-1.8" cy="-2.2" r="0.5" fill="#ffd27a"/>
  <path d="M-9.4,5 Q0,8.6 9.4,5" stroke="#6b4a2a" stroke-width="1.6" fill="none"/>
 </g></g></g>
 <g>{tasi(yol)}<g>{olcekle([(0, "0.8 0.8"), (13, "1.15 1.15", "0.35 0 0.65 1")])}<g>{dondur([(0, 20), (13, -150, DUZ)])}
  <path d="{ip}" stroke="#d8c79c" stroke-width="0.8" fill="none"/>
  <path d="M-48,0 l-3,-1.6 M-48,0 l-3.2,0.6 M-48,0 l-2.2,2" stroke="#d8c79c" stroke-width="0.5"/>
  <rect x="-7.8" y="-9.4" width="15.6" height="15" rx="2" fill="#b9c0ca" stroke="#7d8593" stroke-width="0.5"/>
  {uzuv("M-2.6,6 L-4.5,14.5 L-3,21", 4.2)}{uzuv("M2.6,6 L5.5,14 L9,19", 4.2)}
  <circle cx="-3" cy="21.4" r="2.3" fill="#c3c9d2"/><circle cx="9.2" cy="19.4" r="2.3" fill="#c3c9d2"/>
  <rect x="-5.6" y="-9.2" width="11.2" height="16.4" rx="3.5" fill="#f4f6f9" stroke="#8a929f" stroke-width="0.5"/>
  <rect x="-3" y="-5" width="6" height="3.6" rx="0.6" fill="#9aa3b0"/><circle cx="-1.4" cy="-3.2" r="0.6" fill="#e2483d"/><circle cx="0.6" cy="-3.2" r="0.6" fill="#4f9bff"/>
  <path d="M-5.4,2.6 H5.4" stroke="#b8bec8" stroke-width="0.6"/>
  {uzuv("M-4.5,-5.5 L-10,-0.5 L-12,5", 3.6)}{uzuv("M4.5,-5.5 L10.5,-8.5 L13.5,-13", 3.6)}
  <circle cx="-12.2" cy="5.6" r="2" fill="#c3c9d2"/><circle cx="13.8" cy="-13.6" r="2" fill="#c3c9d2"/>
  <circle cx="0" cy="-13.8" r="5.4" fill="#f6f8fb" stroke="#8a929f" stroke-width="0.5"/>
  <ellipse cx="0.9" cy="-13.6" rx="3.6" ry="3" fill="url(#mtVizor)"/>
  <path d="M-1.2,-15.2 Q0.6,-16.2 2.4,-15.4" stroke="#fff" stroke-width="0.6" opacity="0.85" fill="none"/>
 </g></g></g>
 <g>{tasi(yazi_yolu)}<g opacity="0">{gorun([(1.5, 0), (2.3, 1), (10.6, 1), (11.4, 0)])}{etiket("MAJOR TOM", alt="Space Oddity, 1969")}</g></g>
</g>'''

    # 12. Türksat 6A · 2024
    def turksat(self) -> str:
        def kanat(yon: int) -> str:
            parca = []
            for i in range(3):
                x0 = 17 + i * 15.4
                x = -(x0 + 14.6) if yon < 0 else x0
                cizgi = " ".join(f"M{f(x + 3.65 * k)},-7 V7" for k in range(1, 4)) + f" M{f(x)},0 H{f(x + 14.6)}"
                parca.append(f'<rect x="{f(x)}" y="-7" width="14.6" height="14" fill="url(#tsPanel)" stroke="#c9ced6" stroke-width="0.5"/>'
                             f'<path d="{cizgi}" stroke="#6f86cc" stroke-width="0.3" opacity="0.8"/>')
            return "".join(parca)
        yildiz = " ".join(f"{f(2.3 + (1.35 if k % 2 == 0 else 0.55) * math.cos(math.radians(-90 + 36 * k)))},"
                          f"{f(-0.2 + (1.35 if k % 2 == 0 else 0.55) * math.sin(math.radians(-90 + 36 * k)))}" for k in range(10))
        halka = "".join(f'<circle cx="-6" cy="17" r="4" fill="none" stroke="#9fe7ff" stroke-width="0.9" opacity="0">'
                        f'{degistir("r", [(t, 4), (t + 1.6, 46, "0.2 0.6 0.4 1")])}{gorun([(t - 0.02, 0), (t, 0.85), (t + 1.6, 0)])}</circle>'
                        for t in (5.0, 5.8))
        yol = [(0, "230 322"), (12, "660 -40", DUZ)]
        return f'''<defs>
  <linearGradient id="tsAltin" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#f8dc84"/><stop offset="0.5" stop-color="#c8962e"/><stop offset="1" stop-color="#6e4c12"/>
  </linearGradient>
  <linearGradient id="tsPanel" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#3a52a8"/><stop offset="0.55" stop-color="#1d2a62"/><stop offset="1" stop-color="#111a3d"/>
  </linearGradient>
</defs>
<g opacity="0">{gorun([(0, 0), (0.3, 1), (11.6, 1), (12, 0)])}
<g>{tasi(yol)}
 <g opacity="0">{gorun([(2.0, 0), (2.8, 1), (9.0, 1), (9.8, 0)])}
  {etiket("TÜRKSAT 6A · 2024", 76, -2, "start", alt="ilk yerli haberleşme uydumuz")}
 </g>
 <g>{dondur([(0, -14), (12, -4, DUZ)])}<g transform="scale(1.1)">
  {halka}
  <path d="M-17,0 H-11 M11,0 H17" stroke="#aab2be" stroke-width="1.2"/>
  {kanat(-1)}{kanat(1)}
  <path d="M-6,11 V15.4 M8,-15 V-17.6" stroke="#aab2be" stroke-width="0.7"/>
  <path d="M-11,-11 L-6,-15 L16,-15 L11,-11 Z" fill="#e3e7ec"/>
  <path d="M11,-11 L16,-15 L16,7 L11,11 Z" fill="#8a6a26"/>
  <rect x="-11" y="-11" width="22" height="22" fill="url(#tsAltin)"/>
  <path d="M-9,-6 L-3,-8 M4,8 L9,5 M-8,6 L-4,9" stroke="#fff3c4" stroke-width="0.4" opacity="0.6"/>
  <rect x="-6.5" y="-4.5" width="13" height="8.6" fill="#e30a17" stroke="#fff" stroke-width="0.35"/>
  <circle cx="-1.6" cy="-0.2" r="2.6" fill="#fff"/><circle cx="-0.9" cy="-0.2" r="2.1" fill="#e30a17"/>
  <polygon points="{yildiz}" fill="#fff"/>
  <ellipse cx="-6" cy="17" rx="9" ry="3.6" fill="#eef1f5" stroke="#9aa3b0" stroke-width="0.4"/>
  <ellipse cx="-6" cy="16.4" rx="6" ry="2" fill="#cfd5dd"/><circle cx="-6" cy="15.4" r="0.9" fill="#6f7886"/>
  <ellipse cx="8" cy="-18.4" rx="6.5" ry="2.6" fill="#eef1f5" stroke="#9aa3b0" stroke-width="0.4"/><circle cx="8" cy="-19" r="0.7" fill="#6f7886"/>
 </g></g>
</g></g>'''

    # 13. Project Hail Mary · 2026: Tau Ceti'de Hail Mary ile Rocky'nin ksenonit gemisi Blip-A buluşur
    def hailmary(self) -> str:
        """Hail Mary filmdeki düzeniyle: önde büyük mürettebat bölümü, kafes omurga, uydu tipi güneş kanatları,
        üç yakıt tankı, arkada Petrova ışığıyla yanan spin sürücüleri. Buluşmadan sonra mürettebat bölümü omurgadan
        ayrılır, kablolarla açılır, yan döner ve bütün gemi santrifüj olarak döner.
        Blip-A romandaki tarifle: piramit burun, dört panelli ince sap, elmas sekizyüzlü gövde, üç kalın çubuk,
        geniş yamuk taban; benekli gri-bej ksenonit, penceresiz, Hail Mary'nin iki katından büyük.
        Eridyanca konuşma akordur: küçük porte üstünde renkli üç nota; Rocky konuşurken gemisinin telleri parlar."""
        gel = "0.2 0.6 0.35 1"

        def akor(x: float, y: float, t: float, renkler: tuple, yukari: float = -16) -> str:
            porte = " ".join(f"M-8,{f(-4.4 + 2.2 * i)} H8" for i in range(5))
            bas = "".join(f'<ellipse cx="{f(-0.4 + (1.6 if i == 1 else 0))}" cy="{f(3.3 - 3.3 * i)}" rx="1.7" ry="1.15" '
                          f'fill="{r}" transform="rotate(-20 {f(-0.4 + (1.6 if i == 1 else 0))} {f(3.3 - 3.3 * i)})"/>'
                          for i, r in enumerate(renkler))
            return (f'<g transform="translate({f(x)} {f(y)})" opacity="0">{gorun([(t, 0), (t + 0.25, 1), (t + 1.3, 1), (t + 1.9, 0)])}'
                    f'<g>{tasi([(t, "0 0"), (t + 1.9, f"0 {f(yukari)}", "0.2 0.6 0.4 1")])}<g transform="scale(2.1)">'
                    f'<path d="{porte}" stroke="#9fb0d6" stroke-width="0.35" opacity="0.65"/>'
                    f'<path d="M2.6,-0.6 V-11" stroke="#dfe7ff" stroke-width="0.5"/>'
                    f'<g filter="url(#isik)">{bas}</g></g></g></g>')

        # ---- Hail Mary (burun +x yönünde) ----
        E = 14                                     # santrifüjde her iki yarının açıldığı uzaklık
        ac, don = (8.2, 9.4), (9.4, 10.2)
        izgara = " ".join(f"M-19,{f(y)} H-10" for y in (-27, -23, -19, -15, -11)) + " M-14.5,-31 V-7"
        izgara += " " + " ".join(f"M-19,{f(-y)} H-10" for y in (-27, -23, -19, -15, -11)) + " M-14.5,31 V7"
        tank = lambda y, h: (f'<rect x="-43" y="{f(y)}" width="20" height="{f(h)}" rx="{f(h / 2)}" fill="url(#hmTank)"/>'
                             f'<rect x="-35.5" y="{f(y)}" width="2.6" height="{f(h)}" fill="url(#hmAltin)"/>'
                             f'<path d="M-41,{f(y + h * 0.28)} H-25" stroke="#fff" stroke-width="0.45" opacity="0.6"/>')
        motor = titres(0, 4.6, 0.16, 0.8, 1)
        motor[-1] = (4.6, 0, "0.4 0 0.6 1")
        surucu = "".join(f'<circle cx="-45.4" cy="{f(y)}" r="0.55" fill="#ff7a5c"/>' for y in range(-8, 9, 2))
        arka = f'''<g>{tasi([(ac[0], "0 0"), (ac[1], f"{-E} 0")])}
    <ellipse cx="-53" cy="0" rx="10" ry="11" fill="url(#hmPetrova)" opacity="0">{gorun(motor)}</ellipse>
    <path d="M-14.5,-4 V-7 M-14.5,4 V7" stroke="#aab2be" stroke-width="0.8"/>
    <rect x="-19" y="-31" width="9" height="24" fill="url(#hmPanel)" stroke="#c9a55a" stroke-width="0.45"/>
    <rect x="-19" y="7" width="9" height="24" fill="url(#hmPanel)" stroke="#c9a55a" stroke-width="0.45"/>
    <path d="{izgara}" stroke="#7c93d8" stroke-width="0.28" opacity="0.8"/>
    <path d="M-24,-1.6 H-2 M-24,1.6 H-2" stroke="#b8c0cc" stroke-width="0.6"/>
    <path d="M-24,-1.6 L-20,1.6 L-16,-1.6 L-12,1.6 L-8,-1.6 L-4,1.6 L-2,-1.6" stroke="#8a929f" stroke-width="0.45" fill="none"/>
    {tank(-10.6, 6.6)}{tank(4, 6.6)}{tank(-4.6, 9.2)}
    <rect x="-24.6" y="-11.6" width="2.2" height="23.2" rx="0.8" fill="#8a929f"/>
    <rect x="-46.4" y="-10" width="3.6" height="20" rx="1" fill="#2f343c"/>
    <g opacity="0.35">{gorun([(0, 1), (4.6, 1, DUZ), (5.2, 0.35)])}{surucu}</g>
    <rect x="-2" y="-3.4" width="8" height="6.8" rx="1" fill="url(#nozul)"/>
    <path d="M6,-3.4 V3.4" stroke="#20242b" stroke-width="0.8"/>
   </g>'''
        kablo = "".join(f'<line x1="6" y1="{y}" x2="6" y2="{y}" stroke="#d9dee6" stroke-width="0.45">'
                        f'{degistir("x1", [(ac[0], 6), (ac[1], 6 - E)])}'
                        f'{degistir("x2", [(ac[0], 6), (ac[1], 6 + E), (don[0], 6 + E, DUZ), (don[1], 25)])}</line>'
                        for y in (-2.4, 2.4))
        on = f'''<g opacity="0">{gorun([(ac[0], 0), (ac[0] + 0.1, 1)])}{kablo}</g>
   <g transform="translate(19 0)">{tasi([(ac[0], "19 0"), (ac[1], f"{19 + E} 0")])}<g>{dondur([(don[0], 0), (don[1], 90)])}
    <path d="M-13,-8 H5 Q13,-7.4 16,-3 L16,3 Q13,7.4 5,8 H-13 Z" fill="url(#hmBeyaz)"/>
    <rect x="-13" y="-8" width="3.4" height="16" fill="url(#hmAltin)"/>
    <path d="M-4,-8 V8 M3,-8 V8" stroke="#9aa3b0" stroke-width="0.4"/>
    <path d="M-9.6,-6.5 H5 Q10.5,-6.1 13.6,-3.4" stroke="#fff" stroke-width="0.6" opacity="0.7" fill="none"/>
    <rect x="8.4" y="-4.6" width="3" height="1.9" rx="0.5" fill="#16202e"/><rect x="8.4" y="2.7" width="3" height="1.9" rx="0.5" fill="#16202e"/>
    <circle cx="9.4" cy="-3.9" r="0.45" fill="#ffd27a"/>
    <rect x="16" y="-2.4" width="2.4" height="4.8" rx="0.6" fill="#8a929e" stroke="#4f5766" stroke-width="0.3"/>
   </g></g>'''
        insan_yol = [(0, "372 350"), (4.8, "522 152", gel)]
        insan_yon = [(0, -48), (4.8, -12, gel), (don[1], -10, DUZ), (14, 250, "0.55 0 0.75 1")]

        # ---- Blip-A (burun -x yönünde) ----
        tel_x = (27, 32, 37, 42)
        tel = lambda renk, w: "".join(f'<path d="M{x},{f(-11 - (x - 8) * 8 / 42 + 2)} V{f(11 + (x - 8) * 8 / 42 - 2)}" '
                                      f'stroke="{renk}" stroke-width="{w}"/>' for x in tel_x)
        konus = [5.0, 5.9, 7.6]
        tel_parla = gorun([nk for t in konus for nk in [(t - 0.02, 0), (t + 0.05, 1), (t + 0.8, 0)]])
        cubuk = lambda d: (f'<path d="{d}" stroke="#4a443a" stroke-width="5.4" stroke-linecap="round"/>'
                           f'<path d="{d}" stroke="#8f8471" stroke-width="3.8" stroke-linecap="round"/>'
                           f'<path d="{d}" stroke="#c4b799" stroke-width="0.8" stroke-linecap="round" opacity="0.6" transform="translate(0 -1)"/>')
        govde_ss = ('<path d="M-76,0 L-63,-6.5 L-63,6.5 Z"/><rect x="-63" y="-2" width="34" height="4"/>'
                    '<path d="M-32,0 L-6,-23 L20,0 L-6,23 Z"/><path d="M48,-20 L64,-30 L68,-29 L68,29 L64,30 L48,20 Z"/>')
        blip = f'''<g>
    <ellipse cx="76" cy="0" rx="12" ry="26" fill="url(#hmPetrova)" opacity="0">{gorun([(0, 0.9), (3.4, 0.9, DUZ), (5.0, 0)])}</ellipse>
    <path d="M-56,-2 L-43,-2 L-48,-18 L-60,-18 Z" fill="#5c5446" stroke="#a89c82" stroke-width="0.35"/>
    <path d="M-56,2 L-43,2 L-48,18 L-60,18 Z" fill="#4a443a" stroke="#a89c82" stroke-width="0.35"/>
    {cubuk("M8,-11 L50,-19")}{cubuk("M18,0 L50,0")}{cubuk("M8,11 L50,19")}
    <g opacity="0.55">{tel("#e9dcc0", 0.35)}</g>
    <g opacity="0" filter="url(#isik)">{tel_parla}{tel("#ffd9a0", 0.6)}</g>
    <path d="M-63,-2 H-29 V2 H-63 Z" fill="#8a7f6c"/>
    <path d="M-63,-1.6 H-30" stroke="#d2c6a8" stroke-width="0.5" opacity="0.7"/>
    <path d="M-76,0 L-63,-6.5 L-63,0 Z" fill="#c2b597"/><path d="M-76,0 L-63,6.5 L-63,0 Z" fill="#6c6454"/>
    <path d="M-53,-2 L-41,-2 L-38,-11 L-49,-11 Z" fill="#9a8f78" stroke="#d2c6a8" stroke-width="0.35"/>
    <path d="M-53,2 L-41,2 L-38,11 L-49,11 Z" fill="#7a705f" stroke="#d2c6a8" stroke-width="0.35"/>
    <path d="M-32,0 L-6,-23 L-3,3 Z" fill="#c4b698"/><path d="M-6,-23 L20,0 L-3,3 Z" fill="#9a8f79"/>
    <path d="M20,0 L-6,23 L-3,3 Z" fill="#5b5448"/><path d="M-6,23 L-32,0 L-3,3 Z" fill="#776d5c"/>
    <path d="M-32,0 L-6,-23 L20,0 L-6,23 Z M-6,-23 L-3,3 L-32,0 M-3,3 L20,0 M-3,3 L-6,23" fill="none" stroke="#d8ccae" stroke-width="0.4" stroke-linejoin="round" opacity="0.75"/>
    <path d="M48,-20 L64,-30 L64,30 L48,20 Z" fill="url(#blTaban)"/>
    <path d="M64,-30 L68,-29 L68,29 L64,30 Z" fill="#3e392f"/>
    <path d="M48,-20 L64,-30 L68,-29 M48,-8 H64 M48,8 H64" stroke="#d2c6a8" stroke-width="0.4" fill="none" opacity="0.7"/>
    <g fill="#000" opacity="0.45" filter="url(#blBenek)">{govde_ss}</g>
    <path d="M-27,-1.2 L-7,-18.6 M-24,2.2 L-7,17.4 M15,-1.6 L-2,-16 M-61,0 H-31 M51,-15 L62,-22 V22 L51,15" stroke="#2e2a23" stroke-width="0.55" stroke-dasharray="1.4 1" fill="none" opacity="0.8"/>
   </g>'''
        blip_yol = [(0, "1000 96"), (5.0, "724 124", gel), (14, "714 127", DUZ)]

        tau = (f'<g opacity="0">{gorun([(0.2, 0), (1.6, 1), (12.6, 1), (13.6, 0)])}'
               f'<circle cx="826" cy="40" r="16" fill="url(#hmTau)"/><circle cx="826" cy="40" r="2" fill="#fff1cf"/>'
               f'{etiket("TAU CETI", 826, 62, boyut=13, renk="#b4c1e4")}</g>')
        return f'''<defs>
  <linearGradient id="hmBeyaz" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.5" stop-color="#dfe4ea"/><stop offset="1" stop-color="#848d9b"/>
  </linearGradient>
  <linearGradient id="hmTank" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#e9edf2"/><stop offset="0.5" stop-color="#aab2be"/><stop offset="1" stop-color="#555d6a"/>
  </linearGradient>
  <linearGradient id="hmAltin" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffe7a3"/><stop offset="0.5" stop-color="#c9932f"/><stop offset="1" stop-color="#6e4c12"/>
  </linearGradient>
  <linearGradient id="hmPanel" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#3a52a8"/><stop offset="0.55" stop-color="#1d2a62"/><stop offset="1" stop-color="#111a3d"/>
  </linearGradient>
  <radialGradient id="hmPetrova" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffd0c4"/><stop offset="0.25" stop-color="#ff5a3c" stop-opacity="0.85"/><stop offset="0.6" stop-color="#b3122e" stop-opacity="0.35"/><stop offset="1" stop-color="#6a0a2a" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="blTaban" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#bcae90"/><stop offset="0.5" stop-color="#857a66"/><stop offset="1" stop-color="#4a443a"/>
  </linearGradient>
  <radialGradient id="hmTau" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffe2a8" stop-opacity="0.55"/><stop offset="0.4" stop-color="#ffbe6a" stop-opacity="0.16"/><stop offset="1" stop-color="#ffbe6a" stop-opacity="0"/>
  </radialGradient>
  <filter id="blBenek" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.32" numOctaves="2" seed="11"/>
    <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.6 1.5"/>
    <feComposite in2="SourceAlpha" operator="in"/>
  </filter>
</defs>
<g opacity="0">{gorun([(0, 0), (0.5, 1), (13.0, 1), (13.8, 0)])}
 {tau}
 <g>{tasi(blip_yol)}<g>{dondur([(0, 5), (5.0, -1, gel), (14, -2, DUZ)])}<g transform="scale(1.1)">
  {blip}
 </g></g></g>
 <g>{tasi(insan_yol)}<g>{dondur(insan_yon)}<g transform="scale(1.05)">
  {arka}
  {on}
 </g></g></g>
 {akor(652, 92, konus[0], ("#ff9a52", "#ffd36e", "#c59bff"))}
 {akor(676, 84, konus[1], ("#7dffb8", "#ff9a52", "#ffd36e"))}
 {akor(546, 116, 6.8, ("#8fd8ff", "#f1f4ff", "#8fd8ff"))}
 {akor(660, 90, konus[2], ("#ffd36e", "#7dffb8", "#ff7ac8"))}
 <g opacity="0">{gorun([(2.4, 0), (3.2, 1), (12.0, 1), (12.8, 0)])}{etiket("PROJECT HAIL MARY · 2026", 620, 264)}</g>
</g>'''

    # 14. Interstellar · 2014: Gargantua ve ona spiral çizerek yaklaşan Endurance, dışarıdaki bizim gözümüzle
    def interstellar(self) -> str:
        """Genel görelilik dışarıdan bakana göre: gemi deliğe yaklaştıkça bize göre yavaşlar (yol hızı ve kendi dönüşü),
        ışığı kırmızıya kayar ve sönükleşir, işaret ışığının yanıp sönmesi seyrekleşir; olay ufkunun hemen dışında donmuş
        gibi kalıp kararır, hiç hızlanmaz. Toplanma diski Doppler'le parlar: bize yaklaşan sol yan mavimsi beyaz ve parlak,
        uzaklaşan sağ yan sönük turuncu-kırmızı; diskin arka yüzü bükülüp gölgenin üstünden ve altından yay olarak görünür."""
        bx, by, egim = 688, 144, -6
        RG = 25                                     # gölge yarıçapı
        T0, T1 = 1.0, 11.8                          # yol boyunca hareketin başı ve donduğu an
        K, R0, R1, TUR = 0.34, 300.0, 34.0, 550.0   # yörünge basıklığı, ilk ve son yarıçap, toplam dönüş (derece)

        def nokta(u: float) -> tuple[float, float, float]:
            r = R1 + (R0 - R1) * (1 - u) ** 1.5
            th = math.radians(-TUR * u)            # açı azalır: sol yan bize doğru gelir, diskle aynı yönde
            return r * math.cos(th), K * r * math.sin(th), r
        orn = [nokta(i / 400) for i in range(401)]
        boy = [0.0]
        for a, b in zip(orn, orn[1:]):
            boy.append(boy[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        yol = "M" + " L".join(f"{f(x)},{f(y)}" for x, y, _ in orn[::4])

        def yaricap(s: float) -> float:            # yolun kesrinden yarıçap
            hedef = s * boy[-1]
            i = next((k for k, L in enumerate(boy) if L >= hedef), len(boy) - 1)
            return orn[i][2]
        anlar = [T0 + (T1 - T0) * (i / 36) for i in range(37)]
        kesir = [1 - (1 - (t - T0) / (T1 - T0)) ** 3 for t in anlar]   # hız (1-v)^2 ile hep azalır, sonda sıfır
        hareket = [(round(t, 3), round(s, 5), DUZ) for t, s in zip(anlar, kesir)]
        buyukluk = [0.75 + 0.85 * (yaricap(s) - R1) / (R0 - R1) for s in kesir]   # uzakta büyük, delikte küçük
        olcek = [(round(t, 3), f"{b:.3f} {b:.3f}", DUZ) for t, b in zip(anlar, buyukluk)]
        donus = [(round(t, 3), round(-620 * s, 1), DUZ) for t, s in zip(anlar, kesir)]
        renk = [(T0, "#e4e9f1"), (6.0, "#ebe6df"), (8.2, "#ffbe94"), (9.6, "#ee6a48"), (10.7, "#b8261c"),
                (11.6, "#5c0c0a"), (12.8, "#1a0303")]
        isaret_an, t, ara = [], 1.6, 0.42           # işaret ışığı: bize göre giderek seyrek yanar
        while t < 12.4:
            isaret_an.append(round(t, 2)); t += ara; ara *= 1.33
        isaret = gorun([nk for t in isaret_an for nk in [(t, 0, DUZ), (t + 0.05, 1, DUZ), (t + 0.32, 0)]])
        moduller = "".join(f'<rect x="-2.4" y="-12.6" width="4.8" height="3.4" rx="0.5" fill="currentColor" '
                           f'fill-opacity="{1 if i % 2 == 0 else 0.62}" stroke="#000" stroke-opacity="0.35" stroke-width="0.3" '
                           f'transform="rotate({30 * i})"/>' for i in range(12))
        on_disk = "M-100,0 A100,12 0 0 0 100,0"
        arka_disk = "M-100,0 A100,12 0 0 1 100,0"
        # diskin arka yüzünün bükülmüş görüntüleri: gölgeyi üstten kalın, alttan ince saran hilaller
        ust_yay = "M-74,0 C-60,-3 -54,-43 0,-43 C54,-43 60,-3 74,0 L28,0 C28,-16 16,-28 0,-28 C-16,-28 -28,-16 -28,0 Z"
        ust_ic = "M-28.6,0 C-28.6,-16.4 -16.4,-28.6 0,-28.6 C16.4,-28.6 28.6,-16.4 28.6,0"
        alt_yay = "M-36,0 C-34,17 -19,32.5 0,32.5 C19,32.5 34,17 36,0 L27.4,0 C27.4,15 15,27.4 0,27.4 C-15,27.4 -27.4,15 -27.4,0 Z"
        return f'''<defs>
  <radialGradient id="isHale" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffe3b8" stop-opacity="0.32"/><stop offset="0.45" stop-color="#ff9e4a" stop-opacity="0.1"/><stop offset="1" stop-color="#ff9e4a" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="isDisk" gradientUnits="userSpaceOnUse" x1="-104" y1="0" x2="104" y2="0">
    <stop offset="0" stop-color="#bcd4ff" stop-opacity="0"/><stop offset="0.1" stop-color="#d6e6ff" stop-opacity="0.9"/><stop offset="0.32" stop-color="#f6f9ff"/>
    <stop offset="0.52" stop-color="#ffeccc" stop-opacity="0.85"/><stop offset="0.74" stop-color="#ff9446" stop-opacity="0.45"/>
    <stop offset="0.92" stop-color="#b8361a" stop-opacity="0.22"/><stop offset="1" stop-color="#b8361a" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="isYay" gradientUnits="userSpaceOnUse" x1="-68" y1="0" x2="68" y2="0">
    <stop offset="0" stop-color="#cfe0ff" stop-opacity="0.35"/><stop offset="0.22" stop-color="#e8f0ff"/><stop offset="0.42" stop-color="#fbfcff"/>
    <stop offset="0.6" stop-color="#ffe2b4" stop-opacity="0.8"/><stop offset="0.82" stop-color="#ff8a40" stop-opacity="0.42"/><stop offset="1" stop-color="#b8361a" stop-opacity="0.15"/>
  </linearGradient>
  <filter id="isBulanik" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.6"/></filter>
  <mask id="isGolge" maskUnits="userSpaceOnUse" x="-500" y="-300" width="1000" height="600">
    <rect x="-500" y="-300" width="1000" height="600" fill="#fff"/><circle r="{RG + 0.5}" fill="#000"/>
  </mask>
</defs>
<g transform="translate({bx} {by}) rotate({egim}) scale(1.15)">
 <g opacity="0">{gorun([(0.2, 0), (2.4, 1), (13.8, 1), (15, 0)])}
  <circle r="86" fill="url(#isHale)"/>
  <path d="{arka_disk}" fill="none" stroke="url(#isDisk)" stroke-width="3.6" opacity="0.55"/>
  <path d="{ust_yay}" fill="url(#isYay)" opacity="0.55" filter="url(#isBulanik)"/>
  <path d="{ust_yay}" fill="url(#isYay)" opacity="0.68"/>
  <path d="{ust_ic}" fill="none" stroke="url(#isYay)" stroke-width="2.4"/>
  <path d="{ust_ic}" fill="none" stroke="#fff8ec" stroke-width="0.6" opacity="0.6"/>
  <path d="{alt_yay}" fill="url(#isYay)" opacity="0.45" filter="url(#isBulanik)"/>
  <path d="{alt_yay}" fill="url(#isYay)" opacity="0.85"/>
  <circle r="{RG}" fill="#000"/>
  <circle r="{RG + 1.4}" fill="none" stroke="url(#isYay)" stroke-width="1.1"/>
  <circle r="{RG + 1.4}" fill="none" stroke="#fff8ec" stroke-width="0.4" opacity="0.7"/>
  <path d="{on_disk}" fill="none" stroke="url(#isDisk)" stroke-width="10" opacity="0.45" filter="url(#isBulanik)"/>
  <path d="{on_disk}" fill="none" stroke="url(#isDisk)" stroke-width="5.2"/>
  <path d="{on_disk}" fill="none" stroke="#fff" stroke-width="1" opacity="0.55"/>
  <path d="{on_disk}" fill="none" stroke="#fff" stroke-width="0.8" stroke-dasharray="6 14" opacity="0.35">{degistir("stroke-dashoffset", [(0, 0), (15, -170, DUZ)])}</path>
 </g>
 <g mask="url(#isGolge)"><g opacity="0">{gorun([(T0, 0), (T0 + 0.3, 1), (13.8, 1), (15, 0)])}
  <g>{yolda(yol, hareket)}<g>{olcekle(olcek)}<g color="#e4e9f1">{degistir("color", renk)}<g transform="rotate(-18)"><g transform="scale(1.5 0.62)"><g>{dondur(donus)}
   <circle r="10.9" fill="none" stroke="currentColor" stroke-opacity="0.85" stroke-width="1.3"/>
   <path d="M-10.9,0 H10.9" stroke="currentColor" stroke-opacity="0.7" stroke-width="0.5"/>
   {moduller}
   <circle r="2.2" fill="currentColor" stroke="#000" stroke-opacity="0.35" stroke-width="0.3"/>
  </g></g></g>
   <circle r="1.4" fill="currentColor" opacity="0" filter="url(#isik)">{isaret}</circle>
  </g></g></g>
 </g></g>
</g>
<g opacity="0">{gorun([(2.6, 0), (3.4, 1), (13.0, 1), (13.8, 0)])}{etiket("INTERSTELLAR · 2014", bx, by + 92)}</g>'''

    # ---------- ışık oyunları ----------
    def isik_oyunlari(self) -> None:
        """Kenarlardan sızan, nefes alır gibi kayan mor ışıklar; sahneyi yavaşça tarayan bir ışık hüzmesi; sinema vinyeti."""
        isiklar = [  # (degrade, merkez yolu, yarıçap, süre, opaklık aralığı)
            ("kenarMor1", "-40,330;60,300;-40,330", (300, 170), 13, "0.55;0.95;0.55"),
            ("kenarMor2", "900,-30;820,10;900,-30", (260, 150), 11, "0.5;0.9;0.5"),
            ("kenarMavi", "440,-60;520,-40;440,-60", (330, 90), 17, "0.4;0.75;0.4"),
            ("kenarMor1", "920,330;860,300;920,330", (240, 130), 15, "0.4;0.8;0.4"),
        ]
        self.durgun_ekle(f'<rect width="{W}" height="{H}" fill="url(#vinyet)"/>', '<g style="mix-blend-mode:screen">')
        for degrade, yol, (rx, ry), sure, op in isiklar:
            (x0, y0), (x1, y1) = (map(float, n.split(",")) for n in yol.split(";")[:2])
            orta = sum(map(float, op.split(";")[:2])) / 2
            self.durgun_ekle(f'<ellipse cx="{f((x0 + x1) / 2)}" cy="{f((y0 + y1) / 2)}" rx="{rx}" ry="{ry}" '
                             f'fill="url(#{degrade})" opacity="{orta:.2f}"/>')
        self.durgun_ekle("</g>")
        # ışık hüzmesi: eğik, geniş, sönük; 24 saniyede bir ekranda yatay kayarak soldan sağa geçer.
        # Kayma dış grupta ekran ekseninde olur (iç dikdörtgen eğik kalır); girişte ve çıkışta opaklıkla yumuşar.
        self.ekle('<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.5;0.58;0.9;0.98;1" '
                  'dur="24s" repeatCount="indefinite"/>'
                  '<animateTransform attributeName="transform" type="translate" values="-170 0;-170 0;1050 0;1050 0" '
                  'keyTimes="0;0.5;0.98;1" dur="24s" repeatCount="indefinite"/>'
                  '<rect x="-80" y="-200" width="160" height="700" fill="url(#huzme)" transform="rotate(24 0 150)"/></g>')

    # ---------- yazı ----------
    def yazi(self) -> None:
        self.ekle('<ellipse cx="160" cy="160" rx="190" ry="70" fill="url(#yaziGolge)"/>',
                  '<g font-family="\'Segoe UI\',Ubuntu,\'Helvetica Neue\',Arial,sans-serif">'
                  '<text x="46" y="152" font-size="48" font-weight="800" fill="#f5f7ff" letter-spacing="0.5">Kuzey Labs</text>'
                  '<text x="49" y="186" font-size="21" font-weight="600" fill="#8cbcff">kuzeylabs.com</text></g>')

    # ---------- parçalar ----------
    def parcala(self) -> tuple[str, list[dict], str]:
        """BAS (açılış, tanımlar, arka plan, roket), ANOMALILER [{ad, sure, svg}], SON (ışık, yazı, kapanış)."""
        self.anomaliler: list[dict] = []
        self.ekle(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
                  'aria-label="Kuzey Labs: Samanyolu, Büyük Ayı ve Kuzey Yıldızı. Açılışta takla atan bir roket geçer; ardından sırası her '
                  'açılışta değişen uzay anları gelir: Sputnik, Apollo 11, Voyager ve Soluk Mavi Nokta, Hubble, Starman, Mars yolunda Starship, '
                  'Halley, 2001 monoliti, Major Tom, Türksat 6A uydusu, ışık hızından çıkıp yeniden atlayan bir yük gemisi, '
                  "Project Hail Mary'deki iki gemi ve Interstellar'ın kara deliği.\">",
                  '<!-- uzay_uret.py ile yordamsal üretildi; elle düzenlenmez -->',
                  f'<clipPath id="kose"><rect width="{W}" height="{H}" rx="16"/></clipPath>')
        self.tanimlar(); tanim = self.parca[-1]; self.ortak_tanimlar()
        self.ekle('<g clip-path="url(#kose)">')
        self.zemin(); self.samanyolu(); self.parlaklar(); self.uydu_izi(); self.takimyildiz(); self.gizli_takimyildizlar()
        self.kayan_yildizlar(); self.roket()
        bas = "\n".join(self.parca) + "\n"
        for ad in SURELER:
            self.anomali(ad, getattr(self, ad))
        self.parca = []
        self.isik_oyunlari(); self.yazi()
        self.ekle("</g>", f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#30363d"/>', "</svg>")
        son = "\n".join(self.parca) + "\n"
        durgun = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
                  + tanim + "".join(self.durgun) + "</svg>")
        resim = f'<image width="{W}" height="{H}" href="{resme_pisir(durgun, ARKA)}"/>'
        assert bas.count(ARKA_YER) == 1
        return bas.replace(ARKA_YER, resim), self.anomaliler, son


# anomaliler ve süreleri (saniye); sıra yalnız ANOMALILER dizisinin sırasıdır, oynama sırası zincirden gelir
SURELER = {"sputnik": 11, "apollo": 13, "voyager": 15, "hubble": 13.5, "starman": 13.5,
           "starship": 14, "halley": 12, "buyukayi": 9, "monolit": 12, "hiperuzay": 15,
           "majortom": 13, "turksat": 12, "hailmary": 14, "interstellar": 15}


ARKA_YER = "<!--ARKA-->"
ARKA = FOTO / "arka-plan.jpg"     # pişmiş arka plan; yanındaki .iz dosyası hangi durgun SVG'den çıktığını tutar
ARKA_CIZIM, ARKA_OLCEK = 2, 1.5   # 2 katta çizilir, 1,5 kata inerek saklanır: telefonda keskin, dosya küçük


def resme_pisir(svg: str, dosya: Path) -> str:
    """Kıpırdamayan çizimi bir kez resme çevirir ve data adresi döndürür. Arka plan (gürültü bulutsu, Samanyolu, uzak
    yıldızlar, kenar ışıkları) JPEG olur; kayan yıldız katmanları saydam PNG. Telefonda takılmanın kaynağı bunlardı:
    süzgeçler ve binlerce daire her karede yeniden çiziliyordu, resim ise neredeyse bedava çizilir.
    SVG değişmediyse eski resim kullanılır; değiştiyse Chrome (playwright) ile yeniden çizilir."""
    import hashlib
    saydam = dosya.suffix == ".png"
    iz = dosya.with_suffix(".iz")
    imza = hashlib.sha256(f"{ARKA_CIZIM}|{ARKA_OLCEK}|{svg}".encode("utf-8")).hexdigest()
    if not (dosya.exists() and iz.exists() and iz.read_text(encoding="utf-8").strip() == imza):
        from io import BytesIO
        from PIL import Image
        from playwright.sync_api import sync_playwright   # yoksa burada açıkça düşer: eski resimle sessizce sürmez
        with sync_playwright() as pw:
            b = pw.chromium.launch(channel="chrome", headless=True)
            s = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=ARKA_CIZIM)
            s.set_content(f"<!doctype html><body style='margin:0;background:{'transparent' if saydam else '#000'}'>{svg}</body>")
            s.wait_for_timeout(300)
            png = s.locator("svg").first.screenshot(omit_background=saydam)
            b.close()
        resim = Image.open(BytesIO(png)).convert("RGBA" if saydam else "RGB")
        resim = resim.resize((int(W * ARKA_OLCEK), int(H * ARKA_OLCEK)), Image.LANCZOS)
        if saydam:
            resim.save(dosya, "PNG", optimize=True)
        else:
            resim.save(dosya, "JPEG", quality=76, optimize=True, progressive=True)
        iz.write_text(imza + "\n", encoding="utf-8")
    tur = "png" if saydam else "jpeg"
    return f"data:image/{tur};base64," + base64.b64encode(dosya.read_bytes()).decode("ascii")


def parcala() -> tuple[str, list[dict], str]:
    return Sahne().parcala()


def birlestir(sira: list[str], araliklar: list[float], parcalar: tuple | None = None) -> str:
    """Worker'ın yaptığının aynısı: ilk anomali roketin ve son anomalinin bitişine, diğerleri bir öncekinin bitişine bağlanır."""
    bas, anomaliler, son = parcalar or parcala()
    sozluk = {a["ad"]: a for a in anomaliler}
    assert sorted(sira) == sorted(sozluk) and len(araliklar) == len(sira)
    govde = []
    for j, ad in enumerate(sira):
        g = f"{araliklar[j]:.1f}"
        basla = f"kroket.end+{g}s;k_{sira[-1]}.end+{g}s" if j == 0 else f"k_{sira[j - 1]}.end+{g}s"
        govde.append(sozluk[ad]["svg"].replace(YER_TUTUCU, basla, 1))
    return bas + "".join(govde) + son


def baslangiclar(sira: list[str], araliklar: list[float], tur: int = 1) -> list[tuple[str, float]]:
    """Zincire göre her anomalinin başladığı saniye (tur kadar döngü)."""
    t, sonuc = ROKET_BASLA + ROKET_SURE, []
    for _ in range(tur):
        for j, ad in enumerate(sira):
            t += round(araliklar[j], 1)
            sonuc.append((ad, round(t, 2)))
            t += SURELER[ad]
    return sonuc


def yedek_sira() -> tuple[list[str], list[float]]:
    r = random.Random(YEDEK_TOHUM)
    sira = list(SURELER)
    r.shuffle(sira)
    return sira, [round(r.uniform(*ARA), 1) for _ in sira]


def js_yaz(yol: Path, parcalar: tuple) -> int:
    bas, anomaliler, son = parcalar
    kac = lambda s: json.dumps(s, ensure_ascii=False).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    satirlar = ["// bu dosya uzay_uret.py ile üretilir, elle düzenleme (github-profil/gorseller/uzay_uret.py)",
                f"export const BAS = {kac(bas)};",
                "export const ANOMALILER = ["]
    satirlar += [f"  {{ ad: {kac(a['ad'])}, sure: {a['sure']:g}, svg: {kac(a['svg'])} }}," for a in anomaliler]
    satirlar += ["];", f"export const SON = {kac(son)};", ""]
    metin = "\n".join(satirlar)
    yol.write_text(metin, encoding="utf-8")
    return len(metin.encode("utf-8"))


if __name__ == "__main__":
    burasi = Path(__file__).resolve().parent
    parcalar = parcala()
    sira, araliklar = yedek_sira()
    svg = birlestir(sira, araliklar, parcalar)
    hedef = burasi / "kuzey-uzay.svg"
    hedef.write_text(svg, encoding="utf-8")
    js = burasi.parents[1] / "kuzey-labs" / "site" / "worker" / "uzay_parcalar.js"
    print(f"{hedef.name}: {len(svg.encode('utf-8')) / 1024:.0f} KB")
    if js.parent.is_dir():  # sunucu parçaları yalnız site deposunun yanında yazılır
        print(f"{js.name}: {js_yaz(js, parcalar) / 1024:.0f} KB")
    print("yedek sira:", ", ".join(f"{ad}@{t:g}s" for ad, t in baslangiclar(sira, araliklar)))
