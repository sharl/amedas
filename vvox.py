# -*- coding: utf-8 -*-
import json
import requests
import pyaudio


def vvox(text, host='127.0.0.1', port=50021, speaker=3):
    params = {
        'text': text,
        'speaker': speaker,
    }
    query = requests.post(
        f'http://{host}:{port}/audio_query',
        params=params,
    )
    synthesis = requests.post(
        f'http://{host}:{port}/synthesis',
        headers={'Content-Type': 'application/json'},
        params=params,
        data=json.dumps(query.json()),
    )
    voice = synthesis.content

    pya = pyaudio.PyAudio()
    stream = pya.open(
        format=pyaudio.paInt16,         # 16bit
        channels=1,                     # モノラル
        rate=24000,                     # 設定の「音声のサンプリングレート」に合わせる デフォルトは24000
        output=True,
    )
    stream.write(voice)
    stream.stop_stream()
    stream.close()
    pya.terminate()
