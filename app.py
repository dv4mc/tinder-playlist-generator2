import streamlit as st
import math
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# --- 1. GRAFICKÁ LOGIKA ---
def generate_tinder_image(text):
    base_path = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(base_path, "tinder.png")
    font_path = os.path.join(base_path, "PPPangramSansRounded-Bold.otf")

    if not os.path.exists(image_path) or not os.path.exists(font_path):
        st.error("Chybí soubor tinder.png nebo font!")
        return None

    base_image = Image.open(image_path).convert("RGBA")
    width, height = base_image.size
    
    font_size = int(height * 0.13)
    radius = int(height * 0.36)
    bottom_deg = 90
    max_span_deg = 220
    stroke_thickness = int(font_size * 0.12)
    letter_spacing = -int(font_size * 0.18)
    word_spacing = -int(font_size * 0.2)

    font = ImageFont.truetype(font_path, font_size)
    center_x, center_y = width // 2, height // 2
    
    text_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    measure_draw = ImageDraw.Draw(text_layer)

    char_widths = []
    for char in text:
        bbox = measure_draw.textbbox((0, 0), char, font=font, stroke_width=stroke_thickness)
        char_widths.append(bbox[2] - bbox[0])

    total_arc_len = sum(char_widths)
    for i in range(len(text) - 1):
        total_arc_len += word_spacing if (text[i] == ' ' or text[i+1] == ' ') else letter_spacing

    span_deg = min(math.degrees(total_arc_len / radius), max_span_deg)
    start_angle = bottom_deg + span_deg / 2

    arc_pos = 0.0
    for i, char in enumerate(text):
        char_w = char_widths[i]
        arc_pos += char_w / 2
        angle_deg = start_angle -
