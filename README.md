# amedas

アメダスの気温や積雪量が更新されたら VOICEVOX でお知らせ

## Run

```
git clone https://github.com/sharl/amedas.git
cd amedas
pip install -r requirements.txt
python amedas.py
```

## 設定ファイル `.amedas` 書式
```
14163
```
[アメダス](https://www.jma.go.jp/bosai/amedas/#area_type=japan&area_code=010000)の観測地点コードを記述します。
`14163` は[札幌](https://www.jma.go.jp/bosai/amedas/#amdno=14163)です。
[東京](https://www.jma.go.jp/bosai/amedas/#amdno=44132)は `44132` です。
*#amdno=数字* が観測地点コードになります。
