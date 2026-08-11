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

# HenrikDev v4 currently allows up to 10 matches per request.
MATCH_LIMIT = 10

# Keep only the latest 50 processed match IDs.
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

    missing = [
        key
        for key, value in required.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
        )


# ============================================================
# HTTP helpers
# ============================================================

def api_get(
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:

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
            f"{response.status_code} - "
            f"{response.text[:500]}"
        )

    data = response.json()

    if not isinstance(data, dict):
        raise RuntimeError(
            "HenrikDev API returned an unexpected response."
        )

    return data


# ============================================================
# State management
# ============================================================

def load_state() -> list[str]:

    if not STATE_FILE.exists():
        print(
            "[STATE] state.json does not exist. "
            "Creating empty state."
        )
        return []

    try:
        with STATE_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            state = json.load(file)

        if not isinstance(state, dict):
            raise ValueError(
                "state.json must contain an object."
            )

        processed_matches = state.get(
            "processed_matches",
            []
        )

        if not isinstance(processed_matches, list):
            raise ValueError(
                "processed_matches must be an array."
            )

        return [
            str(match_id)
            for match_id in processed_matches
        ]

    except (
        json.JSONDecodeError,
        ValueError
    ) as exc:

        raise RuntimeError(
            f"Invalid state.json: {exc}"
        ) from exc


def save_state(processed_matches: list[str]):

    # Remove duplicates while preserving order.
    unique_matches = list(
        dict.fromkeys(processed_matches)
    )

    state = {
        "processed_matches": unique_matches[
            -STATE_LIMIT:
        ]
    }

    with STATE_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            state,
            file,
            indent=2
        )

        file.write("\n")

    print(
        f"[STATE] Saved "
        f"{len(state['processed_matches'])} "
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
        # IMPORTANT:
        # Only request Competitive matches.
        "mode": "competitive",

        "size": MATCH_LIMIT,
    }

    print(
        "[API] Fetching competitive match history..."
    )

    response = api_get(
        url,
        params
    )

    matches = response.get(
        "data",
        []
    )

    if not isinstance(matches, list):
        raise RuntimeError(
            "Unexpected match history response."
        )

    print(
        f"[API] Received "
        f"{len(matches)} competitive matches."
    )

    return matches


# ============================================================
# Match parsing
# ============================================================

def get_match_id(
    match: dict[str, Any]
) -> str | None:

    metadata = match.get(
        "metadata",
        {}
    )

    if not isinstance(metadata, dict):
        return None

    # Current v4 structure.
    match_id = metadata.get("match_id")

    # Defensive fallback for older structures.
    if not match_id:
        match_id = metadata.get("matchid")

    return (
        str(match_id)
        if match_id
        else None
    )


def get_match_mode(
    match: dict[str, Any]
) -> str:

    metadata = match.get(
        "metadata",
        {}
    )

    if not isinstance(metadata, dict):
        return ""

    # Current v4 structure:
    #
    # queue:
    # {
    #     "id": "competitive",
    #     "name": "Competitive",
    #     ...
    # }
    queue = metadata.get(
        "queue",
        {}
    )

    if isinstance(queue, dict):

        queue_id = queue.get("id")

        if queue_id:
            return str(queue_id).lower()

        queue_name = queue.get("name")

        if queue_name:
            return str(queue_name).lower()

    # Defensive fallback.
    mode_id = metadata.get("mode_id")

    if mode_id:
        return str(mode_id).lower()

    mode = metadata.get("mode")

    if mode:
        return str(mode).lower()

    return ""


def is_competitive_match(
    match: dict[str, Any]
) -> bool:

    mode = get_match_mode(match)

    return mode in {
        "competitive",
        "competitive mode",
    }


def get_map_name(
    match: dict[str, Any]
) -> str:

    metadata = match.get(
        "metadata",
        {}
    )

    if not isinstance(metadata, dict):
        return "Unknown"

    map_data = metadata.get(
        "map",
        {}
    )

    # Current v4:
    #
    # "map": {
    #     "id": "...",
    #     "name": "Ascent"
    # }
    if isinstance(map_data, dict):

        return str(
            map_data.get(
                "name",
                "Unknown"
            )
        )

    # Older response format:
    # "map": "Ascent"
    if isinstance(map_data, str):
        return map_data

    return "Unknown"


