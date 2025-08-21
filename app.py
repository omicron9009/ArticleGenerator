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

# Custom CSS for absolutely stunning UI
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

/* Global Styles */
* {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Hero Section */
.hero-container {
    background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
    backdrop-filter: blur(20px);
    border-radius: 30px;
    padding: 60px 40px;
    margin: 20px 0 40px 0;
    border: 1px solid rgba(255,255,255,0.2);
    box-shadow: 0 25px 50px rgba(0,0,0,0.15);
    text-align: center;
    position: relative;
    overflow: hidden;
}

.hero-container::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    animation: rotate 20s linear infinite;
}

@keyframes rotate {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.hero-title {
    font-size: 4.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #fff 0%, #f0f0f0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 20px;
    text-shadow: 0 0 30px rgba(255,255,255,0.3);
    position: relative;
    z-index: 1;
}

.hero-subtitle {
    font-size: 1.4rem;
    color: rgba(255,255,255,0.9);
    font-weight: 300;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    position: relative;
    z-index: 1;
}

/* Form Container */
.form-container {
    background: linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.08) 100%);
    backdrop-filter: blur(25px);
    border-radius: 25px;
    padding: 40px;
    margin: 30px 0;
    border: 1px solid rgba(255,255,255,0.3);
    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
}

/* Input Styling */
.stTextArea textarea {
    background: rgba(255,255,255,0.1) !important;
    border: 2px solid rgba(255,255,255,0.3) !important;
    border-radius: 15px !important;
    color: white !important;
    font-size: 16px !important;
    padding: 20px !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.3s ease !important;
}

.stTextArea textarea:focus {
    border-color: rgba(255,255,255,0.6) !important;
    box-shadow: 0 0 20px rgba(255,255,255,0.2) !important;
    transform: translateY(-2px) !important;
}

.stTextArea label {
    color: white !important;
    font-weight: 600 !important;
    font-size: 18px !important;
    margin-bottom: 10px !important;
}

/* Button Styling */
.stButton button {
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%) !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 15px 50px !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    color: white !important;
    box-shadow: 0 15px 30px rgba(255,107,107,0.4) !important;
    transition: all 0.3s ease !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}

.stButton button:hover {
    transform: translateY(-5px) !important;
    box-shadow: 0 20px 40px rgba(255,107,107,0.6) !important;
    background: linear-gradient(135deg, #ff7675 0%, #fd79a8 100%) !important;
}

/* Progress and Status */
.stSpinner > div {
    border-color: rgba(255,255,255,0.3) !important;
    border-top-color: #ff6b6b !important;
}

.stSuccess {
    background: linear-gradient(135deg, rgba(0,255,127,0.2) 0%, rgba(0,255,127,0.1) 100%) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(0,255,127,0.3) !important;
    border-radius: 15px !important;
    color: white !important;
}

.stError {
    background: linear-gradient(135deg, rgba(255,107,107,0.2) 0%, rgba(255,107,107,0.1) 100%) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255,107,107,0.3) !important;
    border-radius: 15px !important;
    color: white !important;
}

/* Content Cards */
.content-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%);
    backdrop-filter: blur(20px);
    border-radius: 20px;
    padding: 30px;
    margin: 20px 0;
    border: 1px solid rgba(255,255,255,0.2);
    box-shadow: 0 15px 35px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
}

.content-card:hover {
    transform: translateY(-10px);
    box-shadow: 0 25px 50px rgba(0,0,0,0.2);
}

/* Headers */
.stHeader h1, .stHeader h2, .stHeader h3 {
    color: white !important;
    text-align: center !important;
    font-weight: 700 !important;
    text-shadow: 0 2px 10px rgba(0,0,0,0.3) !important;
}

.stSubheader {
    color: rgba(255,255,255,0.9) !important;
    font-weight: 600 !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
    padding: 15px 25px;
    border-radius: 15px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
    margin: 20px 0;
}

/* Image Containers */
.stImage {
    border-radius: 20px !important;
    overflow: hidden !important;
    box-shadow: 0 15px 30px rgba(0,0,0,0.2) !important;
    transition: all 0.3s ease !important;
}

.stImage:hover {
    transform: scale(1.05) !important;
    box-shadow: 0 20px 40px rgba(0,0,0,0.3) !important;
}

/* Video Player */
.stVideo {
    border-radius: 20px !important;
    overflow: hidden !important;
    box-shadow: 0 25px 50px rgba(0,0,0,0.3) !important;
    backdrop-filter: blur(10px) !important;
}

/* Download Button */
.stDownloadButton button {
    background: linear-gradient(135deg, #00cec9 0%, #55a3ff 100%) !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 12px 30px !important;
    font-weight: 600 !important;
    color: white !important;
    box-shadow: 0 10px 20px rgba(0,206,201,0.4) !important;
    transition: all 0.3s ease !important;
}

.stDownloadButton button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 15px 30px rgba(0,206,201,0.6) !important;
}

/* Columns */
.stColumns {
    gap: 30px !important;
}

