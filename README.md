# TektoCraft サイト(GitHub Pages)

- 公開 URL: https://tektocraft.github.io/
- **紹介ページ**(`/<言語>/`、`/<言語>/<アプリ>/`)、`assets/`、`sitemap.xml`、ルートの `index.html` は、`tools/build_site.py` が作る生成物。**手で直さない**(スクリプトを直して作り直す)。
  - 作り方: `/opt/homebrew/bin/python3 tools/build_site.py`(Pillow が要る。素材は `~/dev/tekto-apps/apps/*/store/android/` と、`LearningLog`・`ScientificCalc`・`HistoryCalc` の `docs/listing-*.json`)。
  - 掲載するアプリは、スクリプトの `APPS`。App Store の ID は、公開されたら `ios=` に入れる(それまでは「近日公開」と表示される)。
  - 言語は 14(ja en de fr es pt it ru ko zh-hans zh-hant ar th hi)。アプリごとに、ストアの文面がある言語だけ紹介ページを作る。
  - ローカル確認: `python3 -m http.server 8790` → http://127.0.0.1:8790/
- **プライバシーポリシー**(`/<アプリ>/`)は、手書きの Markdown(ストア・AdMob から参照されている URL。**変えない**)。一覧は `/policies/`。
- `app-ads.txt`(AdMob)は、ルートに置いたまま。
