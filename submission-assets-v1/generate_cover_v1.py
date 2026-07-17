#!/usr/bin/env python3
"""Create the public 3:2 cover without network access or private inputs."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "handmade-creator-radar-cover-v1.png"
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size=size)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, radius: int = 34) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def main() -> None:
    image = Image.new("RGB", (1800, 1200), "#081525")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1800, 18), fill="#62D8C7")
    draw.ellipse((1320, 80, 1750, 510), fill="#132B4B")
    draw.ellipse((1430, 180, 1660, 410), fill="#1A4165")
    draw.text((120, 132), "HANDMADE CREATOR RADAR", font=font(94), fill="#F6FAFF")
    draw.text((126, 252), "Evidence before platform hype", font=font(44), fill="#AFC6DD")
    rounded(draw, (120, 390, 760, 650), "#102640")
    rounded(draw, (1040, 390, 1680, 650), "#102640")
    draw.text((174, 438), "BILIBILI", font=font(38), fill="#62D8C7")
    draw.text((174, 502), "Public-source probe", font=font(34), fill="#F6FAFF")
    draw.text((1094, 438), "YOUTUBE", font=font(38), fill="#62D8C7")
    draw.text((1094, 502), "Public-source probe", font=font(34), fill="#F6FAFF")
    draw.line((790, 520, 1010, 520), fill="#62D8C7", width=8)
    draw.polygon([(1010, 520), (960, 488), (960, 552)], fill="#62D8C7")
    rounded(draw, (410, 760, 1390, 1020), "#1C395B")
    draw.text((525, 804), "INSUFFICIENT EVIDENCE", font=font(54), fill="#F6FAFF")
    draw.text((570, 888), "SAFE TO PAUSE. READY TO LEARN.", font=font(34), fill="#AFC6DD")
    draw.text((120, 1092), "Safety-first  •  Offline replay  •  58 tests", font=font(31), fill="#62D8C7")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)


if __name__ == "__main__":
    main()