/* Separators */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%) !important;
    margin: 30px 0 !important;
}

/* Balloons animation enhancement */
.stBalloons {
    z-index: 9999 !important;
}

/* Responsive Design */
@media (max-width: 768px) {
    .hero-title {
        font-size: 2.5rem;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
    }
    
    .form-container, .content-card {
        padding: 20px;
        margin: 15px 0;
    }
}

/* Glassmorphism Enhancement */
.glass-effect {
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(30px);
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 
        0 8px 32px rgba(0,0,0,0.1),
        inset 0 1px 0 rgba(255,255,255,0.2);
}

/* Floating Animation */
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-20px); }
}

.floating {
    animation: float 6s ease-in-out infinite;
}

/* Pulse Animation */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.pulse {
    animation: pulse 2s ease-in-out infinite;
}
</style>
""", unsafe_allow_html=True)

# --- Hero Section ---
st.markdown("""
<div class="hero-container floating">
    <h1 class="hero-title">✨ VISIONARY ✨</h1>
    <p class="hero-subtitle">
        Transform your wildest ideas into cinematic masterpieces with AI magic.<br>
        One prompt. Infinite possibilities. Pure creative power at your fingertips.
    </p>
</div>
""", unsafe_allow_html=True)

# --- API Key Management ---
try:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
except KeyError:
    st.error("🔑 API keys not found in st.secrets. Please add them to your .streamlit/secrets.toml file.")
    st.stop()

# --- Initialize Session State ---
if 'generation_complete' not in st.session_state:
    st.session_state.generation_complete = False
    st.session_state.story_data = None
    st.session_state.image_paths = []
    st.session_state.video_path = None

# --- User Input Form ---
# st.markdown('<div class="form-container glass-effect">', unsafe_allow_html=True)

with st.form("video_form"):
    st.markdown("### 🚀 What shall we bring to life?")
    user_prompt = st.text_area(
        "Describe your vision:", 
        "A lone astronaut discovering a glowing forest on a distant moon.",
        height=120,
        help="Be as creative as you want! The AI will transform your words into visual magic."
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        submitted = st.form_submit_button("Generate", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

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
        with st.spinner("🧠 Crafting your story with AI brilliance..."):
            st.session_state.story_data = generate_story_with_prompts(user_prompt, openai_client)
        st.success("✨ Story crafted to perfection!")

        with st.spinner("🎙️ Breathing life into words with cinematic narration..."):
            full_narration_text = st.session_state.story_data.get('title', '') + ". " + " ".join([scene['text'] for scene in st.session_state.story_data['scenes']])
            narration_path = generate_narration(full_narration_text, "narration.mp3", elevenlabs_client)
        st.success("🎧 Narration perfected!")

        with st.spinner("🎨 Painting your imagination with AI artistry..."):
            for i, scene in enumerate(st.session_state.story_data['scenes']):
                img_path = generate_image_with_dalle(scene['image_prompt'], i, openai_client)
                if img_path:
                    st.session_state.image_paths.append(img_path)
        st.success("🖼️ Visual masterpieces created!")
        
        # Display Story Content
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("## 📖 Your Story Unveiled")
        
        story_data = st.session_state.story_data
        if story_data:
            st.markdown(f"### {story_data['title']}")
            
            for i, scene in enumerate(story_data['scenes']):
                col1, col2 = st.columns([1, 2])
                with col1:
                    if i < len(st.session_state.image_paths):
                        st.image(st.session_state.image_paths[i], use_container_width=True)
                with col2:
                    st.markdown(f"*{scene['text']}*")
                
                if i < len(story_data['scenes']) - 1:
                    st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.spinner("🎬 Weaving everything into cinematic gold..."):
            st.session_state.video_path = images_to_video_ffmpeg(narration_path, st.session_state.story_data['title'])
        st.success("🎉 Cinematic masterpiece completed!")
        
        st.session_state.generation_complete = True
        st.balloons()

    except Exception as e:
        st.error(f"⚠️ Creative process interrupted: {e}")

# --- Display Results ---
if st.session_state.generation_complete:
    st.markdown('<div class="content-card pulse">', unsafe_allow_html=True)
    st.markdown("## 🏆 Behold Your Masterpiece")
    
    # Display Video
    if st.session_state.video_path and os.path.exists(st.session_state.video_path):
        video_file = open(st.session_state.video_path, 'rb')
        video_bytes = video_file.read()
        
        col1, col2, col3 = st.columns([0.5, 2, 0.5])
        with col2:
            st.video(video_bytes)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.download_button(
                label="⬇️ Download Your Creation",
                data=video_bytes,
                file_name=os.path.basename(st.session_state.video_path),
                mime="video/mp4",
                use_container_width=True
            )
    else:
        st.error("🎬 Video file not found. The magic seems to have gone missing!")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; padding: 40px 0 20px 0; color: rgba(255,255,255,0.6);">
    <p style="font-size: 14px; margin: 0;">✨ Powered by AI Magic & Creative Vision ✨</p>
</div>

""", unsafe_allow_html=True)
