#!/opt/homebrew/bin/python3
"""TektoCraft の紹介サイト(GitHub Pages)の、静的な HTML を作る。

使い方: /opt/homebrew/bin/python3 tools/build_site.py   (リポジトリのルートで)
  - 紹介する 9 アプリの、名前・説明・画像を、各アプリのストア用の素材(~/dev/ 以下)から読む。
  - 出力: <言語>/index.html(アプリ一覧)、<言語>/<アプリ>/index.html(紹介ページ)、index.html(言語の振り分け)、
          assets/(CSS・アイコン・スクリーンショット)、sitemap.xml、tools/apps.json(読み込んだ内容の写し。確認用)。
  - プライバシーポリシーの URL(/<アプリ>/)は、変えない。この中の紹介ページは、/<言語>/<アプリ>/ に置く。
  - 生成物は、手で直さない(このスクリプトを直して、作り直す)。
"""
import hashlib
import html
import json
import os
import re
import shutil
import sys
from collections import OrderedDict

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV = os.path.expanduser('~/dev')
APPS_SRC = os.path.join(DEV, 'tekto-apps/apps')
BASE = 'https://tektocraft.github.io'
CONTACT = 'tektocraft.apps@gmail.com'
YEAR = '2026'

# サイトの言語(URL のパス、表示名、html の lang)
LANGS = OrderedDict([
    ('ja', ('日本語', 'ja')), ('en', ('English', 'en')), ('de', ('Deutsch', 'de')), ('fr', ('Français', 'fr')), ('es', ('Español', 'es')),
    ('pt', ('Português', 'pt')), ('it', ('Italiano', 'it')), ('ru', ('Русский', 'ru')), ('ko', ('한국어', 'ko')),
    ('zh-hans', ('简体中文', 'zh-Hans')), ('zh-hant', ('繁體中文', 'zh-Hant')), ('ar', ('العربية', 'ar')), ('th', ('ไทย', 'th')), ('hi', ('हिन्दी', 'hi')),
])
RTL = {'ar'}
# Play のロケール名 → サイトの言語
LOCALE = {'ja-JP': 'ja', 'ja': 'ja', 'en-US': 'en', 'de-DE': 'de', 'fr-FR': 'fr', 'es-ES': 'es', 'pt-BR': 'pt', 'pt-PT': 'pt', 'it-IT': 'it', 'it': 'it',
          'ru-RU': 'ru', 'ko-KR': 'ko', 'zh-CN': 'zh-hans', 'zh-TW': 'zh-hant', 'ar': 'ar', 'th': 'th', 'hi-IN': 'hi'}
IOS_KEYS = {'ja': 'ja', 'en': 'en', 'de': 'de', 'fr': 'fr', 'es': 'es', 'pt': 'pt', 'it': 'it', 'ru': 'ru', 'ko': 'ko', 'zh-Hans': 'zh-hans',
            'zh-Hant': 'zh-hant', 'ar': 'ar', 'th': 'th', 'hi': 'hi'}

