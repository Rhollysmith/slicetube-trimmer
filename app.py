import os
import glob
import uuid
import subprocess
import streamlit as st

st.set_page_config(page_title="SliceTube Trimmer", page_icon="✂️", layout="centered")
st.title("✂️ SliceTube - YouTube Video Trimmer")
st.caption("Paste a YouTube link, preview the video, choose your start and end times, and download your clip.")

TEMP_DIR = "/tmp/temp_clips"
os.makedirs(TEMP_DIR, exist_ok=True)

url = st.text_input("Paste YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

with st.expander("⚙️ Optional: Upload YouTube cookies.txt (if YouTube blocks cloud IP)"):
    cookie_file = st.file_uploader("Upload cookies.txt (Netscape format)", type=["txt"])

if url:
    st.video(url)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_time = st.text_input("Start Time", value="00:00", help="MM:SS or HH:MM:SS")
    with col2:
        end_time = st.text_input("End Time", value="00:15", help="MM:SS or HH:MM:SS")
    with col3:
        format_type = st.selectbox("Format", ["mp4", "mp3"])
    with col4:
        quality = st.selectbox("Max Quality", ["1080", "720", "480"], disabled=(format_type == "mp3"))

    if st.button("✂️ Trim & Prepare Download", type="primary", use_container_width=True):
        clip_id = str(uuid.uuid4())
        ext = "mp3" if format_type == "mp3" else "mp4"
        output_template = os.path.join(TEMP_DIR, f"{clip_id}.%(ext)s")
        final_file = os.path.join(TEMP_DIR, f"{clip_id}.{ext}")

        # Base arguments with JS runtime and working YouTube player clients
        base_cmd = [
            "yt-dlp",
            "--no-playlist",
            "--js-runtimes", "node",
            "--extractor-args", "youtube:player_client=android,web,tv,default,-android_vr",
        ]

        cookie_path = None
        if cookie_file is not None:
            cookie_path = os.path.join(TEMP_DIR, f"{clip_id}_cookies.txt")
            with open(cookie_path, "wb") as cf:
                cf.write(cookie_file.read())
            base_cmd += ["--cookies", cookie_path]

        # Force DASH formats so FFmpeg does not fail with code 8 on progressive streams
        if format_type == "mp3":
            fmt_args = ["-f", "bestaudio[ext=m4a]/bestaudio", "-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            fmt_str = (
                f"bestvideo[height<={quality}][vcodec^=avc1]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={quality}]+bestaudio/bestvideo+bestaudio/best"
            )
            fmt_args = ["-f", fmt_str, "--merge-output-format", "mp4"]

        # Attempt 1: Fast direct partial-stream slice
        section_arg = f"*{start_time.strip()}-{end_time.strip()}"
        cmd_fast = base_cmd + ["--download-sections", section_arg, "-o", output_template] + fmt_args + [url.strip()]

        with st.spinner("Slicing video stream... Please wait."):
            result = subprocess.run(cmd_fast, capture_output=True, text=True)

            # Attempt 2 (Automatic Fallback): If FFmpeg gets HTTP 403 (code 8) on direct range request,
            # download via yt-dlp's native chunked downloader and trim locally with FFmpeg
            if result.returncode != 0 or not os.path.exists(final_file):
                raw_template = os.path.join(TEMP_DIR, f"{clip_id}_raw.%(ext)s")
                cmd_fallback = base_cmd + ["-o", raw_template] + fmt_args + [url.strip()]
                result = subprocess.run(cmd_fallback, capture_output=True, text=True)

                raw_matches = glob.glob(os.path.join(TEMP_DIR, f"{clip_id}_raw.*"))
                if result.returncode == 0 and raw_matches:
                    raw_file = raw_matches[0]
                    ffmpeg_cmd = [
                        "ffmpeg", "-y",
                        "-ss", start_time.strip(),
                        "-to", end_time.strip(),
                        "-i", raw_file,
                        "-c", "copy",
                        final_file
                    ]
                    subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                    if os.path.exists(raw_file):
                        os.remove(raw_file)

        if cookie_path and os.path.exists(cookie_path):
            os.remove(cookie_path)

        if os.path.exists(final_file):
            with open(final_file, "rb") as f:
                file_bytes = f.read()
            os.remove(final_file)

            safe_name = f"slicetube_{start_time.replace(':', '-')}_to_{end_time.replace(':', '-')}.{ext}"
            st.success("✅ Clip ready! Click below to save it to your device:")
            st.download_button(
                label=f"⬇ Download {safe_name}",
                data=file_bytes,
                file_name=safe_name,
                mime="audio/mpeg" if ext == "mp3" else "video/mp4",
                use_container_width=True,
            )
        else:
            st.error("Failed to trim video.")
            with st.expander("View full error details"):
                st.code(result.stderr or result.stdout or "Unknown error")
                
