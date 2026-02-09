import json
from io import BytesIO
from minio import Minio
from src.backend.services.sentence_service import SentenceService

client = Minio('localhost:9000', access_key='minioadmin', secret_key='minioadmin', secure=False)
bucket = 'cres'

for slug in ['antigravity', 'anti-gravity']:
    key = f'queries/{slug}/combined/combined-output.json'
    try:
        obj = client.get_object(bucket, key)
        try:
            payload = json.loads(obj.read().decode('utf-8'))
        finally:
            obj.close(); obj.release_conn()
    except Exception:
        continue

    transcript_texts = []
    for item in payload.get('transcripts', []):
        tkey = item.get('transcript_key')
        if not tkey:
            continue
        try:
            tobj = client.get_object(bucket, tkey)
            try:
                tdata = json.loads(tobj.read().decode('utf-8'))
            finally:
                tobj.close(); tobj.release_conn()
            text = (tdata.get('text') or '').strip()
            if text:
                transcript_texts.append(text)
        except Exception:
            pass

    terms = [k.get('term') for k in payload.get('combined_keywords', []) if isinstance(k, dict) and k.get('term')]
    sentence = SentenceService.extract_combined_sentence_from_transcripts(transcript_texts, terms, max_sentences=5)
    payload['combined_sentence'] = sentence

    raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    client.put_object(bucket, key, BytesIO(raw), len(raw), content_type='application/json')

    skey = f'queries/{slug}/combined/combined-sentence.txt'
    sraw = sentence.encode('utf-8')
    client.put_object(bucket, skey, BytesIO(sraw), len(sraw), content_type='text/plain; charset=utf-8')
    print(slug, 'updated', len(sentence))