# 紹介するアプリ(表示の順)。ios = App Store の ID(公開前は None)、play = Google Play のパッケージ名、policy = ポリシーのページ(/<policy>/)。
APPS = [
    dict(slug='learninglog', src='study_log', policy='learninglog', ios=1461679466, play='app.tektocraft.study_log',
         ios_json=os.path.join(DEV, 'LearningLog/docs/listing-1.2.0.json')),
    dict(slug='scientificcalc', src='sci_calc', policy='scientificcalc', ios=1452129839, play='app.tektocraft.sci_calc',
         ios_json=os.path.join(DEV, 'ScientificCalc/docs/listing-1.3.0.json')),
    dict(slug='historycalc', src='history_calc', policy='historycalc', ios=1452124003, play='app.tektocraft.history_calc',
         ios_json=os.path.join(DEV, 'HistoryCalc/docs/listing-1.2.0.json')),
    dict(slug='kyudo', src='kyudo', policy='kyudo', ios=1465454417, play='app.tektocraft.kyudo'),
    dict(slug='jikanwari', src='timetable', policy='jikanwari', ios=1464675027, play='app.tektocraft.timetable',
         ios_json=os.path.join(DEV, 'Jikanwari/docs/listing-1.2.0.json')),
    dict(slug='lifelog', src='life_log', policy='lifelog', ios=1460523405, play='app.tektocraft.life_log'),
    dict(slug='huelab', src='color_sense', policy='huelab', ios=None, play='app.tektocraft.color_sense'),
    dict(slug='dailyrhythm', src='snare_lab', policy='dailyrhythm', ios=6832241980, play='app.tektocraft.snare_lab'),
    dict(slug='pin2048', src='pin_2048', policy='pin2048', ios=None, play='app.tektocraft.pin_2048'),
    # iOS のみ(Android 版なし)。アイコンとスクリーンショットは、ABAB のリポジトリから。
    dict(slug='abab', src=None, policy='abab', ios=1460811673, play=None,
         ios_json=os.path.join(DEV, 'ABAB/docs/listing-2.0.0.json'),
         icon=os.path.join(DEV, 'ABAB/docs/icon/final/AppIcon-1024.png'),
         shots_dir=os.path.join(DEV, 'ABAB/docs/store/final'), shots_names=('1.png', '2.png', '3.png')),
]

