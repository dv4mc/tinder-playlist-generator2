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
        angle_deg = start_angle - (arc_pos / total_arc_len) * span_deg
        angle_rad = math.radians(angle_deg)

        x = center_x + radius * math.cos(angle_rad)
        y = center_y + radius * math.sin(angle_rad)

        bbox = measure_draw.textbbox((0, 0), char, font=font, stroke_width=stroke_thickness)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = stroke_thickness + 15
        
        char_img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((pad - bbox[0], pad - bbox[1]), char, font=font, fill=(0, 255, 66), 
                        stroke_width=stroke_thickness, stroke_fill=(255, 255, 255))

        rotated = char_img.rotate(90 - angle_deg, resample=Image.Resampling.BICUBIC, expand=True)
        text_layer.paste(rotated, (int(x - rotated.width / 2), int(y - rotated.height / 2)), rotated)
        
        arc_pos += char_w / 2
        if i < len(text) - 1:
            arc_pos += word_spacing if (text[i] == ' ' or text[i+1] == ' ') else letter_spacing

    return Image.alpha_composite(base_image, text_layer)

# --- 2. SPOTIFY SETUP ---
st.set_page_config(page_title="Tinder Playlist Generator", page_icon="🎵")
st.title("🎵 Tinder Playlist Generator")

scope = "playlist-modify-private playlist-modify-public ugc-image-upload"
cache_path = os.path.join(os.getcwd(), ".spotify_cache")

auth_manager = SpotifyOAuth(
    client_id=st.secrets["SPOTIPY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],
    scope=scope,
    show_dialog=False, 
    cache_path=cache_path
)

if "code" in st.query_params:
    auth_manager.get_access_token(st.query_params["code"])
    st.query_params.clear()
    st.rerun()

sp = spotipy.Spotify(auth_manager=auth_manager)
token_info = auth_manager.get_cached_token()

if not token_info:
    auth_url = auth_manager.get_authorize_url()
    st.info("Pro vytvoření playlistu se musíš přihlásit ke Spotify.")
    st.link_button("Přihlásit se ke Spotify", auth_url)
    st.stop()

# --- 3. KONFIGURACE TRACKŮ ---
track_ids = [
    "4Vqv5vr4G4OEWINosjwX2t", "2cEFHXXBfVEMUcTAaz2jVO", "75IN3CtuZwTHTnZvYM4qnJ",
    "6ghDayhHeBXAP4OOnnrFW9", "3TzLgFxVxvFXPdIdcKY81D", "0QQviRjnsuP04U9r75fANz",
    "0D1P89Vt4rdF1m2rVE7kRK", "66BfuepFzEO1t0ZmZA4lAL", "16B00iTnq08BrEPVD9MMkh",
    "6C9X0E0E2i9NQLutXRlJcF", "11qgXw005lZy5rmrpeOL3y", "3e0ZGE7Gp034iLknjQk4QW",
    "0cGjUnkLjOBqFCF8YYuoUA", "31BPE9mx2gbSXYkmM0FIAC", "6UPTAEFulqmF8SulceHgzg"
]
track_uris = [f"spotify:track:{tid}" for tid in track_ids]

user_text = st.text_input("Zadej text pro obrázek (např. Tinder):", "Playlist Pro")

if st.button("Vytvořit vše"):
    if user_text:
        with st.spinner("Generuji obrázek a playlist..."):
            # A. Generování obrázku
            final_img = generate_tinder_image(user_text)
            
            # B. Spotify operace
            playlist = sp.current_user_playlist_create(user_text, public=False, description="")
            sp.playlist_add_items(playlist['id'], track_uris)
            
            # C. Nahrání obalu
            if final_img:
                cover_img = final_img.convert("RGB")
                cover_img.thumbnail((640, 640))
                buffered = io.BytesIO()
                cover_img.save(buffered, format="JPEG", quality=85)
                img_str = base64.b64encode(buffered.getvalue()).decode()
                sp.playlist_upload_cover_image(playlist['id'], img_str)
                st.image(final_img, caption="Obal playlistu")
            
            st.success("Hotovo!")
            st.markdown(f"### [👉 Otevřít playlist na Spotify]({playlist['external_urls']['spotify']})")
    else:
        st.warning("Zadej prosím text.")
