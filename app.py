import streamlit as st
import math
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# --- 1. GRAFICKÁ LOGIKA (Z vašeho script.py) ---
def generate_tinder_image(text):
    base_path = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(base_path, "tinder.png")
    font_path = os.path.join(base_path, "PPPangramSansRounded-Bold.otf")

    if not os.path.exists(image_path) or not os.path.exists(font_path):
        st.error("Chybí soubor tinder.png nebo font! Ujistěte se, že jsou ve stejné složce jako tento skript.")
        return None

    base_image = Image.open(image_path).convert("RGBA")
    width, height = base_image.size
    
    # Nastavení parametrů podle vašich požadavků
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

    # Výpočet šířek písmen
    char_widths = []
    for char in text:
        bbox = measure_draw.textbbox((0, 0), char, font=font, stroke_width=stroke_thickness)
        char_widths.append(bbox[2] - bbox[0])

    # Výpočet délky oblouku
    total_arc_len = sum(char_widths)
    for i in range(len(text) - 1):
        total_arc_len += word_spacing if (text[i] == ' ' or text[i+1] == ' ') else letter_spacing

    span_deg = min(math.degrees(total_arc_len / radius), max_span_deg)
    start_angle = bottom_deg + span_deg / 2

    # Vykreslení písmen
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
        
        # Průhledná bílá pro eliminaci černých okrajů
        char_img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((pad - bbox[0], pad - bbox[1]), char, font=font, fill=(0, 255, 66), 
                       stroke_width=stroke_thickness, stroke_fill=(255, 255, 255))

        # Rotace (vršek do středu)
        rotated = char_img.rotate(90 - angle_deg, resample=Image.Resampling.BICUBIC, expand=True)
        text_layer.paste(rotated, (int(x - rotated.width / 2), int(y - rotated.height / 2)), rotated)
        
        arc_pos += char_w / 2
        if i < len(text) - 1:
            arc_pos += word_spacing if (text[i] == ' ' or text[i+1] == ' ') else letter_spacing

    return Image.alpha_composite(base_image, text_layer)

# --- 2. SPOTIFY AUTH (Upraveno pro Streamlit) ---
st.set_page_config(page_title="Tinder Playlist Generator", page_icon="🎵")
st.title("🎵 Tinder Playlist Generator")

scope = "playlist-modify-private playlist-modify-public ugc-image-upload"

auth_manager = SpotifyOAuth(
    client_id=st.secrets["SPOTIPY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],
    scope=scope,
    show_dialog=True,
    cache_path=".cache"
)

# Kontrola, zda se vracíme ze Spotify s kódem
if "code" in st.query_params:
    auth_manager.get_access_token(st.query_params["code"])
    # Vyčistíme URL od kódu (volitelné, ale čistší)
    st.query_params.clear()

# Zkusíme získat token z cache
token_info = auth_manager.get_cached_token()

if not token_info:
    # Pokud nejsme přihlášeni, zobrazíme odkaz pro přihlášení
    auth_url = auth_manager.get_authorize_url()
    st.info("Pro vytvoření playlistu se musíš nejdříve přihlásit ke Spotify.")
    st.link_button("Přihlásit se ke Spotify", auth_url)
    st.stop()

# Pokud jsme přihlášeni, pokračujeme k aplikaci
sp = spotipy.Spotify(auth_manager=auth_manager)

try:
    user_info = sp.current_user()
    st.write(f"Přihlášen jako: **{user_info['display_name']}**")
except:
    st.error("Chyba při načítání uživatele. Zkus se přihlásit znovu.")
    if os.path.exists(".cache"):
        os.remove(".cache")
    st.stop()

user_text = st.text_input("Zadej text pro playlist a obrázek:", "Playlist Pro")

if st.button("Vytvořit vše (Obrázek + Playlist)"):
    if user_text:
        # A. Generování obrázku
        with st.spinner("Vytvářím grafiku..."):
            final_img = generate_tinder_image(user_text)
            if final_img:
                st.image(final_img, caption="Náhled obalu")
                
                # Příprava pro stažení
                img_buffer = io.BytesIO()
                final_img.save(img_buffer, format="PNG")
                st.download_button("Stáhnout obrázek", data=img_buffer.getvalue(), file_name=f"Tinder-{user_text}.png")

        # B. Spotify integrace
        with st.spinner("Komunikuji se Spotify..."):
            try:
                # 1. Vytvoření playlistu
                # Použijeme jednodušší metodu, která nevyžaduje user_id
                playlist = sp.current_user_playlist_create(user_text, public=False)
                st.success(f"1. Playlist '{user_text}' vytvořen!")

                # 2. Nahrání obalu (Cover)
                with st.spinner("Nahrávám obal..."):
                    # Spotify vyžaduje JPEG, max 256KB. Zmenšíme obrázek pro jistotu.
                    cover_img = final_img.convert("RGB")
                    cover_img.thumbnail((640, 640)) # Spotify doporučuje 640x640
                    
                    quality = 85
                    while True:
                        buffered = io.BytesIO()
                        cover_img.save(buffered, format="JPEG", quality=quality)
                        img_data = buffered.getvalue()
                        if len(img_data) < 250000 or quality < 10:
                            break
                        quality -= 5
                    
                    img_str = base64.b64encode(img_data).decode()
                    
                    try:
                        sp.playlist_upload_cover_image(playlist['id'], img_str)
                        st.success("2. Obal playlistu nahrán!")
                    except Exception as cover_err:
                        st.warning(f"Obal se nepodařilo nahrát (ale playlist je vytvořen): {cover_err}")

                # 3. Přidání písniček (Vyhledávání podle seznamu)
                with st.spinner("Vyhledávám a přidávám písničky..."):
                    songs_to_find = [
                        "Hi Hi Hi Wings",
                        "My Name Is Eminem",
                        "David Lorde",
                        "But Chon",
                        "Something's Wrong The Jesus and Mary Chain",
                        "Oh I Know Bootleg Rascal",
                        "I Didn't Ask You MBP",
                        "Out Single Ruin",
                        "The Question Is Grand River",
                        "When Vincent Gallo",
                        "Can I Drake",
                        "Take You Out Nettspend",
                        "For Drink Sub Fever",
                        "?!?!?! Kay Okay Thanks."
                    ]
                    
                    track_uris = []
                    for song_query in songs_to_find:
                        results = sp.search(q=song_query, limit=1, type='track')
                        tracks = results['tracks']['items']
                        if tracks:
                            track_uris.append(tracks[0]['uri'])
                        else:
                            st.warning(f"Nepodařilo se najít písničku: {song_query}")

                    if track_uris:
                        sp.playlist_add_items(playlist['id'], track_uris)
                        st.success(f"3. Přidáno {len(track_uris)} písniček!")

                st.balloons()
                st.markdown(f"### [👉 Otevřít tvůj nový playlist]({playlist['external_urls']['spotify']})")

            except Exception as e:
                st.error(f"Chyba: {e}")
    else:
        st.warning("Zadej prosím nějaký text.")