# サイトの文言(14 言語)
T = {
    'apps': dict(ja='アプリ', en='Apps', de='Apps', fr='Applications', es='Aplicaciones', pt='Aplicativos', it='App', ru='Приложения', ko='앱',
                 **{'zh-hans': '应用', 'zh-hant': '應用程式'}, ar='التطبيقات', th='แอป', hi='ऐप्स'),
    'intro': dict(ja='シンプルで使いやすいアプリを作っています。', en='Simple, easy-to-use apps.', de='Einfache, leicht zu bedienende Apps.',
                  fr='Des applications simples et faciles à utiliser.', es='Aplicaciones sencillas y fáciles de usar.',
                  pt='Aplicativos simples e fáceis de usar.', it='App semplici e facili da usare.', ru='Простые и удобные приложения.',
                  ko='간단하고 쓰기 쉬운 앱을 만듭니다.', **{'zh-hans': '制作简单易用的应用。', 'zh-hant': '製作簡單好用的 App。'},
                  ar='تطبيقات بسيطة وسهلة الاستخدام.', th='แอปที่เรียบง่ายและใช้งานง่าย', hi='सरल और आसानी से इस्तेमाल होने वाले ऐप।'),
    'app_store': dict(ja='App Store で入手', en='Download on the App Store', de='Laden im App Store', fr="Télécharger sur l'App Store",
                      es='Descargar en App Store', pt='Baixar na App Store', it="Scarica dall'App Store", ru='Загрузить в App Store',
                      ko='App Store에서 받기', **{'zh-hans': '在 App Store 下载', 'zh-hant': '於 App Store 下載'}, ar='نزّل من App Store',
                      th='ดาวน์โหลดจาก App Store', hi='App Store से पाएँ'),
    'google_play': dict(ja='Google Play で入手', en='Get it on Google Play', de='Jetzt bei Google Play', fr='Disponible sur Google Play',
                        es='Disponible en Google Play', pt='Disponível no Google Play', it='Scarica su Google Play', ru='Доступно в Google Play',
                        ko='Google Play에서 받기', **{'zh-hans': '在 Google Play 获取', 'zh-hant': '在 Google Play 取得'}, ar='احصل عليه من Google Play',
                        th='รับได้จาก Google Play', hi='Google Play पर पाएँ'),
    'soon': dict(ja='App Store は近日公開', en='App Store: coming soon', de='App Store: demnächst', fr="App Store : bientôt",
                 es='App Store: próximamente', pt='App Store: em breve', it='App Store: prossimamente', ru='App Store: скоро',
                 ko='App Store: 출시 예정', **{'zh-hans': 'App Store：即将上线', 'zh-hant': 'App Store：即將上架'}, ar='App Store: قريبًا',
                 th='App Store: เร็ว ๆ นี้', hi='App Store: जल्द आ रहा है'),
    'screenshots': dict(ja='スクリーンショット', en='Screenshots', de='Screenshots', fr="Captures d'écran", es='Capturas de pantalla',
                        pt='Capturas de tela', it='Schermate', ru='Скриншоты', ko='스크린샷', **{'zh-hans': '屏幕截图', 'zh-hant': '螢幕截圖'},
                        ar='لقطات الشاشة', th='ภาพหน้าจอ', hi='स्क्रीनशॉट'),
    'privacy': dict(ja='プライバシーポリシー', en='Privacy Policy', de='Datenschutzerklärung', fr='Politique de confidentialité',
                    es='Política de privacidad', pt='Política de privacidade', it='Informativa sulla privacy', ru='Политика конфиденциальности',
                    ko='개인정보 처리방침', **{'zh-hans': '隐私政策', 'zh-hant': '隱私權政策'}, ar='سياسة الخصوصية', th='นโยบายความเป็นส่วนตัว',
                    hi='गोपनीयता नीति'),
    'contact': dict(ja='お問い合わせ', en='Contact', de='Kontakt', fr='Contact', es='Contacto', pt='Contato', it='Contatti', ru='Контакты',
                    ko='문의', **{'zh-hans': '联系我们', 'zh-hant': '聯絡我們'}, ar='اتصل بنا', th='ติดต่อ', hi='संपर्क'),
    'all_apps': dict(ja='すべてのアプリ', en='All apps', de='Alle Apps', fr='Toutes les applications', es='Todas las aplicaciones',
                     pt='Todos os aplicativos', it='Tutte le app', ru='Все приложения', ko='모든 앱', **{'zh-hans': '全部应用', 'zh-hant': '全部應用程式'},
                     ar='كل التطبيقات', th='แอปทั้งหมด', hi='सभी ऐप'),
    'language': dict(ja='言語', en='Language', de='Sprache', fr='Langue', es='Idioma', pt='Idioma', it='Lingua', ru='Язык', ko='언어',
                     **{'zh-hans': '语言', 'zh-hant': '語言'}, ar='اللغة', th='ภาษา', hi='भाषा'),
    'fallback': dict(ja='このアプリの説明は、英語です。', en='', de='Die Beschreibung dieser App ist auf Englisch.', fr="La description de cette application est en anglais.",
                     es='La descripción de esta aplicación está en inglés.', pt='A descrição deste aplicativo está em inglês.', it="La descrizione di questa app è in inglese.",
                     ru='Описание этого приложения на английском.', ko='이 앱의 설명은 영어입니다.', **{'zh-hans': '此应用的说明为英文。', 'zh-hant': '此 App 的說明為英文。'},
                     ar='وصف هذا التطبيق باللغة الإنجليزية.', th='คำอธิบายของแอปนี้เป็นภาษาอังกฤษ', hi='इस ऐप का विवरण अंग्रेज़ी में है।'),
}
# 説明文から外す段落(「上のページに記載のメール」など、ストアの画面を前提にした文)
STORE_ONLY = re.compile(r'上のページ|page above|ci-dessus|arriba|acima|sopra|oben genannt|выше|위 페이지|上述|أعلاه|ด้านบน|ऊपर दिए|tektocraft\.github\.io/\S*\s*$')


def read(path):
    return open(path, encoding='utf-8').read().strip()


def first(*paths):
    for p in paths:
        if os.path.exists(p):
            return read(p)
    return None


