"""Préchauffer le modèle réel verrouillé, sans générer ni envoyer de message client."""
import json
from pathlib import Path
import time
import urllib.request
import urllib.error


def main():
    lock = json.loads(Path('/project/infra/llm.lock.json').read_text())
    deadline = time.monotonic() + 20
    while True:
        try:
            with urllib.request.urlopen('http://ollama:11434/api/tags', timeout=5) as response:
                models = json.load(response)['models']
            break
        except (OSError, urllib.error.URLError):
            if time.monotonic() >= deadline:
                raise TimeoutError('Ollama non disponible sous 20 secondes')
            time.sleep(1)
    if not any(m['name'] == lock['model'] and m['digest'] == lock['digest'] for m in models):
        raise ValueError('Modèle verrouillé absent ; aucun téléchargement implicite')
    body = {'model': lock['model'], 'prompt': 'Bonjour', 'stream': False, 'keep_alive': '10m',
            'options': {'num_ctx': 2048, 'num_batch': 64, 'num_thread': 2, 'num_predict': 1}}
    start = time.monotonic()
    request = urllib.request.Request('http://ollama:11434/api/generate', data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
    if result.get('done') is not True:
        raise RuntimeError('Préchauffage incomplet')
    print(json.dumps({'event': 'locked_llm_prewarmed', 'model': lock['model'], 'digest': lock['digest'],
                      'elapsed_seconds': time.monotonic() - start,
                      'load_duration_ns': result.get('load_duration'),
                      'scope': 'One-token warmup, not a client draft or quality validation'}))


if __name__ == '__main__':
    main()