def get_match_time(
    match: dict[str, Any]
) -> str:

    metadata = match.get(
        "metadata",
        {}
    )

    if not isinstance(metadata, dict):
        return ""

    started_at = metadata.get(
        "started_at"
    )

    if started_at:
        return str(started_at)

    # Older format fallback.
    started_at = metadata.get(
        "game_start_patched"
    )

    if started_at:
        return str(started_at)

    return ""


def get_player(
    match: dict[str, Any]
) -> dict[str, Any]:

    players = match.get(
        "players",
        []
    )

    if not isinstance(players, list):
        raise RuntimeError(
            "Unexpected players structure "
            "in match."
        )

    target_name = (
        VALORANT_NAME.lower()
    )

    target_tag = (
        VALORANT_TAG.lower()
    )

    for player in players:

        name = str(
            player.get(
                "name",
                ""
            )
        ).lower()

        tag = str(
            player.get(
                "tag",
                ""
            )
        ).lower()

        if (
            name == target_name
            and tag == target_tag
        ):
            return player

    raise RuntimeError(
        f"Could not find player "
        f"{VALORANT_NAME}#{VALORANT_TAG} "
        f"in match data."
    )


def get_player_stats(
    match: dict[str, Any]
) -> tuple[int, int]:

    player = get_player(match)

    stats = player.get(
        "stats",
        {}
    )

    if not isinstance(stats, dict):
        raise RuntimeError(
            "Unexpected player stats structure."
        )

    kills = int(
        stats.get(
            "kills",
            0
        )
    )

    deaths = int(
        stats.get(
            "deaths",
            0
        )
    )

    return kills, deaths


def get_player_agent(
    match: dict[str, Any]
) -> str:

    player = get_player(match)

    agent = player.get(
        "agent"
    )

    # Current v4 structure:
    #
    # "agent": {
    #     "id": "...",
    #     "name": "Sova"
    # }
    if isinstance(agent, dict):

        name = agent.get(
            "name"
        )

        if name:
            return str(name)

    # Defensive fallback for older structures.
    character = player.get(
        "character"
    )

    if character:
        return str(character)

    return "Unknown"


# ============================================================
# Match result
# ============================================================

def get_match_result(
    match: dict[str, Any]
) -> str:

    """
    Determine whether the configured player won/lost.

    Current v4 match responses identify the player's
    team through player["team_id"].

    Some older responses use player["team"].

    If the response does not expose a reliable team
    result, return UNKNOWN rather than guessing.
    """

    player = get_player(match)

    player_team = player.get(
        "team_id"
    )

    if not player_team:
        player_team = player.get(
            "team"
        )

    if not player_team:
        return "UNKNOWN"

    # --------------------------------------------------------
    # Current v4 responses may contain team result information.
    # --------------------------------------------------------

    teams = match.get(
        "teams"
    )

    if isinstance(teams, dict):

        team_data = teams.get(
            player_team
        )

        if isinstance(team_data, dict):

            won = team_data.get(
                "won"
            )

            if won is True:
                return "WIN"

            if won is False:
                return "LOSS"

    # --------------------------------------------------------
    # Some responses expose red/blue team information.
    # --------------------------------------------------------

    if isinstance(teams, list):

        for team in teams:

            if not isinstance(
                team,
                dict
            ):
                continue

            team_id = (
                team.get("id")
                or team.get("team_id")
                or team.get("team")
            )

            if (
                team_id == player_team
                and "won" in team
            ):

                if team["won"] is True:
                    return "WIN"

                if team["won"] is False:
                    return "LOSS"

    return "UNKNOWN"


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

    print(
        "[API] Fetching MMR history..."
    )

    response = api_get(url)

    history = response.get(
        "data",
        []
    )

    if not isinstance(history, list):
        raise RuntimeError(
            "Unexpected MMR history response."
        )

    print(
        f"[API] Received "
        f"{len(history)} MMR entries."
    )

    return history


# ============================================================
# MMR lookup
# ============================================================

def build_mmr_lookup(
    mmr_history: list[dict[str, Any]]
) -> dict[str, int]:

    lookup: dict[str, int] = {}

    for entry in mmr_history:

        match_id = entry.get(
            "match_id"
        )

        if not match_id:
            continue

        rr_change = entry.get(
            "mmr_change_to_last_game"
        )

        if rr_change is None:

            # Defensive fallback.
            rr_change = entry.get(
                "last_mmr_change"
            )

        if rr_change is None:
            continue

        try:

            lookup[
                str(match_id)
            ] = int(rr_change)

        except (
            TypeError,
            ValueError
        ):

            continue

    return lookup


