import json, glob, os

logs = sorted(glob.glob('c:/Users/HP/Desktop/vaani voice agent/backend/logs/latency_*.json'), key=os.path.getmtime)
if not logs:
    print("No logs")
    exit(0)

d = json.load(open(logs[-1]))
valid = [t for t in d if t.get('transcript')]

for v in valid:
    ts = v['timestamps']
    if 'vad_stop' in ts and 'bot_started' in ts:
        print(f"Turn {v['turn_index']}: '{v['transcript']}'")
        
        stt_final = ts.get('stt_final', ts['vad_stop'])
        print(f"  VAD -> STT Final: {(stt_final - ts['vad_stop'])*1000:.0f}ms")
        
        turn_stop = ts.get('turn_stop', stt_final)
        print(f"  STT Final -> Smart Turn COMPLETE: {(turn_stop - stt_final)*1000:.0f}ms")
        
        llm_first = ts.get('llm_first_token', turn_stop)
        print(f"  Turn COMPLETE -> LLM First Token (TTFB): {(llm_first - turn_stop)*1000:.0f}ms")
        
        text_tts = ts.get('first_text_to_tts', llm_first)
        print(f"  LLM First -> First text to TTS: {(text_tts - llm_first)*1000:.0f}ms")
        
        bot_started = ts.get('bot_started', text_tts)
        print(f"  TTS Text -> Bot Audio Started: {(bot_started - text_tts)*1000:.0f}ms")
        
        total = bot_started - ts['vad_stop']
        print(f"  Total Latency (VAD to Audio): {total*1000:.0f}ms\n")
