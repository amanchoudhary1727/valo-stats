import json
import os
import sys
from pathlib import Path
from typing import Any

import requests


# ============================================================
# Configuration
# ============================================================

API_BASE = "https://api.henrikdev.xyz"

STATE_FILE = Path("state.json")

API_KEY = os.getenv("VALORANT_API_KEY")
VALORANT_NAME = os.getenv("VALORANT_NAME")
VALORANT_TAG = os.getenv("VALORANT_TAG")
VALORANT_REGION = os.getenv("VALORANT_REGION", "ap")
VALORANT_PLATFORM = os.getenv("VALORANT_PLATFORM", "pc")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

MATCH_LIMIT = 10
STATE_LIMIT = 50

REQUEST_TIMEOUT = 30


# ============================================================
# Validation
# ============================================================

def validate_config():
    required = {
        "VALORANT_API_KEY": API_KEY,
        "VALORANT_NAME": VALORANT_NAME,
        "VALORANT_TAG": VALORANT_TAG,
        "VALORANT_REGION": VALORANT_REGION,
        "VALORANT_PLATFORM": VALORANT_PLATFORM,
        "DISCORD_WEBHOOK_URL": DISCORD_WEBHOOK_URL,
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


# ============================================================
# HTTP helpers
# ============================================================

def api_get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "Authorization": API_KEY,
        "Accept": "application/json",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"HenrikDev API request failed: "
            f"{response.status_code} - {response.text[:500]}"
        )

    data = response.json()

    if not isinstance(data, dict):
        raise RuntimeError("HenrikDev API returned an unexpected response.")

    return data


# ============================================================
# State management
# ============================================================

def load_state() -> list[str]:
    if not STATE_FILE.exists():
        print("[STATE] state.json does not exist. Creating empty state.")
        return []

    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)

        if not isinstance(state, dict):
            raise ValueError("state.json must contain an object.")

        processed_matches = state.get("processed_matches", [])

        if not isinstance(processed_matches, list):
            raise ValueError("processed_matches must be an array.")

        return [str(match_id) for match_id in processed_matches]

    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Invalid state.json: {exc}") from exc


def save_state(processed_matches: list[str]):
    unique_matches = list(dict.fromkeys(processed_matches))

    state = {
        "processed_matches": unique_matches[-STATE_LIMIT:]
    }

    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)

        # newline keeps git diffs clean
        file.write("\n")

    print(
        f"[STATE] Saved {len(state['processed_matches'])} "
        f"processed match IDs."
    )


# ============================================================
# HenrikDev - Match History
# ============================================================

def fetch_matches() -> list[dict[str, Any]]:
    url = (
        f"{API_BASE}/valorant/v4/matches/"
        f"{VALORANT_REGION}/"
        f"{VALORANT_PLATFORM}/"
        f"{VALORANT_NAME}/"
        f"{VALORANT_TAG}"
    )

    params = {
        "mode": "competitive",
        "size": MATCH_LIMIT,
    }

    print("[API] Fetching competitive match history...")

    response = api_get(url, params)

    matches = response.get("data", [])

    if not isinstance(matches, list):
        raise RuntimeError("Unexpected match history response.")

    print(f"[API] Received {len(matches)} competitive matches.")

    return matches


# ============================================================
# Match parsing
# ============================================================

def get_match_id(match: dict[str, Any]) -> str | None:
    metadata = match.get("metadata", {})

    return metadata.get("match_id")


def get_player_stats(
    match: dict[str, Any],
) -> tuple[int, int]:
    """
    Extract the configured player's kills and deaths.

    HenrikDev v4 match data uses:
        players: [
            {
                puuid,
                name,
                tag,
                stats: {
                    kills,
                    deaths,
                    ...
                }
            }
        ]
    """

    players = match.get("players", [])

    if not isinstance(players, list):
        raise RuntimeError("Unexpected players structure in match.")

    target_name = VALORANT_NAME.lower()
    target_tag = VALORANT_TAG.lower()

    for player in players:
        name = str(player.get("name", "")).lower()
        tag = str(player.get("tag", "")).lower()

        if name == target_name and tag == target_tag:
            stats = player.get("stats", {})

            kills = int(stats.get("kills", 0))
            deaths = int(stats.get("deaths", 0))

            return kills, deaths

    raise RuntimeError(
        f"Could not find player {VALORANT_NAME}#{VALORANT_TAG} "
        f"in match data."
    )