def load_app(a):
    """アプリごとに、言語 → {name, tagline, desc} と、アイコン、スクリーンショットを集める。"""
    base = os.path.join(APPS_SRC, a['src'], 'store/android') if a.get('src') else None
    texts = {}
    ios = json.load(open(a['ios_json'], encoding='utf-8')) if a.get('ios_json') else {}
    ldir = os.path.join(base, 'listing') if base else None
    for d in (sorted(os.listdir(ldir)) if ldir else []):
        code = LOCALE.get(d)
        if not code:
            continue
        p = os.path.join(ldir, d)
        title = first(p + '/title.txt')
        short = first(p + '/short_description.txt', p + '/short.txt')
        full = first(p + '/full_description.txt', p + '/full.txt')
        if title and full:
            texts[code] = dict(name=title, tagline=short or '', desc=full)
    for k, code in IOS_KEYS.items():
        if k in ios:
            i = ios[k]
            cur = texts.get(code, {})
            # 名前は、ストアで統一した iOS 側。説明は Android(ストアの説明文)があればそれを、なければ iOS の説明。
            texts[code] = dict(name=i['name'], tagline=cur.get('tagline') or i['promo'], desc=cur.get('desc') or i['description'])
    return texts


def short_name(name):
    for sep in (' - ', ': ', ' – ', ' — '):
        if sep in name:
            return name.split(sep)[0].strip()
    return name


def blocks(desc):
    """説明文を、段落・見出し・箇条書きの塊にする。"""
    out = []
    for raw in re.split(r'\n\s*\n', desc.strip()):
        lines = [l.rstrip() for l in raw.strip().split('\n') if l.strip()]
        if not lines or STORE_ONLY.search(raw):
            continue
        bullet = lambda s: re.match(r'^\s*(?:[-•*]\s+|・\s*)', s)
        head = None
        m = re.match(r'^[■【\[]\s*(.+?)\s*[】\]]?$', lines[0])
        if m and (lines[0].startswith('■') or lines[0].startswith('【')):
            head = m.group(1)
            lines = lines[1:]
        elif len(lines) > 1 and not bullet(lines[0]) and all(bullet(l) for l in lines[1:]) and len(lines[0]) < 60 and not lines[0].endswith(('。', '.', '!', '?', '！', '？')):
            head = lines[0]
            lines = lines[1:]
        elif len(lines) > 1 and not bullet(lines[0]) and len(lines[0]) < 40 and not re.search(r'[。.!?！？:：]$', lines[0]) and lines[0].upper() == lines[0] and re.search(r'[A-ZÄÖÜ]', lines[0]):
            head = lines[0]
            lines = lines[1:]
        if head:
            out.append(('h', head))
        if lines and all(bullet(l) for l in lines):
            out.append(('ul', [re.sub(r'^\s*(?:[-•*]\s+|・\s*)', '', l) for l in lines]))
        elif lines:
            out.append(('p', lines))
    return out


