from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# VALORANT-INSPIRED SESSION CARD
# ============================================================

WIDTH = 1400

# Main palette
BG = "#080A0D"
BG_2 = "#0D1117"
PANEL = "#11161D"
PANEL_2 = "#151B23"

WHITE = "#F2F2F2"
LIGHT = "#D8DCE1"
MUTED = "#7F8994"
DARK_MUTED = "#454D57"

RED = "#FF4655"
RED_DARK = "#8F2630"

GREEN = "#7CFF6B"
GREEN_DARK = "#285E2B"

ORANGE = "#FFB347"

BORDER = "#29313A"
GRID = "#1A2129"


OUTPUT_FILE = Path("session_digest.png")


# ============================================================
# Font loading
# ============================================================

def load_font(size: int, bold: bool = False):

    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            + (
                "DejaVuSans-Bold.ttf"
                if bold
                else "DejaVuSans.ttf"
            )
        ),

        (
            "/usr/share/fonts/truetype/liberation2/"
            + (
                "LiberationSans-Bold.ttf"
                if bold
                else "LiberationSans-Regular.ttf"
            )
        ),

        (
            "C:/Windows/Fonts/"
            + (
                "arialbd.ttf"
                if bold
                else "arial.ttf"
            )
        ),
    ]

    for path in candidates:

        if Path(path).exists():

            return ImageFont.truetype(
                path,
                size
            )

    return ImageFont.load_default()


FONT_HUGE = load_font(48, True)
FONT_TITLE = load_font(34, True)
FONT_SUBTITLE = load_font(18, True)

FONT_STAT = load_font(48, True)
FONT_STAT_LABEL = load_font(15, True)

FONT_HEADER = load_font(16, True)

FONT_MATCH = load_font(19, False)
FONT_MATCH_BOLD = load_font(19, True)

FONT_SMALL = load_font(14, False)
FONT_SMALL_BOLD = load_font(14, True)

FONT_FOOTER = load_font(13, False)


# ============================================================
# Drawing helpers
# ============================================================