# ============================================================
# Find unprocessed matches
# ============================================================

def get_new_matches(
    matches: list[dict[str, Any]],
    processed_ids: list[str]
) -> list[dict[str, Any]]:

    processed_set = set(
        processed_ids
    )

    new_matches = []

    for match in matches:

        match_id = get_match_id(
            match
        )

        if not match_id:

            print(
                "[WARNING] Match without "
                "match_id encountered."
            )

            continue

        # ----------------------------------------------------
        # SECONDARY COMPETITIVE CHECK
        #
        # The API request already uses:
        #
        #     mode=competitive
        #
        # This check makes sure we don't accidentally
        # process Deathmatch/TDM/etc. if an unexpected
        # response ever appears.
        # ----------------------------------------------------

        if not is_competitive_match(
            match
        ):

            print(
                f"[FILTER] Ignoring non-competitive "
                f"match {match_id}"
            )

            continue

        if match_id in processed_set:
            continue

        new_matches.append(
            match
        )

    return new_matches


# ============================================================
# Sort matches chronologically
# ============================================================

def get_match_timestamp(
    match: dict[str, Any]
) -> str:

    metadata = match.get(
        "metadata",
        {}
    )

    if not isinstance(
        metadata,
        dict
    ):
        return ""

    return str(
        metadata.get(
            "started_at",
            ""
        )
    )


def sort_matches_oldest_first(
    matches: list[dict[str, Any]]
) -> list[dict[str, Any]]:

    return sorted(
        matches,
        key=get_match_timestamp
    )


# ============================================================
# Aggregate session
# ============================================================

def calculate_session(
    new_matches: list[dict[str, Any]],
    mmr_lookup: dict[str, int]
) -> dict[str, Any]:

    total_kills = 0
    total_deaths = 0
    total_rr = 0

    match_summaries = []

    # Show games in chronological order:
    #
    # Game 1 → Game 2 → Game 3
    #
    ordered_matches = sort_matches_oldest_first(
        new_matches
    )

    for match in ordered_matches:

        match_id = get_match_id(
            match
        )

        if not match_id:
            continue

        # ----------------------------------------------------
        # RR must exist for every competitive match.
        #
        # If it doesn't, abort without:
        #
        #   - Discord message
        #   - state update
        #
        # This prevents losing a match because its RR
        # wasn't available yet.
        # ----------------------------------------------------

        if match_id not in mmr_lookup:

            raise RuntimeError(
                f"MMR history does not contain "
                f"match {match_id}. "
                "Aborting so an incomplete "
                "digest is not sent."
            )

        kills, deaths = get_player_stats(
            match
        )

        rr_change = mmr_lookup[
            match_id
        ]

        map_name = get_map_name(
            match
        )

        agent = get_player_agent(
            match
        )

        result = get_match_result(
            match
        )

        total_kills += kills
        total_deaths += deaths
        total_rr += rr_change

        match_summaries.append(
            {
                "match_id": match_id,
                "kills": kills,
                "deaths": deaths,
                "rr": rr_change,
                "map": map_name,
                "agent": agent,
                "result": result,
            }
        )

    matches_played = len(
        match_summaries
    )

    if total_deaths == 0:

        kd_ratio = float(
            total_kills
        )

    else:

        kd_ratio = (
            total_kills
            / total_deaths
        )

    return {
        "matches_played": matches_played,
        "kills": total_kills,
        "deaths": total_deaths,
        "kd_ratio": kd_ratio,
        "net_rr": total_rr,
        "matches": match_summaries,
    }


# ============================================================
# Discord formatting
# ============================================================

def get_embed_color(
    net_rr: int
) -> int:

    if net_rr < 0:
        return 0xFF0000

    return 0x00FF00


def format_rr(
    rr: int
) -> str:

    if rr > 0:
        return f"+{rr}"

    return str(rr)


def format_match_line(
    index: int,
    match: dict[str, Any]
) -> str:

    result = match["result"]

    if result == "WIN":

        icon = "🟢"
        result_text = "WIN"

    elif result == "LOSS":

        icon = "🔴"
        result_text = "LOSS"

    else:

        icon = "⚪"
        result_text = "?"

    kills = match["kills"]
    deaths = match["deaths"]
    rr = format_rr(
        match["rr"]
    )

    map_name = match["map"]
    agent = match["agent"]

    return (
        f"`#{index}` "
        f"{icon} **{result_text}** "
        f"| `{kills}/{deaths}` "
        f"| **{rr} RR** "
        f"| `{map_name}` "
        f"| `{agent}`"
    )


