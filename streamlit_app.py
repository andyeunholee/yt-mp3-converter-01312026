import streamlit as st
import os
import re
import uuid
import shutil
import subprocess
import platform
import yt_dlp
from moviepy.editor import AudioFileClip
import imageio_ffmpeg
import time

# --- Configuration & Setup ---
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def setup_ffmpeg():
    """Extracts/Copies ffmpeg binary to a local path for consistent use by yt-dlp."""
    try:
        src = imageio_ffmpeg.get_ffmpeg_exe()
        exe_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
        local_ffmpeg = os.path.join(os.getcwd(), exe_name)
        
        if not os.path.exists(local_ffmpeg):
            try:
                shutil.copy2(src, local_ffmpeg)
                if platform.system() != "Windows":
                    os.chmod(local_ffmpeg, 0o755)
            except Exception:
                return src
        return local_ffmpeg
    except Exception:
        return imageio_ffmpeg.get_ffmpeg_exe()

FFMPEG_PATH = setup_ffmpeg()

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def process_video(video_url, output_format='mp3'):
    """Downloads video and converts to specified format."""
    try:
        temp_id = str(uuid.uuid4())
        
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'ffmpeg_location': FFMPEG_PATH,
            'source_address': '0.0.0.0', # Keep IPv4 force
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            }
        }

        if output_format == 'mp4':
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s.%(ext)s'),
            })
        else: # mp3
            ydl_opts.update({
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.%(ext)s'),
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            
            if output_format == 'mp4':
                sanitized_title = sanitize_filename(info_dict['title'])
                result_path = ydl.prepare_filename(info_dict)
                base, _ = os.path.splitext(result_path)
                final_mp4_path = base + '.mp4'
                
                # Re-encode to AAC for compatibility
                temp_fixed_path = base + '_fixed.mp4'
                subprocess.run([
                    FFMPEG_PATH, '-y', '-i', final_mp4_path,
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    temp_fixed_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                if os.path.exists(temp_fixed_path):
                    os.replace(temp_fixed_path, final_mp4_path)

                return {"success": True, "file_path": final_mp4_path, "filename": os.path.basename(final_mp4_path), "title": info_dict['title']}
            
            # MP3 Flow
            temp_file_path = ydl.prepare_filename(info_dict)
        
        if output_format == 'mp3':
            if not temp_file_path or not os.path.exists(temp_file_path):
                raise Exception("Download failed")

            title = sanitize_filename(info_dict.get('title', 'audio'))
            mp3_filename = f"{title}.mp3"
            mp3_path = os.path.join(DOWNLOAD_FOLDER, mp3_filename)
            
            if os.path.exists(mp3_path):
                mp3_filename = f"{title}_{temp_id[:8]}.mp3"
                mp3_path = os.path.join(DOWNLOAD_FOLDER, mp3_filename)

            audioclip = AudioFileClip(temp_file_path)
            audioclip.write_audiofile(mp3_path, logger=None)
            audioclip.close()
            
            try:
                os.remove(temp_file_path)
            except:
                pass
                
            return {"success": True, "file_path": mp3_path, "filename": mp3_filename, "title": title}

    except Exception as e:
        return {"success": False, "error": str(e)}

# --- Streamlit UI ---
st.set_page_config(page_title="YT to MP3", page_icon="🎵", layout="centered")

# Custom CSS for styling
st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #3b0764, #0f172a);
    }
    .title {
        font-family: 'Outfit', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #fff, #cbd5e1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #94a3b8;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">YT to MP3</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Convert audio instantly. Private & High Quality.</div>', unsafe_allow_html=True)

url = st.text_input("YouTube URL", placeholder="Paste YouTube link here...")

col1, col2 = st.columns(2)

if url:
    with col1:
        if st.button("Convert to MP4", use_container_width=True):
            with st.spinner("Processing video..."):
                result = process_video(url, 'mp4')
                if result['success']:
                    st.success(f"Converted: {result['title']}")
                    with open(result['file_path'], "rb") as file:
                        st.download_button(
                            label="Download MP4",
                            data=file,
                            file_name=result['filename'],
                            mime="video/mp4",
                            use_container_width=True
                        )
                else:
                    st.error(f"Error: {result['error']}")

    with col2:
        if st.button("Convert to MP3", type="primary", use_container_width=True):
            with st.spinner("Processing audio..."):
                result = process_video(url, 'mp3')
                if result['success']:
                    st.success(f"Converted: {result['title']}")
                    with open(result['file_path'], "rb") as file:
                        st.download_button(
                            label="Download MP3",
                            data=file,
                            file_name=result['filename'],
                            mime="audio/mpeg",
                            use_container_width=True
                        )
                else:
                    st.error(f"Error: {result['error']}")
