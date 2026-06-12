"""Phase 1 stub: writes an empty array to $RUNNER_TEMP/chorus_transcripts.json. Phase 2 replaces this with real Chorus API integration (see CHO-01..CHO-04)."""

import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fetch_chorus")

if __name__ == "__main__":
    runner_temp = os.environ.get("RUNNER_TEMP", ".")
    out_path = os.path.join(runner_temp, "chorus_transcripts.json")

    # Phase 1 stub: Chorus integration is Phase 2. Writing an empty array
    # keeps the file contract stable so generate_campaign.py can always
    # safely json.load() this file. Phase 2 will replace the body of this
    # script with the real Chorus API integration (CHO-01..CHO-04) without
    # changing the output schema (still a JSON array of transcript objects).
    transcripts: list = []

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(transcripts, f, indent=2)

    log.info(f"Wrote {out_path}: Chorus integration is disabled in Phase 1 (stub). 0 transcripts. Phase 2 will replace this with real fetching.")