def build_match_details(
    matches: list[dict[str, Any]]
) -> str:

    lines = []

    for index, match in enumerate(
        matches,
        start=1
    ):

        lines.append(
            format_match_line(
                index,
                match
            )
        )

    return "\n".join(lines)


# ============================================================
# Discord Webhook
# ============================================================

def build_discord_payload(
    session: dict[str, Any]
) -> dict[str, Any]:

    net_rr = session["net_rr"]

    rr_text = format_rr(
        net_rr
    )

    match_details = build_match_details(
        session["matches"]
    )

    embed = {
        "title": "🎮 Valorant Session Digest",

        "description": (
            f"**{session['matches_played']}** "
            "competitive "
            f"match"
            f"{'es' if session['matches_played'] != 1 else ''} "
            "played since the previous digest."
        ),

        "color": get_embed_color(
            net_rr
        ),

        "fields": [
            {
                "name": "📊 Session Summary",
                "value": (
                    f"**Matches:** "
                    f"{session['matches_played']}\n"
                    f"**Net RR:** "
                    f"{rr_text}\n"
                    f"**Session K/D:** "
                    f"{session['kd_ratio']:.2f}"
                ),
                "inline": False,
            },

            {
                "name": "🎯 Match Details",
                "value": match_details,
                "inline": False,
            },
        ],

        "footer": {
            "text": (
                f"{VALORANT_NAME}#{VALORANT_TAG} "
                "• Valorant Session Digest"
            )
        },
    }

    return {
        "username": "Valorant Session Digest",
        "embeds": [embed],
    }


def send_discord_webhook(
    payload: dict[str, Any]
):

    print(
        "[DISCORD] Sending session digest..."
    )

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code not in (
        200,
        204
    ):

        raise RuntimeError(
            f"Discord webhook failed: "
            f"{response.status_code} - "
            f"{response.text[:500]}"
        )

    print(
        "[DISCORD] Digest delivered successfully."
    )


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
    # 2. Fetch API data
    # --------------------------------------------------------

    matches = fetch_matches()

    mmr_history = fetch_mmr_history()

    # --------------------------------------------------------
    # 3. Identify new competitive matches
    # --------------------------------------------------------

    new_matches = get_new_matches(
        matches,
        processed_ids
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

        print(
            "[DONE] Nothing to do."
        )

        return 0

    # --------------------------------------------------------
    # 5. Build MMR lookup
    # --------------------------------------------------------

    mmr_lookup = build_mmr_lookup(
        mmr_history
    )

    # --------------------------------------------------------
    # 6. Aggregate session
    # --------------------------------------------------------

    session = calculate_session(
        new_matches,
        mmr_lookup
    )

    print()
    print("[SESSION]")
    print(
        f"Matches : "
        f"{session['matches_played']}"
    )
    print(
        f"Kills   : "
        f"{session['kills']}"
    )
    print(
        f"Deaths  : "
        f"{session['deaths']}"
    )
    print(
        f"K/D     : "
        f"{session['kd_ratio']:.2f}"
    )
    print(
        f"Net RR  : "
        f"{format_rr(session['net_rr'])}"
    )

    print()
    print("[MATCHES]")

    for index, match in enumerate(
        session["matches"],
        start=1
    ):

        print(
            format_match_line(
                index,
                match
            )
        )

    print()

    # --------------------------------------------------------
    # 7. Build + send Discord payload
    # --------------------------------------------------------

    payload = build_discord_payload(
        session
    )

    send_discord_webhook(
        payload
    )

    # --------------------------------------------------------
    # 8. ONLY AFTER SUCCESSFUL DISCORD DELIVERY:
    #
    #    Update state.
    # --------------------------------------------------------

    new_ids = [
        get_match_id(match)
        for match in new_matches
        if get_match_id(match)
    ]

    updated_state = (
        processed_ids
        + new_ids
    )

    save_state(
        updated_state
    )

    print(
        "[DONE] Session digest "
        "completed successfully."
    )

    return 0


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    try:

        sys.exit(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\n[ERROR] Interrupted by user."
        )

        sys.exit(130)

    except Exception as exc:

        print(
            f"\n[ERROR] {exc}"
        )

        sys.exit(1)
