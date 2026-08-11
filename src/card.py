from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# Card configuration
# ============================================================

WIDTH = 1200

BACKGROUND = "#111111"
PANEL = "#181818"
BORDER = "#2A2A2A"

TEXT = "#F5F5F5"
MUTED = "#8F8F8F"

GREEN = "#7CFF4F"
RED = "#FF4655"

OUTPUT_FILE = Path("session_digest.png")


# ============================================================
# Fonts
# ============================================================

def load_font(size: int, bold: bool = False):

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/"
        + (
            "LiberationSans-Bold.ttf"
            if bold
            else "LiberationSans-Regular.ttf"
        ),
    ]

    for path in font_paths:

        if Path(path).exists():
            return ImageFont.truetype(
                path,
                size
            )

    return ImageFont.load_default()


FONT_TITLE = load_font(42, True)
FONT_PLAYER = load_font(24, False)

FONT_STAT = load_font(42, True)
FONT_LABEL = load_font(18, False)

FONT_MATCH = load_font(22, False)
FONT_MATCH_BOLD = load_font(22, True)

FONT_FOOTER = load_font(16, False)


# ============================================================
# Helpers
# ============================================================

def rounded_rectangle(
    draw,
    xy,
    radius,
    fill,
    outline=None,
    width=1
):
    draw.rounded_rectangle(
        xy,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width
    )


def rr_text(rr):

    if rr > 0:
        return f"+{rr}"

    return str(rr)


# ============================================================
# Generate card
# ============================================================

def generate_session_card(session, player_name, player_tag):

    matches = session["matches"]

    # --------------------------------------------------------
    # Dynamic height
    # --------------------------------------------------------

    header_height = 170
    summary_height = 190
    match_header_height = 70
    match_row_height = 55
    footer_height = 80

    height = (
        header_height
        + summary_height
        + match_header_height
        + (
            len(matches)
            * match_row_height
        )
        + footer_height
    )

    # --------------------------------------------------------
    # Canvas
    # --------------------------------------------------------

    image = Image.new(
        "RGB",
        (WIDTH, height),
        BACKGROUND
    )

    draw = ImageDraw.Draw(image)

    # --------------------------------------------------------
    # Outer panel
    # --------------------------------------------------------

    rounded_rectangle(
        draw,
        (
            30,
            30,
            WIDTH - 30,
            height - 30
        ),
        24,
        fill=PANEL,
        outline=BORDER,
        width=2
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    x = 70
    y = 65

    draw.text(
        (x, y),
        "VALORANT SESSION",
        font=FONT_TITLE,
        fill=TEXT
    )

    draw.text(
        (x, y + 55),
        "SESSION DIGEST",
        font=FONT_LABEL,
        fill=MUTED
    )

    player_text = (
        f"{player_name}#{player_tag}"
    )

    draw.text(
        (
            WIDTH - 70
            - draw.textbbox(
                (0, 0),
                player_text,
                font=FONT_PLAYER
            )[2],
            y + 15
        ),
        player_text,
        font=FONT_PLAYER,
        fill=TEXT
    )

    # --------------------------------------------------------
    # Summary boxes
    # --------------------------------------------------------

    summary_y = header_height

    box_margin = 70
    gap = 20

    box_width = (
        WIDTH
        - (box_margin * 2)
        - (gap * 2)
    ) // 3

    stats = [
        (
            "MATCHES",
            str(session["matches_played"])
        ),
        (
            "NET RR",
            rr_text(session["net_rr"])
        ),
        (
            "SESSION K/D",
            f"{session['kd_ratio']:.2f}"
        ),
    ]

    for index, (label, value) in enumerate(stats):

        left = (
            box_margin
            + index
            * (box_width + gap)
        )

        right = left + box_width

        rounded_rectangle(
            draw,
            (
                left,
                summary_y,
                right,
                summary_y + 130
            ),
            16,
            fill=BACKGROUND,
            outline=BORDER,
            width=2
        )

        draw.text(
            (
                left + 25,
                summary_y + 20
            ),
            label,
            font=FONT_LABEL,
            fill=MUTED
        )

        value_color = TEXT

        if label == "NET RR":

            value_color = (
                GREEN
                if session["net_rr"] >= 0
                else RED
            )

        draw.text(
            (
                left + 25,
                summary_y + 55
            ),
            value,
            font=FONT_STAT,
            fill=value_color
        )

    # --------------------------------------------------------
    # Match section
    # --------------------------------------------------------

    match_y = (
        summary_y
        + summary_height
    )

    draw.text(
        (
            70,
            match_y
        ),
        "MATCH HISTORY",
        font=FONT_MATCH_BOLD,
        fill=TEXT
    )

    # Column positions

    col_number = 70
    col_result = 130
    col_kd = 330
    col_rr = 500
    col_map = 680
    col_agent = 920

    header_y = match_y + 45

    headers = [
        (col_number, "#"),
        (col_result, "RESULT"),
        (col_kd, "K/D"),
        (col_rr, "RR"),
        (col_map, "MAP"),
        (col_agent, "AGENT"),
    ]

    for x, label in headers:

        draw.text(
            (x, header_y),
            label,
            font=FONT_LABEL,
            fill=MUTED
        )

    # --------------------------------------------------------
    # Match rows
    # --------------------------------------------------------

    row_y = header_y + 35

    for index, match in enumerate(
        matches,
        start=1
    ):

        result = match["result"]

        if result == "WIN":

            result_color = GREEN

        elif result == "LOSS":

            result_color = RED

        else:

            result_color = MUTED

        rr = match["rr"]

        rr_color = (
            GREEN
            if rr > 0
            else RED
            if rr < 0
            else MUTED
        )

        # Row separator

        draw.line(
            (
                70,
                row_y - 10,
                WIDTH - 70,
                row_y - 10
            ),
            fill=BORDER,
            width=1
        )

        # Number

        draw.text(
            (
                col_number,
                row_y
            ),
            f"{index:02d}",
            font=FONT_MATCH,
            fill=MUTED
        )

        # Result

        draw.text(
            (
                col_result,
                row_y
            ),
            result,
            font=FONT_MATCH_BOLD,
            fill=result_color
        )

        # K/D

        draw.text(
            (
                col_kd,
                row_y
            ),
            f"{match['kills']}/{match['deaths']}",
            font=FONT_MATCH,
            fill=TEXT
        )

        # RR

        draw.text(
            (
                col_rr,
                row_y
            ),
            rr_text(rr),
            font=FONT_MATCH_BOLD,
            fill=rr_color
        )

        # Map

        draw.text(
            (
                col_map,
                row_y
            ),
            match["map"],
            font=FONT_MATCH,
            fill=TEXT
        )

        # Agent

        draw.text(
            (
                col_agent,
                row_y
            ),
            match["agent"],
            font=FONT_MATCH,
            fill=TEXT
        )

        row_y += match_row_height

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    footer_y = height - 55

    draw.text(
        (
            70,
            footer_y
        ),
        "Valorant Session Digest",
        font=FONT_FOOTER,
        fill=MUTED
    )

    draw.text(
        (
            WIDTH - 70
            - draw.textbbox(
                (0, 0),
                "Powered by HenrikDev",
                font=FONT_FOOTER
            )[2],
            footer_y
        ),
        "Powered by HenrikDev",
        font=FONT_FOOTER,
        fill=MUTED
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    image.save(
        OUTPUT_FILE,
        "PNG"
    )

    print(
        f"[CARD] Generated {OUTPUT_FILE}"
    )

    return OUTPUT_FILE