# ============================================================
# HenrikDev - MMR History
# ============================================================

def fetch_mmr_history() -> list[dict[str, Any]]:
    url = (
        f"{API_BASE}/valorant/v1/mmr-history/"
        f"{VALORANT_REGION}/"
        f"{VALORANT_NAME}/"
        f"{VALORANT_TAG}"
    )

    print("[API] Fetching MMR history...")

    response = api_get(url)

    history = response.get("data", [])

    if not isinstance(history, list):
        raise RuntimeError("Unexpected MMR history response.")

    print(f"[API] Received {len(history)} MMR entries.")

    return history


# ============================================================
# MMR lookup
# ============================================================

def build_mmr_lookup(
    mmr_history: list[dict[str, Any]],
) -> dict[str, int]:

    lookup: dict[str, int] = {}

    for entry in mmr_history:
        match_id = entry.get("match_id")

        if not match_id:
            continue

        # v1 field documented by HenrikDev.
        rr_change = entry.get("mmr_change_to_last_game")

        if rr_change is None:
            # Defensive fallback for possible response variations.
            rr_change = entry.get("last_mmr_change")

        if rr_change is None:
            continue

        try:
            lookup[str(match_id)] = int(rr_change)
        except (TypeError, ValueError):
            continue

    return lookup


# ============================================================
# Find unprocessed matches
# ============================================================

def get_new_matches(
    matches: list[dict[str, Any]],
    processed_ids: list[str],
) -> list[dict[str, Any]]:

    processed_set = set(processed_ids)

    new_matches = []

    for match in matches:
        match_id = get_match_id(match)

        if not match_id:
            print("[WARNING] Match without match_id encountered.")
            continue

        if match_id in processed_set:
            continue

        new_matches.append(match)

    return new_matches


# ============================================================
# Aggregate session
# ============================================================

def calculate_session(
    new_matches: list[dict[str, Any]],
    mmr_lookup: dict[str, int],
) -> dict[str, Any]:

    total_kills = 0
    total_deaths = 0
    total_rr = 0

    match_summaries = []

    for match in new_matches:
        match_id = get_match_id(match)

        if not match_id:
            continue

        # ----------------------------------------------------
        # RR must exist for every competitive match.
        # Otherwise we abort instead of sending inaccurate data.
        # ----------------------------------------------------

        if match_id not in mmr_lookup:
            raise RuntimeError(
                f"MMR history does not contain match {match_id}. "
                "Aborting so an incomplete digest is not sent."
            )

        kills, deaths = get_player_stats(match)

        rr_change = mmr_lookup[match_id]

        total_kills += kills
        total_deaths += deaths
        total_rr += rr_change

        metadata = match.get("metadata", {})

        map_data = metadata.get("map", {})
        map_name = (
            map_data.get("name", "Unknown")
            if isinstance(map_data, dict)
            else str(map_data)
        )

        match_summaries.append(
            {
                "match_id": match_id,
                "kills": kills,
                "deaths": deaths,
                "rr": rr_change,
                "map": map_name,
            }
        )

    matches_played = len(match_summaries)

    if total_deaths == 0:
        kd_ratio = float(total_kills)
    else:
        kd_ratio = total_kills / total_deaths

    return {
        "matches_played": matches_played,
        "kills": total_kills,
        "deaths": total_deaths,
        "kd_ratio": kd_ratio,
        "net_rr": total_rr,
        "matches": match_summaries,
    }


# ============================================================
# Discord Webhook
# ============================================================

