import streamlit as st
import os
from video_generator import (
    initialize_clients,
    generate_story_with_prompts,
    generate_image_with_dalle,
    generate_narration,
    images_to_video_ffmpeg,
    cleanup_images,
    IMAGE_DIR
)

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Story Video Generator",
    page_icon="🎬",
    layout="wide"
)

# --- App Title and Description ---
st.title("🎬 Ask For It ... ") #//
st.markdown("""
Welcome! This tool helps you create a short video from a single text prompt. 
1.  **Enter a prompt** for a story or idea.
2.  The AI will generate a title and image prompts.
3.  It will then generate images and a voiceover.
4.  Finally, it will combine everything into a video with background music.
""")

# --- API Key Management ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
except KeyError:
    st.error("API keys not found in st.secrets. Please add them to your .streamlit/secrets.toml file.")
    st.stop()

# --- Initialize Session State ---
if 'generation_complete' not in st.session_state:
    st.session_state.generation_complete = False
    st.session_state.story_data = None
    st.session_state.image_paths = []
    st.session_state.video_path = None

# --- User Input ---
with st.form("video_form"):
    user_prompt = st.text_area("Enter your video prompt here:", "A lone astronaut discovering a glowing forest on a distant moon.")
    submitted = st.form_submit_button("✨ Generate")

# --- Main Logic ---
if submitted:
    # Reset state for a new run
    st.session_state.generation_complete = False
    st.session_state.story_data = None
    st.session_state.image_paths = []
    st.session_state.video_path = None
    cleanup_images() # Clean up old images before starting

    try:
        # Initialize clients
        openai_client, elevenlabs_client = initialize_clients(OPENAI_API_KEY, ELEVENLABS_API_KEY)

        # --- Generation Steps ---
        with st.spinner("Step 1/4: Generating story and prompts... ✍️"):
            st.session_state.story_data = generate_story_with_prompts(user_prompt, openai_client)
        st.success("Story and prompts generated!")

        with st.spinner("Step 2/4: Generating narration... 🎧"):
            full_narration_text = st.session_state.story_data.get('title', '') + ". " + " ".join([scene['text'] for scene in st.session_state.story_data['scenes']])
            narration_path = generate_narration(full_narration_text, "narration.mp3", elevenlabs_client)
        st.success("Narration generated!")

        with st.spinner("Step 3/4: Generating images... 🎨"):
            for i, scene in enumerate(st.session_state.story_data['scenes']):
                img_path = generate_image_with_dalle(scene['image_prompt'], i, openai_client)
                if img_path:
                    st.session_state.image_paths.append(img_path)
        st.success("All images generated!")
        # Display Title and Story with Images (Article Style)
        st.header("📜 Here is what you asked for...")
        story_data = st.session_state.story_data

        if story_data:
            st.subheader(story_data['title'])
            
            for i, scene in enumerate(story_data['scenes']):
                cols = st.columns([1, 2])  # 1/3rd for image, 2/3rd for text
                with cols[0]:
                    st.image(st.session_state.image_paths[i], use_container_width=True)
                with cols[1]:
                    st.markdown(scene['text'])
                
                st.markdown("---")  # separator like in articles
        
        with st.spinner("Step 4/4: Assembling the final video... 🎬"):
            st.session_state.video_path = images_to_video_ffmpeg(narration_path, st.session_state.story_data['title'])
        st.success("Video assembly complete!")
        
        st.session_state.generation_complete = True
        st.balloons()

    except Exception as e:
        st.error(f"An error occurred: {e}")

# --- Display Results ---

if st.session_state.generation_complete:
    st.header("🎉 Here is a summary video !")

    # Display Video
    if st.session_state.video_path and os.path.exists(st.session_state.video_path):
        video_file = open(st.session_state.video_path, 'rb')
        video_bytes = video_file.read()
        st.video(video_bytes)
        st.download_button(
            label="Download Video",
            data=video_bytes,
            file_name=os.path.basename(st.session_state.video_path),
            mime="video/mp4"
        )
    else:
        st.error("Video file not found.")


