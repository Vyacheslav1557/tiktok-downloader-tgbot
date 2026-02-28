import textwrap
from typing import Optional, cast

from PIL import Image, ImageDraw, ImageFont, ImageOps


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold:
        candidates = [
            "Chirp-Bold.ttf",
            "seguisb.ttf",
            "segoeuib.ttf",
            "Segoe UI Bold.ttf",
            "HelveticaNeue-Bold.ttf",
            "arialbd.ttf",
            "DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "Chirp-Regular.ttf",
            "segoeui.ttf",
            "Segoe UI.ttf",
            "HelveticaNeue.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
        ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return cast(tuple[int, int], (int(right - left), int(bottom - top)))


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    width_chars: int,
    line_height: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_lines: int,
) -> tuple[int, int]:
    lines = textwrap.wrap(text.strip() or "(empty post)", width=width_chars)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .") + "..."

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height

    return y, len(lines)


def _draw_inline_image(
    image: Image.Image,
    canvas: Image.Image,
    left: int,
    top: int,
    right: int,
    bottom: int,
    radius: int,
) -> None:
    target_w = right - left
    target_h = bottom - top
    fitted = ImageOps.fit(image.convert("RGB"), (target_w, target_h), method=Image.Resampling.LANCZOS)

    mask = Image.new("L", (target_w, target_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, target_w, target_h), radius=radius, fill=255)
    canvas.paste(fitted, (left, top), mask)


def _draw_avatar(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    size: int,
    accent: tuple[int, int, int],
    fallback_letter: str,
    avatar_path: Optional[str],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    right = left + size
    bottom = top + size

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size, size), fill=255)

    pasted = False
    if avatar_path:
        try:
            with Image.open(avatar_path) as avatar_image:
                fitted = ImageOps.fit(avatar_image.convert("RGB"), (size, size), method=Image.Resampling.LANCZOS)
                canvas.paste(fitted, (left, top), mask)
                pasted = True
        except Exception:
            pasted = False

    if not pasted:
        draw.ellipse((left, top, right, bottom), fill=(9, 16, 24))
        letter_w, letter_h = _text_size(draw, fallback_letter, font)
        letter_x = left + (size - letter_w) // 2
        letter_y = top + (size - letter_h) // 2 - 2
        draw.text((letter_x, letter_y), fallback_letter, font=font, fill=(238, 244, 250))

    draw.ellipse((left, top, right, bottom), outline=accent, width=3)


