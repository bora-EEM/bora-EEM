"""Aynı çizimi daha az baytla yazar. GitHub'ın resim aracısı SVG'yi sıkıştırmadan iletir, bu yüzden her bayt yolda sayılır.
Gereksiz boşluk, baştaki ve sondaki sıfırlar, doğrusal animasyonların eğri listeleri gider; gömülü resimlere dokunulmaz."""
import re

DUZ = "0 0 1 1"
_VERI = re.compile(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+")
_BOS = ("g|path|circle|rect|ellipse|image|use|line|polygon|polyline|stop|clipPath|linearGradient|radialGradient|"
        "animate|animateTransform|animateMotion")


def _animasyon(m: re.Match) -> str:
    e = m.group(0)
    ks = re.search(r' keySplines="([^"]*)"', e)
    if ks and not e.startswith("<animateMotion") and all(k.strip() == DUZ for k in ks.group(1).split(";")):
        e = e.replace(ks.group(0), "").replace(' calcMode="spline"', "")      # doğrusal zaten varsayılan
    elif ks and 'attributeName="opacity"' in e:                                # sönüp yanmada eğri gözle ayırt edilmez
        e = e.replace(ks.group(0), "").replace(' calcMode="spline"', "")
    kt, vs = re.search(r' keyTimes="([^"]*)"', e), re.search(r' values="([^"]*)"', e)
    if kt and vs and "keySplines" not in e and "calcMode" not in e:            # değeri değişmeyen ara noktalar gereksiz
        z, d = kt.group(1).split(";"), vs.group(1).split(";")
        kal = [i for i in range(len(d)) if i in (0, len(d) - 1) or not d[i - 1] == d[i] == d[i + 1]]
        if len(z) == len(d) and len(kal) < len(d):
            e = e.replace(vs.group(0), ' values="' + ";".join(d[i] for i in kal) + '"')
            e = e.replace(kt.group(0), ' keyTimes="' + ";".join(z[i] for i in kal) + '"')
    return e


def _nitelik(n: re.Match) -> str:
    ad, deger = n.group(1), n.group(2)
    if ad in ("begin", "dur", "id", "href", "aria-label", "font-family", "attributeName", "xmlns"):
        return n.group(0)
    if ad == "keyTimes":
        deger = ";".join(f"{float(x):.4f}" for x in deger.split(";"))
    deger = re.sub(r"(\.\d*?)0+(?!\d)", lambda k: k.group(1) if len(k.group(1)) > 1 else "", deger)
    deger = re.sub(r"(?<![\w.#])(-?)0+\.(\d)", r"\1.\2", deger)
    if ad in ("d", "points", "path"):
        deger = re.sub(r"\s*([MLHVCSQTAZmlhvcsqtaz])\s*", r"\1", deger)
    if ad in ("d", "points", "path", "values", "keySplines", "keyTimes"):
        deger = re.sub(r"([;,])\s+", r"\1", deger)
    if ad == "values":
        deger = re.sub(r"(?<=[\d.])\s*([MLHVCSQTAZ])\s*", r"\1", deger)
    return f' {ad}="{deger.strip()}"'


def _etiket(m: re.Match) -> str:
    e = re.sub(r'\s+([\w:-]+)="([^"]*)"', _nitelik, m.group(0))
    return re.sub(r"\s+(/?>)$", r"\1", e)


def hafiflet(svg: str) -> str:
    veri: list[str] = []

    def sakla(m: re.Match) -> str:
        veri.append(m.group(0))
        return f"@@{len(veri) - 1}@@"
    svg = _VERI.sub(sakla, svg)
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    svg = re.sub(r"<animate\w*\b[^>]*>", _animasyon, svg)
    svg = re.sub(r"<[a-zA-Z][^>]*>", _etiket, svg)
    svg = re.sub(r">\s+<(?!/?t(?:ext|span)\b)", "><", svg)
    svg = re.sub(rf"<({_BOS})\b([^>]*[^/>])></\1>", r"<\1\2/>", svg)
    return re.sub(r"@@(\d+)@@", lambda m: veri[int(m.group(1))], svg).strip()
