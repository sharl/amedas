# -*- coding: utf-8 -*-
import binascii
import datetime as dt
import io
import sys
import threading
import time

from PIL import Image
from pystray import Icon, Menu, MenuItem
from vvox import vvox
import requests
import schedule

INTERVAL = 300          # seconds
D_TEMP = 100
D_SNOW = -1
WD = '静穏 北北東 北東 東北東 東 東南東 南東 南南東 南 南南西 南西 西南西 西 西北西 北西 北北西 北'.split()
WEATHER_INFO = {
    0: "晴",
    1: "曇",
    2: "煙霧",
    3: "霧",
    4: "降水またはしゅう雨性の降水",
    5: "霧雨",
    6: "着氷性の霧雨",
    7: "雨",
    8: "着氷性の雨",
    9: "みぞれ",
    10: "雪",
    11: "凍雨",
    12: "霧雪",
    13: "しゅう雨または止み間のある雨",
    14: "しゅう雪または止み間のある雪",
    15: "ひょう",
    16: "雷",
    30: "天気不明",
    31: "欠測",
}

# AQC (Automatic Quality Control) 識別符号
# https://www.data.jma.go.jp/stats/data/mdrr/man/remark.html
# https://www.data.jma.go.jp/suishin/shiyou/pdf/no13301
# 0 正常
# 1 準正常 (やや疑わしい)
# 2 非常に疑わしい
# 3 利用に適さない
# 4 観測値は期間内で資料数が不足している
# 5 点検又は計画休止のため欠測
# 6 障害のため欠測
# 7 この要素の観測はしていない
AQC_INFO = {
    0: '',
    1: ')',
    2: '#',
    3: '#',
    4: ']',
    5: '休止中',
    6: '✕',
    None: '　',
}
ずんだもん = [3, 22]
四国めたん = [2, 36]


class taskTray:
    def __init__(self, code='44132'):
        # スレッド実行モード
        self.running = False
        self.vvox = True
        self.default = str()
        self.code = code
        self.loc = {}
        self.name = str()
        self.last_modified = None
        self.temp = D_TEMP
        self.snow = D_SNOW

        # スポット情報取得
        if not code:
            try:
                with open('.amedas') as fd:
                    self.code = fd.read().strip()
                    self.default = self.code
            except Exception:
                pass

        # アイコンの画像をデコード
        if self.code == self.default:
            image = Image.open(io.BytesIO(binascii.unhexlify(ICON.replace('\n', '').strip())))
        else:
            image = Image.open(f'{self.code}.png')
        menu = Menu(
            MenuItem('Reset', self.reset, default=True, visible=False),
            MenuItem('Voice', self.toggle, checked=lambda MenuItem: self.vvox),
            MenuItem('Exit', self.stopApp),
        )
        self.app = Icon(
            name='PYTHON.win32.amedas',
            title='zunda amedas',
            icon=image,
            menu=menu
        )
        self.amedas()

    def daytime(self, speaker):
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
        if now.hour <= 5:
            return speaker[1]
        return speaker[0]

    def vvox_temp(self):
        _name = '' if self.code == self.default else f'{self.name}が'
        temp = self.temp
        pm = ''
        if temp < 0:
            temp = -temp
            pm = 'マイナス'
        vvox(f"{_name}{pm}{str(temp).replace('.0', '')}度になったのだ", speaker=self.daytime(ずんだもん))

    def vvox_snow(self):
        _name = '' if self.code == self.default else f'{self.name}が'
        vvox(f'{_name}{self.snow}センチになったわ', speaker=self.daytime(四国めたん))

    def toggle(self):
        self.vvox = not self.vvox

    def reset(self):
        self.temp = D_TEMP
        self.snow = D_SNOW
        self.amedas()

    def amedas(self):
        try:
            r = requests.get(
                'https://www.jma.go.jp/bosai/amedas/const/amedastable.json',
                headers={
                    'If-Modified-Since': self.last_modified
                },
                timeout=10,
            )
            if r and r.status_code == 200:
                self.loc = r.json()[self.code]
                self.name = self.loc.get('kjName', '-')
                self.last_modified = r.headers.get('Last-Modified')
        except Exception:
            return

        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))) - dt.timedelta(minutes=10)
        yyyymmdd = now.strftime('%Y%m%d')
        HH = now.strftime('%H')
        hh = f'{int(HH) // 3 * 3:02d}'
        url = f'https://www.jma.go.jp/bosai/amedas/data/point/{self.code}/{yyyymmdd}_{hh}.json'
        try:
            r = requests.get(url, timeout=10)
            if r and r.status_code == 200:
                data = r.json()
                base_key = f'{yyyymmdd}{HH}0000'        # 積雪は1時間毎
                last_key = list(data.keys())[-1]
                _vars = data[base_key]
                for k in data[last_key]:
                    _vars[k] = data[last_key][k]
                h = last_key[8:10]
                if h == '00':
                    h = '24'
                m = last_key[10:12]
                lines = [
                    self.name + f' {h}:{m}'
                ]
                for x in [
                        '天気 weather -',
                        '気温 temp 度',
                        '降水 precipitation1h mm/h',
                        '風向 windDirection -',
                        '風速 wind m/s',
                        '積雪 snow cm',
                        '降雪 snow1h cm/h',
                        '湿度 humidity %',
                        '気圧 pressure hPa',
                ]:
                    t, k, u = x.split()
                    if k in _vars:
                        v, aqc = _vars[k]
                        print(k, [v, aqc])
                        if isinstance(v, float):
                            if v == int(v):
                                v = int(v)
                        # 0: 正常 1: 准正常
                        if aqc != 0 and aqc != 1:
                            continue

                        if self.vvox:
                            if k == 'temp':
                                temp = v
                                if int(temp) != int(self.temp):
                                    self.temp = temp
                                    self.vvox_temp()
                            if k == 'snow':
                                snow = v
                                if snow is not None and snow != self.snow:
                                    self.snow = snow
                                    self.vvox_snow()
                        if k == 'windDirection':
                            lines.append(f'{t} {WD[v]}')
                        elif k == 'weather':
                            lines.append(f'{t} {WEATHER_INFO[v]}')
                        else:
                            lines.append(f'{t} {v}{u}')
                title = '\n'.join(lines)
                self.app.title = title
                self.app.update_menu()
        except Exception:
            pass

    def runSchedule(self):
        # INTERVAL 秒ごとにタスクを実行
        schedule.every(INTERVAL).seconds.do(self.amedas)

        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stopApp(self):
        self.running = False
        self.app.stop()

    def runApp(self):
        self.running = True

        task_thread = threading.Thread(target=self.runSchedule)
        task_thread.start()

        self.app.run()