def rounded_box(
    draw,
    xy,
    radius=12,
    fill=PANEL,
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


def draw_text_right(
    draw,
    x,
    y,
    text,
    font,
    fill
):

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    text_width = bbox[2] - bbox[0]

    draw.text(
        (
            x - text_width,
            y
        ),
        text,
        font=font,
        fill=fill
    )


def draw_text_center(
    draw,
    center_x,
    y,
    text,
    font,
    fill
):

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    text_width = bbox[2] - bbox[0]

    draw.text(
        (
            center_x - text_width / 2,
            y
        ),
        text,
        font=font,
        fill=fill
    )


def rr_text(rr):

    if rr > 0:
        return f"+{rr}"

    return str(rr)


# ============================================================
# Background
# ============================================================

def draw_background(
    image,
    draw,
    width,
    height
):

    # --------------------------------------------------------
    # Base
    # --------------------------------------------------------

    draw.rectangle(
        (0, 0, width, height),
        fill=BG
    )

    # --------------------------------------------------------
    # Subtle grid
    # --------------------------------------------------------

    grid_spacing = 45

    for x in range(
        0,
        width,
        grid_spacing
    ):

        draw.line(
            (
                x,
                0,
                x,
                height
            ),
            fill=GRID,
            width=1
        )

    for y in range(
        0,
        height,
        grid_spacing
    ):

        draw.line(
            (
                0,
                y,
                width,
                y
            ),
            fill=GRID,
            width=1
        )

    # --------------------------------------------------------
    # Large diagonal tactical shapes
    # --------------------------------------------------------

    draw.polygon(
        [
            (width - 450, 0),
            (width, 0),
            (width, 240),
            (width - 170, 110),
        ],
        fill="#111820"
    )

    draw.polygon(
        [
            (0, height - 230),
            (0, height),
            (420, height),
            (230, height - 160),
        ],
        fill="#10161D"
    )

    # --------------------------------------------------------
    # Red angular accent
    # --------------------------------------------------------

    draw.polygon(
        [
            (0, 0),
            (250, 0),
            (150, 12),
            (0, 72),
        ],
        fill=RED
    )

    draw.polygon(
        [
            (width - 190, height),
            (width, height),
            (width, height - 12),
            (width - 95, height - 12),
        ],
        fill=RED
    )

    # --------------------------------------------------------
    # Small diagonal lines
    # --------------------------------------------------------

    for i in range(8):

        x = width - 360 + (i * 45)

        draw.line(
            (
                x,
                80,
                x - 100,
                180
            ),
            fill="#202830",
            width=2
        )


# ============================================================
# Header
# ============================================================

def draw_header(
    draw,
    player_name,
    player_tag
):

    # Red vertical marker

    draw.rectangle(
        (
            65,
            55,
            71,
            135
        ),
        fill=RED
    )

    draw.text(
        (
            90,
            48
        ),
        "VALORANT",
        font=FONT_HUGE,
        fill=WHITE
    )

    draw.text(
        (
            93,
            105
        ),
        "SESSION DIGEST",
        font=FONT_SUBTITLE,
        fill=RED
    )

    # Player

    player = (
        f"{player_name}#{player_tag}"
    )

    draw_text_right(
        draw,
        WIDTH - 70,
        65,
        player,
        FONT_TITLE,
        WHITE
    )

    draw_text_right(
        draw,
        WIDTH - 70,
        108,
        "COMPETITIVE SESSION",
        FONT_SMALL_BOLD,
        MUTED
    )


# ============================================================
# Stat cards
# ============================================================

def draw_stat_cards(
    draw,
    session
):

    top = 170
    left = 65

    gap = 18

    card_width = (
        WIDTH
        - (left * 2)
        - (gap * 2)
    ) // 3

    card_height = 135

    stats = [
        (
            "MATCHES",
            str(session["matches_played"]),
            WHITE
        ),
        (
            "NET RR",
            rr_text(session["net_rr"]),
            (
                GREEN
                if session["net_rr"] >= 0
                else RED
            )
        ),
        (
            "SESSION K/D",
            f"{session['kd_ratio']:.2f}",
            WHITE
        ),
    ]

    for index, (
        label,
        value,
        value_color
    ) in enumerate(stats):

        x1 = (
            left
            + index
            * (
                card_width
                + gap
            )
        )

        x2 = x1 + card_width

        # Card

        rounded_box(
            draw,
            (
                x1,
                top,
                x2,
                top + card_height
            ),
            radius=14,
            fill=PANEL,
            outline=BORDER,
            width=2
        )

        # Top accent

        if label == "NET RR":

            accent = value_color

        else:

            accent = RED

        draw.rectangle(
            (
                x1,
                top,
                x1 + 5,
                top + card_height
            ),
            fill=accent
        )

        # Label

        draw.text(
            (
                x1 + 25,
                top + 20
            ),
            label,
            font=FONT_STAT_LABEL,
            fill=MUTED
        )

        # Value

        draw.text(
            (
                x1 + 25,
                top + 48
            ),
            value,
            font=FONT_STAT,
            fill=value_color
        )


# ============================================================
# Match history header
# ============================================================

def draw_match_header(
    draw,
    y
):

    draw.text(
        (
            65,
            y
        ),
        "MATCH HISTORY",
        font=FONT_TITLE,
        fill=WHITE
    )

    draw.text(
        (
            67,
            y + 42
        ),
        "RECENT COMPETITIVE GAMES",
        font=FONT_SMALL_BOLD,
        fill=MUTED
    )

    # Header row

    header_y = y + 78

    draw.rectangle(
        (
            65,
            header_y,
            WIDTH - 65,
            header_y + 40
        ),
        fill="#0B0F14"
    )

    columns = [
        (85, "#"),
        (155, "RESULT"),
        (330, "K/D"),
        (490, "RR"),
        (650, "MAP"),
        (940, "AGENT"),
    ]

    for x, text in columns:

        draw.text(
            (
                x,
                header_y + 11
            ),
            text,
            font=FONT_HEADER,
            fill=MUTED
        )

    return header_y + 40


# ============================================================
# Match rows
# ============================================================

def draw_match_rows(
    draw,
    matches,
    start_y
):

    row_height = 58

    for index, match in enumerate(
        matches,
        start=1
    ):

        y1 = start_y + (
            (index - 1)
            * row_height
        )

        y2 = y1 + row_height

        # Alternate row backgrounds

        if index % 2 == 0:

            row_fill = PANEL_2

        else:

            row_fill = PANEL

        draw.rectangle(
            (
                65,
                y1,
                WIDTH - 65,
                y2
            ),
            fill=row_fill
        )

        # Bottom separator

        draw.line(
            (
                65,
                y2,
                WIDTH - 65,
                y2
            ),
            fill=BORDER,
            width=1
        )

        # ----------------------------------------------------
        # Match number
        # ----------------------------------------------------

        draw.text(
            (
                85,
                y1 + 18
            ),
            f"{index:02d}",
            font=FONT_MATCH_BOLD,
            fill=MUTED
        )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        result = match["result"]

        if result == "WIN":

            result_color = GREEN
            result_text = "WIN"

        elif result == "LOSS":

            result_color = RED
            result_text = "LOSS"

        else:

            result_color = MUTED
            result_text = "?"

        # Result indicator

        draw.rectangle(
            (
                145,
                y1 + 18,
                151,
                y1 + 40
            ),
            fill=result_color
        )

        draw.text(
            (
                165,
                y1 + 17
            ),
            result_text,
            font=FONT_MATCH_BOLD,
            fill=result_color
        )

        # ----------------------------------------------------
        # K/D
        # ----------------------------------------------------

        kd = (
            f"{match['kills']}"
            f"/"
            f"{match['deaths']}"
        )

        draw.text(
            (
                330,
                y1 + 17
            ),
            kd,
            font=FONT_MATCH,
            fill=WHITE
        )

        # ----------------------------------------------------
        # RR
        # ----------------------------------------------------

        rr = match["rr"]

        if rr > 0:

            rr_color = GREEN

        elif rr < 0:

            rr_color = RED

        else:

            rr_color = MUTED

        draw.text(
            (
                490,
                y1 + 17
            ),
            rr_text(rr),
            font=FONT_MATCH_BOLD,
            fill=rr_color
        )

        # ----------------------------------------------------
        # Map
        # ----------------------------------------------------

        draw.text(
            (
                650,
                y1 + 17
            ),
            match["map"],
            font=FONT_MATCH,
            fill=LIGHT
        )

        # ----------------------------------------------------
        # Agent
        # ----------------------------------------------------

        draw.text(
            (
                940,
                y1 + 17
            ),
            match["agent"],
            font=FONT_MATCH,
            fill=LIGHT
        )


# ============================================================
# Session result
# ============================================================

def draw_session_result(
    draw,
    session,
    y
):

    net_rr = session["net_rr"]

    if net_rr > 0:

        result_color = GREEN
        result_text = "POSITIVE SESSION"

    elif net_rr < 0:

        result_color = RED
        result_text = "NEGATIVE SESSION"

    else:

        result_color = ORANGE
        result_text = "EVEN SESSION"

    # --------------------------------------------------------
    # Section title
    # --------------------------------------------------------

    draw.text(
        (
            65,
            y
        ),
        result_text,
        font=FONT_SUBTITLE,
        fill=result_color
    )

    # --------------------------------------------------------
    # RR progress line
    # --------------------------------------------------------

    bar_x1 = 65
    bar_x2 = WIDTH - 65
    bar_y = y + 42

    draw.rounded_rectangle(
        (
            bar_x1,
            bar_y,
            bar_x2,
            bar_y + 10
        ),
        radius=5,
        fill="#1C242C"
    )

    # Normalize purely for visual purposes.
    #
    # This is NOT an RR percentage.
    # It is just a visual indicator.

    magnitude = min(
        abs(net_rr) / 100,
        1
    )

    bar_width = int(
        (bar_x2 - bar_x1)
        * magnitude
    )

    if bar_width > 0:

        draw.rounded_rectangle(
            (
                bar_x1,
                bar_y,
                bar_x1 + bar_width,
                bar_y + 10
            ),
            radius=5,
            fill=result_color
        )

    # --------------------------------------------------------
    # RR number
    # --------------------------------------------------------

    draw_text_right(
        draw,
        WIDTH - 65,
        y - 5,
        rr_text(net_rr),
        FONT_TITLE,
        result_color
    )


# ============================================================
# Footer
# ============================================================

def draw_footer(
    draw,
    height
):

    y = height - 42

    draw.text(
        (
            65,
            y
        ),
        "VALORANT SESSION DIGEST",
        font=FONT_FOOTER,
        fill=DARK_MUTED
    )

    draw_text_right(
        draw,
        WIDTH - 65,
        y,
        "Powered by HenrikDev",
        FONT_FOOTER,
        DARK_MUTED
    )


# ============================================================
# Main card generator
# ============================================================

def generate_session_card(
    session,
    player_name,
    player_tag
):

    matches = session["matches"]

    # --------------------------------------------------------
    # Dynamic height
    # --------------------------------------------------------

    header_height = 155
    stat_height = 175

    match_section_height = (
        125
        + (
            len(matches)
            * 58
        )
    )

    result_height = 100

    footer_height = 70

    height = (
        header_height
        + stat_height
        + match_section_height
        + result_height
        + footer_height
    )

    # --------------------------------------------------------
    # Create image
    # --------------------------------------------------------

    image = Image.new(
        "RGB",
        (
            WIDTH,
            height
        ),
        BG
    )

    draw = ImageDraw.Draw(
        image
    )

    # --------------------------------------------------------
    # Background
    # --------------------------------------------------------

    draw_background(
        image,
        draw,
        WIDTH,
        height
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    draw_header(
        draw,
        player_name,
        player_tag
    )

    # --------------------------------------------------------
    # Stats
    # --------------------------------------------------------

    draw_stat_cards(
        draw,
        session
    )

    # --------------------------------------------------------
    # Match section
    # --------------------------------------------------------

    match_title_y = (
        header_height
        + stat_height
    )

    match_header_bottom = draw_match_header(
        draw,
        match_title_y
    )

    draw_match_rows(
        draw,
        matches,
        match_header_bottom
    )

    # --------------------------------------------------------
    # Session result
    # --------------------------------------------------------

    result_y = (
        match_header_bottom
        + (
            len(matches)
            * 58
        )
        + 30
    )

    draw_session_result(
        draw,
        session,
        result_y
    )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    draw_footer(
        draw,
        height
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