def render_x_post_card(
    output_path: str,
    author_name: str,
    handle: str,
    post_text: str,
    quote_text: Optional[str] = None,
    reply_to_text: Optional[str] = None,
    inline_image_path: Optional[str] = None,
    avatar_image_path: Optional[str] = None,
    published_at_text: Optional[str] = None,
    views_text: Optional[str] = None,
) -> None:
    width = 1200
    height = 1000

    canvas = Image.new("RGB", (width, height), (10, 14, 20))
    draw = ImageDraw.Draw(canvas)

    for i in range(height):
        ratio = i / height
        r = int(8 + (18 - 8) * ratio)
        g = int(12 + (22 - 12) * ratio)
        b = int(18 + (34 - 18) * ratio)
        draw.line((0, i, width, i), fill=(r, g, b))

    panel_left = 64
    panel_top = 56
    panel_right = width - 64
    panel_bottom = height - 56

    panel_bg = (16, 22, 30)
    panel_outline = (38, 49, 63)
    text_primary = (233, 239, 246)
    text_secondary = (133, 148, 166)
    accent = (29, 155, 240)
    quote_bg = (22, 29, 39)

    draw.rounded_rectangle(
        (panel_left, panel_top, panel_right, panel_bottom),
        radius=34,
        fill=panel_bg,
        outline=panel_outline,
        width=2,
    )

    avatar_size = 84
    avatar_left = panel_left + 38
    avatar_top = panel_top + 34
    avatar_right = avatar_left + avatar_size
    avatar_bottom = avatar_top + avatar_size
    avatar_letter = (author_name.strip()[:1] or "X").upper()
    avatar_font = _load_font(36, bold=True)
    _draw_avatar(
        canvas=canvas,
        draw=draw,
        left=avatar_left,
        top=avatar_top,
        size=avatar_size,
        accent=accent,
        fallback_letter=avatar_letter,
        avatar_path=avatar_image_path,
        font=avatar_font,
    )

    name_font = _load_font(38, bold=True)
    handle_font = _load_font(28)
    text_font = _load_font(36)
    reply_font = _load_font(26)
    quote_label_font = _load_font(24, bold=True)
    quote_font = _load_font(28)

    text_left = avatar_right + 28
    draw.text((text_left, avatar_top + 2), author_name, font=name_font, fill=text_primary)
    draw.text((text_left, avatar_top + 48), handle, font=handle_font, fill=text_secondary)

    text_start_y = avatar_bottom + 44
    if reply_to_text:
        reply_top = avatar_bottom + 24
        bar_left = panel_left + 44
        bar_right = bar_left + 6
        reply_label = f"Replying to {reply_to_text}"
        reply_mid_y = reply_top + 17
        draw.rounded_rectangle((bar_left, reply_top, bar_right, reply_top + 34), radius=3, fill=accent)
        draw.text((bar_right + 12, reply_mid_y), reply_label, font=reply_font, fill=accent, anchor="lm")
        text_start_y = reply_top + 48

    cursor_y, _ = _draw_wrapped_text(
        draw=draw,
        text=post_text,
        x=panel_left + 44,
        y=text_start_y,
        width_chars=44,
        line_height=54,
        font=text_font,
        fill=text_primary,
        max_lines=8,
    )

    if quote_text:
        quote_top = cursor_y + 18
        quote_bottom = min(quote_top + 154, panel_bottom - 44)
        if quote_bottom - quote_top >= 90:
            indicator_left = panel_left + 44
            indicator_right = indicator_left + 6
            draw.rounded_rectangle(
                (indicator_left, quote_top, indicator_right, quote_bottom),
                radius=3,
                fill=accent,
            )

            quote_left = panel_left + 58
            draw.rounded_rectangle(
                (quote_left, quote_top, panel_right - 44, quote_bottom),
                radius=20,
                fill=quote_bg,
                outline=panel_outline,
                width=2,
            )
            draw.text((quote_left + 20, quote_top + 16), "Reply to quoted post", font=quote_label_font, fill=accent)
            _draw_wrapped_text(
                draw=draw,
                text=quote_text,
                x=quote_left + 20,
                y=quote_top + 50,
                width_chars=54,
                line_height=34,
                font=quote_font,
                fill=text_primary,
                max_lines=2,
            )
            cursor_y = quote_bottom

    should_draw_inline_image = inline_image_path is not None
    inline_top = cursor_y + 22
    inline_bottom = panel_bottom - 78
    enough_space_for_image = inline_bottom - inline_top >= 220

    if should_draw_inline_image and enough_space_for_image:
        try:
            with Image.open(inline_image_path) as inline_image:
                _draw_inline_image(
                    image=inline_image,
                    canvas=canvas,
                    left=panel_left + 44,
                    top=inline_top,
                    right=panel_right - 44,
                    bottom=inline_bottom,
                    radius=24,
                )
                draw.rounded_rectangle(
                    (panel_left + 44, inline_top, panel_right - 44, inline_bottom),
                    radius=24,
                    outline=panel_outline,
                    width=2,
                )
        except Exception:
            pass

    footer_parts = []
    if published_at_text:
        footer_parts.append(published_at_text)
    if views_text:
        footer_parts.append(views_text)
    footer = " · ".join(footer_parts)
    if footer:
        footer_font = _load_font(28)
        draw.text((panel_left + 44, panel_bottom - 48), footer, font=footer_font, fill=text_secondary)

    canvas.save(output_path, format="PNG")