ICON = """
89504e470d0a1a0a0000000d4948445200000010000000100803000000282d0f530000000467414d410000b18f0bfc6105000000206348524d00007a
26000080840000fa00000080e8000075300000ea6000003a98000017709cba513c000001f2504c5445000000adadadb6b6b6afafafb0b0b0b1b1b1ac
acacafafafb6b6b6bebebec4c4c4adadadaeaeaeb5b5b5c9c9c9cacac9b8b8b8abababacacacafafafc9c9c9b6b6b6bebebec4c4c4b9b9b9b6b6b6c9
cacadededfe8e9e9eaeaebeaeaeae8e8e8e0dfded7d7d7ebebebe9e6e4e9d7cbe7ded8e5e5e5b5c7d8d6dde4d6d5d5e5e6e7ecc2a6f98333f4a068e8
dfdadee1e2599dd43d8ad2b3c3d5d9d8d7e6e6e6f0b38bfe6b09f98b41eadcd2b0c5d06da8cf7daed6d5dadfececebdededee3e5e5d3e2e8e7d8ceef
b893ecc9b2e8e5e3b9cbd1b4c7cee6e5e4e5e4e4e8e7e6cadae499d0e9e1e6e7e5e6e6e9e6e69cd0df63c2e1dfe1e1d0bcb7dfdbdae3e5e6ccdde6b5
d2e3aed0e3e4e6e6e3e1e28dcdd27fcddbe2e1e1cbaaa3ddd7d6eaebebecebeabbd5e4abd7eabbcedf9dc5e2e7e8ead9dad3bac9ab7bc9a4b3d4cee5
e3e3cba8a0ddd6d5e9e8e8c9dae4c9dde7e3e4e4dcd6c8dfd3b4d3c771bac74b98c480c9d6cde0dadacf8574d8c4c0e8e9eae8e8e7e1deddd2bca7cf
9d52d0a94ddab942d1cc8fccd2c5cddee4dee2e3d9c7c3e3dedddfdfdfc8a799c38765c9ab89d4c6afd0cec1c6d5e4c5dae7c5dfeadbe5e8e7e7e7eb
ececd7d8d8d1b7afcb9784e3e2e1e3e5e7c4d1e1b1cadfb1d1e5cddfe8d2d0cfe5e2e1e9e9e9e6e6e5e2e4e5c9dbe6dbe5e9ecebebe7e8e8ffffffc9
5c85100000001b74524e530000000000000748a7e3fb071891eeeeb0060649eda6e2fab091ee7688ee2800000001624b4744a52eb94a2f0000000774
494d4507e70c14080519ca11a16e0000010f4944415418d3636060606463e7e0e4e2e2e460e7666460606062e6e1e5939691959357e0e7e561666160
e5115054525651555353d7d014e0616510e45554d2d2d6d1d5d337303432e615621016513231313533b7b0b4b2b6b115616710b593b7777074727671
7573f790b713651093f7f4f2f6f1d5f2f30f080c0a961763e0920b090d0b8f30898c8a8e898d8b1767104f484c4a4e494d4bcfc8cccace010a88e5e6
e517141615979496955754568931884a57d7d4d6d537343635b7b4b6b58b32b08bc877747675f7f4f6f54f98380968ad20efe42953a74d9f3173d66c
132545a0c3587924e6cc9d67327fc1c2458b15414e6761e69194b29397935b62c707f61cd0fbdceca240ef8b8982bd0f0016db3bcfad6b6df4000000
2574455874646174653a63726561746500323032332d31322d31395432333a30353a35342b30393a303005c035420000002574455874646174653a6d
6f6469667900323032332d31322d31395432333a30353a32352b30393a3030d82f8f530000000049454e44ae426082
"""

if __name__ == '__main__':
    code = None
    if len(sys.argv) == 2:
        code = sys.argv[1]
    taskTray(code).runApp()