def get_embed_color(net_rr: int) -> int:
    if net_rr < 0:
        return 0xFF0000

    return 0x00FF00


def build_discord_payload(session: dict[str, Any]) -> dict[str, Any]:
    net_rr = session["net_rr"]

    rr_text = f"+{net_rr}" if net_rr >= 0 else str(net_rr)

    embed = {
        "title": "🎮 Valorant Session Digest",
        "description": (
            f"**{session['matches_played']}** competitive "
            f"match{'es' if session['matches_played'] != 1 else ''} "
            "played since the previous digest."
        ),
        "color": get_embed_color(net_rr),
        "fields": [
            {
                "name": "🎯 Matches Played",
                "value": str(session["matches_played"]),
                "inline": True,
            },
            {
                "name": "📈 Net RR",
                "value": rr_text,
                "inline": True,
            },
            {
                "name": "⚔️ Session K/D",
                "value": f"{session['kd_ratio']:.2f}",
                "inline": True,
            },
        ],
        "footer": {
            "text": (
                f"{VALORANT_NAME}#{VALORANT_TAG} • "
                "Valorant Session Digest"
            )
        },
    }

    return {
        "username": "Valorant Session Digest",
        "embeds": [embed],
    }


def send_discord_webhook(payload: dict[str, Any]):
    print("[DISCORD] Sending session digest...")

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"Discord webhook failed: "
            f"{response.status_code} - {response.text[:500]}"
        )

    print("[DISCORD] Digest delivered successfully.")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("VALORANT SESSION DIGEST")
    print("=" * 60)

    validate_config()

    # --------------------------------------------------------
    # 1. Load state
    # --------------------------------------------------------

    processed_ids = load_state()

    print(
        f"[STATE] Previously processed matches: "
        f"{len(processed_ids)}"
    )

    # --------------------------------------------------------
    # 2. Fetch APIs
    # --------------------------------------------------------

    matches = fetch_matches()
    mmr_history = fetch_mmr_history()

    # --------------------------------------------------------
    # 3. Identify new matches
    # --------------------------------------------------------

    new_matches = get_new_matches(
        matches,
        processed_ids,
    )

    print(
        f"[STATE] New unprocessed matches: "
        f"{len(new_matches)}"
    )

    # --------------------------------------------------------
    # 4. SILENCE PROTOCOL
    # --------------------------------------------------------

    if not new_matches:
        print(
            "[SILENCE] No new matches detected."
        )
        print(
            "[SILENCE] Skipping Discord webhook."
        )
        print(
            "[SILENCE] state.json remains unchanged."
        )
        print("[DONE] Nothing to do.")

        return 0

    # --------------------------------------------------------
    # 5. Build MMR lookup
    # --------------------------------------------------------

    mmr_lookup = build_mmr_lookup(mmr_history)

    # --------------------------------------------------------
    # 6. Aggregate
    # --------------------------------------------------------

    session = calculate_session(
        new_matches,
        mmr_lookup,
    )

    print()
    print("[SESSION]")
    print(f"Matches : {session['matches_played']}")
    print(f"Kills   : {session['kills']}")
    print(f"Deaths  : {session['deaths']}")
    print(f"K/D     : {session['kd_ratio']:.2f}")
    print(f"Net RR  : {session['net_rr']}")
    print()

    # --------------------------------------------------------
    # 7. Send Discord
    # --------------------------------------------------------

    payload = build_discord_payload(session)

    send_discord_webhook(payload)

    # --------------------------------------------------------
    # 8. Only AFTER successful Discord delivery:
    #    update state.
    # --------------------------------------------------------

    new_ids = [
        get_match_id(match)
        for match in new_matches
        if get_match_id(match)
    ]

    updated_state = processed_ids + new_ids

    save_state(updated_state)

    print("[DONE] Session digest completed successfully.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())

    except KeyboardInterrupt:
        print("\n[ERROR] Interrupted by user.")
        sys.exit(130)

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)
