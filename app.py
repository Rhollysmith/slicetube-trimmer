import os
import uuid
import subprocess
import streamlit as st

st.set_page_config(page_title="SliceTube Trimmer", page_icon="✂️", layout="centered")
st.title("✂️ SliceTube - YouTube Video Trimmer")
st.caption("Paste a YouTube link, preview the video, choose your start and end times, and download your clip.")

TEMP_DIR = "/tmp/temp_clips"
os.makedirs(TEMP_DIR, exist_ok=True)

url = st.text_input("Paste YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

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

        section_arg = f"*{start_time.strip()}-{end_time.strip()}"
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--download-sections", section_arg,
            "--force-keyframes-at-cuts",
            "-o", output_template,
        ]

        if format_type == "mp3":
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            fmt_str = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best"
            cmd += ["-f", fmt_str, "--merge-output-format", "mp4"]

        cmd.append(url.strip())

        with st.spinner("Slicing video stream... Please wait a few seconds."):
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(final_file):
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
            st.error(f"Failed to trim video: {result.stderr.splitlines()[-1] if result.stderr else 'Unknown error'}")
      
