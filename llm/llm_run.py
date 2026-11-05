"""
Run the code-reading LLM baseline on a local GPU through Ollama. Standard library only.

  1. Install Ollama (https://ollama.com) and pull the model:   ollama pull qwen2.5-coder:7b
  2. From this folder:                                         python llm_run.py
  3. Send back answers.jsonl and run_info.json.

Greedy decoding (temperature 0, fixed seed), so a rerun with the same model digest gives
the same answers. The script is resumable: rerun it after an interruption and it skips
prompts already answered. Options: --model NAME, --host URL, --limit N (smoke test).
"""
import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def call(host, path, payload=None, timeout=600):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(host + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def parse(text):
    t = text.strip().upper()
    if t.startswith("YES"):
        return "YES"
    if t.startswith("NO"):
        return "NO"
    return "YES" if "YES" in t and "NO" not in t else ("NO" if "NO" in t else "UNPARSED")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--prompts", default=os.path.join(HERE, "prompts.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "answers.jsonl"))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    tags = call(a.host, "/api/tags")
    digest = next((m.get("digest") for m in tags.get("models", [])
                   if m.get("name") == a.model or m.get("model") == a.model), None)
    if digest is None:
        sys.exit(f"Model {a.model} not found. Run: ollama pull {a.model}")
    options = {"temperature": 0, "seed": 20260902, "num_predict": 4, "num_ctx": 4096, "top_k": 1}
    with open(os.path.join(HERE, "run_info.json"), "w", encoding="utf-8") as fh:
        json.dump({"model": a.model, "digest": digest, "options": options,
                   "started": time.strftime("%Y-%m-%d %H:%M:%S")}, fh, indent=2)

    done = set()
    if os.path.exists(a.out):
        with open(a.out, encoding="utf-8") as fh:
            done = {json.loads(line)["id"] for line in fh if line.strip()}
    with open(a.prompts, encoding="utf-8") as fh:
        todo = [json.loads(line) for line in fh if line.strip()]
    todo = [p for p in todo if p["id"] not in done]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(done)} already answered, {len(todo)} to go, model {a.model} ({digest[:12]})")
    t0 = time.time()
    with open(a.out, "a", encoding="utf-8") as out:
        for i, p in enumerate(todo, 1):
            r = call(a.host, "/api/generate", {"model": a.model, "prompt": p["prompt"],
                                               "stream": False, "options": options})
            raw = r.get("response", "")
            out.write(json.dumps({"id": p["id"], "raw": raw, "answer": parse(raw)}) + "\n")
            if i % 50 == 0 or i == len(todo):
                out.flush()
                rate = i / (time.time() - t0)
                print(f"  {i}/{len(todo)}  {rate:.1f}/s  eta {(len(todo) - i) / rate / 60:.1f} min")
    print("done:", a.out)


if __name__ == "__main__":
    main()
