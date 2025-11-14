# -*- coding: utf-8 -*-
import io
import wave

import pyaudio
import requests

CHUNK = 1024


def vvox(text, host='127.0.0.1', port=50021, speaker=3, speed=1.0, volume=1.0):
    params = {
        'text': text,
        'speaker': speaker,
    }
    query = requests.post(
        f'http://{host}:{port}/audio_query',
        params=params,
        timeout=10,
    )
    qp = query.json()
    # modify query
    qp['speedScale'] = speed
    qp['volumeScale'] = volume

    synthesis = requests.post(
        f'http://{host}:{port}/synthesis',
        headers={'Content-Type': 'application/json'},
        params=params,
        json=qp,
        timeout=10,
    )
    voice = synthesis.content

    pya = pyaudio.PyAudio()
    stream = pya.open(
        format=pyaudio.paInt16,         # 16bit
        channels=1,                     # モノラル
        rate=qp['outputSamplingRate'],
        output=True,
    )

    wf = wave.open(io.BytesIO(voice), 'rb')
    data = wf.readframes(CHUNK)
    while data:
        stream.write(data)
        data = wf.readframes(CHUNK)

    stream.stop_stream()
    stream.close()
    pya.terminate()