def accent(img_path):
    """アイコンの主色: 彩度のある画素を、色相の 12 区画に分け、いちばん多い区画の平均色。"""
    import colorsys
    im = Image.open(img_path).convert('RGB').resize((64, 64))
    buckets = {}
    for r, g, b in im.getdata():
        h, s_, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s_ < 0.25 or v < 0.25 or v > 0.97:
            continue
        k = int(h * 12) % 12
        buckets.setdefault(k, []).append((r, g, b))
    if not buckets:
        return (200, 90, 80)
    px = max(buckets.values(), key=len)
    n = len(px)
    r, g, b = (sum(c[i] for c in px) // n for i in range(3))
    h, s_, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    r, g, b = colorsys.hsv_to_rgb(h, min(1.0, max(s_, 0.55)), min(v, 0.78))  # 文字や枠に使えるよう、少し濃く
    return (int(r * 255), int(g * 255), int(b * 255))


def esc(s):
    return html.escape(s, quote=True)


CSS = """
:root{--bg:#fafaf8;--fg:#1d1d1f;--sub:#5f6368;--card:#fff;--line:#e4e4df;--acc:#d9534f;--max:960px}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--fg:#f2f2f0;--sub:#a0a4a8;--card:#202024;--line:#34343a}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","Hiragino Sans","Noto Sans CJK JP","Noto Sans",system-ui,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:var(--max);margin:0 auto;padding:0 20px}
header.site{border-bottom:1px solid var(--line);background:var(--card)}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:56px}
.brand{font-weight:700;font-size:18px;color:var(--fg)}.brand:hover{text-decoration:none}
nav.top{display:flex;align-items:center;gap:16px}
details.lang{position:relative}details.lang summary{cursor:pointer;list-style:none;padding:6px 12px;border:1px solid var(--line);border-radius:999px;font-size:14px;color:var(--fg);background:var(--card)}
details.lang summary::-webkit-details-marker{display:none}
details.lang ul{position:absolute;inset-inline-end:0;margin:6px 0 0;padding:6px;list-style:none;background:var(--card);border:1px solid var(--line);border-radius:12px;min-width:160px;box-shadow:0 8px 24px rgba(0,0,0,.12);z-index:5;max-height:70vh;overflow:auto}
details.lang li a{display:block;padding:7px 12px;border-radius:8px;color:var(--fg)}details.lang li a:hover{background:var(--line);text-decoration:none}
details.lang li a[aria-current]{font-weight:700}
main{padding:32px 0 56px}
h1{font-size:clamp(26px,5vw,38px);line-height:1.25;margin:0 0 8px}
h2{font-size:20px;margin:36px 0 10px}
.lead{color:var(--sub);font-size:18px;margin:0 0 28px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.card{display:flex;gap:16px;align-items:center;padding:16px;background:var(--card);border:1px solid var(--line);border-radius:18px;color:var(--fg)}
.card:hover{text-decoration:none;border-color:var(--acc);transform:translateY(-1px)}
.card img{width:72px;height:72px;border-radius:17px;flex:none;box-shadow:0 1px 4px rgba(0,0,0,.18)}
.card b{display:block;font-size:17px;line-height:1.35}.card span{display:block;color:var(--sub);font-size:14px;line-height:1.5;margin-top:2px}
.hero{display:flex;gap:24px;align-items:center;padding:28px;border-radius:26px;background:linear-gradient(135deg,color-mix(in srgb,var(--acc) 16%,var(--card)),var(--card));border:1px solid var(--line)}
.hero img{width:112px;height:112px;border-radius:26px;flex:none;box-shadow:0 2px 10px rgba(0,0,0,.22)}
.hero p{margin:0 0 16px;color:var(--sub);font-size:17px}
.btns{display:flex;flex-wrap:wrap;gap:10px}
.btn{display:inline-block;padding:10px 18px;border-radius:12px;background:var(--fg);color:var(--bg);font-weight:600;font-size:15px}
.btn:hover{text-decoration:none;opacity:.85}.btn.off{background:transparent;color:var(--sub);border:1px dashed var(--line);font-weight:400}
.shots{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 14px;scroll-snap-type:x proximity}
.shots img{height:440px;width:auto;border-radius:20px;border:1px solid var(--line);flex:none;scroll-snap-align:start;background:var(--card)}
.shots{margin-bottom:8px}.doc{margin-top:28px}.doc p{margin:0 0 14px}.doc ul{margin:0 0 14px;padding-inline-start:1.3em}.doc li{margin:3px 0}
.note{color:var(--sub);font-size:14px;margin:0 0 12px}
footer.site{border-top:1px solid var(--line);padding:24px 0;color:var(--sub);font-size:14px}
footer.site .wrap{display:flex;flex-wrap:wrap;gap:8px 20px;justify-content:space-between}
@media(max-width:560px){.hero{flex-direction:column;align-items:flex-start;padding:22px}.shots img{height:380px}}
[dir=rtl] .hero,[dir=rtl] .card{text-align:start}
"""


def page(lang, title, desc, body, alts, canonical, app=None, accent_rgb=None, og_image=None, jsonld=None):
    name, htmllang = LANGS[lang]
    d = ' dir="rtl"' if lang in RTL else ''
    alt_tags = ''.join(f'<link rel="alternate" hreflang="{LANGS[c][1]}" href="{BASE}{u}">' for c, u in alts)
    if alts:
        alt_tags += f'<link rel="alternate" hreflang="x-default" href="{BASE}{dict(alts).get("en", alts[0][1])}">'
    sw = ''.join(f'<li><a href="{u}"{" aria-current=page" if c == lang else ""} hreflang="{LANGS[c][1]}" lang="{LANGS[c][1]}" data-lang="{c}">{esc(LANGS[c][0])}</a></li>' for c, u in alts)
    style = ''
    if accent_rgb:
        style = f'<style>:root{{--acc:rgb{accent_rgb}}}@media (prefers-color-scheme:dark){{:root{{--acc:color-mix(in srgb,rgb{accent_rgb} 70%,#fff)}}}}</style>'
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ''
    img = f'<meta property="og:image" content="{BASE}{og_image}">' if og_image else ''
    return f"""<!doctype html>
<html lang="{htmllang}"{d}>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}{canonical}">{alt_tags}
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">{img}
<meta name="theme-color" content="#d9534f">
<link rel="icon" href="/assets/favicon.png">
<link rel="stylesheet" href="/assets/site.css">{style}{ld}
</head>
<body>
<header class="site"><div class="wrap"><a class="brand" href="/{lang}/">TektoCraft</a>
<nav class="top"><details class="lang"><summary aria-label="{esc(T['language'][lang])}">🌐 {esc(name)}</summary><ul>{sw}</ul></details></nav></div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap"><span>© {YEAR} TektoCraft</span><span><a href="mailto:{CONTACT}">{esc(T['contact'][lang])}</a></span></div></footer>
<script>try{{document.querySelectorAll('details.lang a').forEach(function(a){{a.addEventListener('click',function(){{localStorage.setItem('tc_lang',a.dataset.lang)}})}})}}catch(e){{}}</script>
</body></html>
"""


def write(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(text)


def main():
    # 出力を作り直す(古い生成物を消す)。ポリシーのページ(<アプリ>/)は、触らない。
    for lang in LANGS:
        shutil.rmtree(os.path.join(ROOT, lang), ignore_errors=True)
    shutil.rmtree(os.path.join(ROOT, 'assets'), ignore_errors=True)
    os.makedirs(os.path.join(ROOT, 'assets/img'), exist_ok=True)
    write('assets/site.css', CSS.strip() + '\n')

    data = OrderedDict()
    sitemap = []
    for a in APPS:
        texts = load_app(a)
        base = os.path.join(APPS_SRC, a['src'], 'store/android') if a.get('src') else None
        icon_src = a['icon'] if a.get('icon') else next(p for p in (base + '/icon-512.png', base + '/icon512.png') if os.path.exists(p))
        out_icon = f'assets/img/{a["slug"]}/icon.png'
        os.makedirs(os.path.join(ROOT, os.path.dirname(out_icon)), exist_ok=True)
        Image.open(icon_src).convert('RGBA').resize((256, 256), Image.LANCZOS).save(os.path.join(ROOT, out_icon), optimize=True)
        acc = accent(icon_src)
        # スクリーンショット: 言語のフォルダにあればそれ、なければ en-US。同じ内容は、1 つの画像を使い回す。
        shots, done = {}, {}
        sdir = os.path.join(base, 'screenshots') if base else None
        for code in texts:
            if a.get('shots_dir'):
                # ストア用の画像(<言語>/1.png ...)。サイトの言語コードを、フォルダ名(zh-hans → zh-Hans)に直す。
                key = next((k for k, v in IOS_KEYS.items() if v == code), code)
                files = [os.path.join(a['shots_dir'], key, n) for n in a['shots_names'] if os.path.exists(os.path.join(a['shots_dir'], key, n))]
                urls = []
                for n, f in enumerate(files, 1):
                    h = hashlib.md5(open(f, 'rb').read()).hexdigest()
                    if h not in done:
                        rel = f'assets/img/{a["slug"]}/{code}-{n}.jpg'
                        im = Image.open(f).convert('RGB')
                        im = im.resize((540, int(im.size[1] * 540 / im.size[0])), Image.LANCZOS)
                        im.save(os.path.join(ROOT, rel), 'JPEG', quality=80, optimize=True)
                        done[h] = '/' + rel
                    urls.append(done[h])
                shots[code] = urls
                continue
            locs = [d for d, c in LOCALE.items() if c == code and os.path.isdir(os.path.join(sdir, d))] or ['en-US']
            folder = os.path.join(sdir, locs[0])
            files = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(folder) for f in fs if f.lower().endswith('.png'))[:6]
            if not files and locs[0] != 'en-US':
                folder = os.path.join(sdir, 'en-US')
                files = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(folder) for f in fs if f.lower().endswith('.png'))[:6]
            urls = []
            for n, f in enumerate(files, 1):
                h = hashlib.md5(open(f, 'rb').read()).hexdigest()
                if h not in done:
                    rel = f'assets/img/{a["slug"]}/{code}-{n}.jpg'
                    im = Image.open(f).convert('RGB')
                    im = im.resize((540, int(im.size[1] * 540 / im.size[0])), Image.LANCZOS)
                    im.save(os.path.join(ROOT, rel), 'JPEG', quality=80, optimize=True)
                    done[h] = '/' + rel
                urls.append(done[h])
            shots[code] = urls
        data[a['slug']] = dict(a, texts=texts, shots=shots, icon='/' + out_icon, accent=acc)

    Image.open(os.path.join(ROOT, 'assets/img/learninglog/icon.png')).resize((64, 64)).save(os.path.join(ROOT, 'assets/favicon.png'))

    def best(app, lang):
        t = app['texts']
        return lang if lang in t else ('en' if 'en' in t else next(iter(t)))

    # 一覧と紹介ページ
    for lang in LANGS:
        alts_all = [(c, f'/{c}/') for c in LANGS]
        cards = []
        for slug, app in data.items():
            use = best(app, lang)
            t = app['texts'][use]
            cards.append(f'<a class="card" href="/{use if use != "en" or "en" in app["texts"] else lang}/{slug}/"{"" if use == lang else " lang=%s" % chr(34) + LANGS[use][1] + chr(34)}>'
                         f'<img src="{app["icon"]}" alt="" width="72" height="72"><div><b>{esc(short_name(t["name"]))}</b><span>{esc(t["tagline"])}</span></div></a>')
        body = f'<h1>{esc(T["apps"][lang])}</h1><p class="lead">{esc(T["intro"][lang])}</p><div class="grid">{"".join(cards)}</div>'
        write(f'{lang}/index.html', page(lang, f'TektoCraft — {T["apps"][lang]}', T['intro'][lang], body, alts_all, f'/{lang}/'))
        sitemap.append(f'/{lang}/')

    for slug, app in data.items():
        langs = [c for c in LANGS if c in app['texts']]
        alts = [(c, f'/{c}/{slug}/') for c in langs]
        for lang in langs:
            t = app['texts'][lang]
            nm = short_name(t['name'])
            btns = []
            if app['ios']:
                btns.append(f'<a class="btn" href="https://apps.apple.com/app/id{app["ios"]}" rel="noopener">{esc(T["app_store"][lang])}</a>')
            else:
                btns.append(f'<span class="btn off">{esc(T["soon"][lang])}</span>')
            if app['play']:
                btns.append(f'<a class="btn" href="https://play.google.com/store/apps/details?id={app["play"]}" rel="noopener">{esc(T["google_play"][lang])}</a>')
            sh = app['shots'].get(lang) or app['shots'].get('en') or []
            shots = ''.join(f'<img src="{u}" alt="{esc(nm)} {i}" loading="lazy" width="360">' for i, u in enumerate(sh, 1))
            doc = []
            for kind, v in blocks(t['desc']):
                if kind == 'h':
                    doc.append(f'<h2>{esc(v)}</h2>')
                elif kind == 'ul':
                    doc.append('<ul>' + ''.join(f'<li>{esc(x)}</li>' for x in v) + '</ul>')
                else:
                    doc.append('<p>' + '<br>'.join(esc(x) for x in v) + '</p>')
            body = (f'<p class="note"><a href="/{lang}/">← {esc(T["all_apps"][lang])}</a></p>'
                    f'<section class="hero"><img src="{app["icon"]}" alt="" width="112" height="112"><div><h1>{esc(nm)}</h1><p>{esc(t["tagline"])}</p><div class="btns">{"".join(btns)}</div></div></section>'
                    + (f'<h2>{esc(T["screenshots"][lang])}</h2><div class="shots">{shots}</div>' if shots else '')
                    + f'<div class="doc">{"".join(doc)}</div>'
                    + f'<h2>{esc(T["privacy"][lang])}</h2><p><a href="/{app["policy"]}/">{esc(T["privacy"][lang])}</a></p>')
            ld = {'@context': 'https://schema.org', '@type': 'MobileApplication', 'name': nm, 'description': t['tagline'],
                  'operatingSystem': 'iOS, Android' if app['play'] else 'iOS', 'applicationCategory': 'UtilitiesApplication', 'image': BASE + app['icon'],
                  'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'}, 'inLanguage': LANGS[lang][1]}
            write(f'{lang}/{slug}/index.html', page(lang, f'{nm} — TektoCraft', t['tagline'] or nm, body, alts, f'/{lang}/{slug}/', app=slug,
                                                    accent_rgb=tuple(app['accent']), og_image=app['icon'], jsonld=ld))
            sitemap.append(f'/{lang}/{slug}/')

    # ルート: 言語の振り分け
    links = ''.join(f'<li><a href="/{c}/" lang="{LANGS[c][1]}">{esc(LANGS[c][0])}</a></li>' for c in LANGS)
    langmap = json.dumps({c: c for c in LANGS})
    write('index.html', f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TektoCraft</title><meta name="description" content="Simple, easy-to-use apps.">
<link rel="canonical" href="{BASE}/">{''.join(f'<link rel="alternate" hreflang="{LANGS[c][1]}" href="{BASE}/{c}/">' for c in LANGS)}<link rel="alternate" hreflang="x-default" href="{BASE}/en/">
<link rel="icon" href="/assets/favicon.png"><link rel="stylesheet" href="/assets/site.css">
<script>(function(){{var s=null;try{{s=localStorage.getItem('tc_lang')}}catch(e){{}}var L={langmap};var l=s&&L[s]?s:null;
if(!l){{var n=(navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language||'en']);
for(var i=0;i<n.length&&!l;i++){{var x=String(n[i]).toLowerCase();
if(/^zh/.test(x)){{l=/hant|-tw|-hk|-mo/.test(x)?'zh-hant':'zh-hans'}}else{{var p=x.split('-')[0];if(L[p])l=p}}}}}}
location.replace('/'+(l||'en')+'/')}})();</script></head>
<body><main><div class="wrap"><h1>TektoCraft</h1><ul>{links}</ul></div></main></body></html>
""")
    sitemap.append('/')

    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + ''.join(f'<url><loc>{BASE}{u}</loc></url>\n' for u in sitemap) + '</urlset>\n')
    write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    summary = {s: dict(langs=[c for c in LANGS if c in a['texts']], shots={c: len(v) for c, v in a['shots'].items()}, ios=a['ios'], play=a['play'])
               for s, a in data.items()}
    write('tools/apps.json', json.dumps(summary, ensure_ascii=False, indent=1))
    print('pages:', len(sitemap))
    for s, v in summary.items():
        print(s, len(v['langs']), 'langs', 'ios' if v['ios'] else 'ios:soon')


main()
