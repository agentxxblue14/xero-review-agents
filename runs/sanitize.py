"""Drops the session 'init' events (they list the tools, skills and plugins installed on the
machine that ran them) so the published logs contain only this repo's run."""
import json, pathlib, sys
for f in pathlib.Path(__file__).parent.rglob("session.jsonl"):
    keep = [l for l in f.read_text(encoding="utf8").splitlines()
            if l.strip() and not (json.loads(l).get("type") == "system" and json.loads(l).get("subtype") == "init")]
    f.write_text("\n".join(keep) + "\n", encoding="utf8")
    print(f, len(keep))
# Local machine paths were also replaced with repo-relative ones before publishing.
