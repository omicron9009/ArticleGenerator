import os
import requests
import glob
import random
import json
import ffmpeg
from ffmpeg._run import Error as FFmpegError
import openai
from elevenlabs.client import ElevenLabs
from mutagen.mp3 import MP3
from io import BytesIO
from PIL import Image
import os
import google.genai as genai
from google.genai import types
# pydub is used for handling audio conversion
# You may need to install it: pip install pydub
# pydub also requires ffmpeg to be installed on your system.
from pydub import AudioSegment

# Define directories
IMAGE_DIR = "output_images"
VIDEO_DIR = "output_videos"
MUSIC_DIR = "music"

# ========================
# 1. SETUP & CONFIGURATION
# ========================

def initialize_clients(openai_key, elevenlabs_key):
    """Initializes and returns API clients."""
    try:
        openai_client = openai.OpenAI(api_key=openai_key)
        elevenlabs_client = ElevenLabs(api_key=elevenlabs_key)
        # Ensure directories exist
        os.makedirs(IMAGE_DIR, exist_ok=True)
        os.makedirs(VIDEO_DIR, exist_ok=True)
        os.makedirs(MUSIC_DIR, exist_ok=True)
        return openai_client, elevenlabs_client
    except Exception as e:
        raise ConnectionError(f"Failed to initialize API clients: {e}")

# ========================
# 2. CORE GENERATION FUNCTIONS
# ========================

def generate_story_with_prompts(user_prompt, openai_client):
    """
    Generates a story with scenes and image prompts using OpenAI's GPT model.
    """
    print("✍️  Generating story and image prompts...")
    system_prompt = """
    You are a creative content generator. Based on the user's prompt, generate engaging text.
    The content should be strictly structured as a JSON object with a 'title' and a list of 5 'scenes'.
    Each scene in the list should be an object containing two keys:
    1. 'text': A paragraph of the story (about 30-50 words).
    2. 'image_prompt': A descriptive, visually rich prompt for DALL-E 3. This prompt should be detailed, focusing on art style (e.g., cinematic, digital art, photorealistic), lighting, and mood.
    
    Example output format:
    {
      "title": "The Last Stargazer",
      "scenes": [
        {
          "text": "In a city of perpetual twilight, Elias adjusted the lens of his grandfather's brass telescope, the city's neon glow reflecting in his determined eyes.",
          "image_prompt": "Cinematic shot of a young man on a futuristic city rooftop at dusk, looking through a vintage brass telescope. The scene is filled with dramatic lighting from neon signs, casting long shadows. Digital art, hyper-detailed."
        }
      ]
    }
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        story_data = json.loads(response.choices[0].message.content)
        print("✅ Story generated successfully.")
        return story_data
    except Exception as e:
        print(f"❌ Error generating story: {e}")
        raise

def generate_image_with_dalle(prompt, index, openai_client):
    """
    Generates an image using DALL-E 3, downloads it, and saves it.
    """
    print(f"🎨 Generating image for scene {index+1}...")
    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        
        # Download and save the image
        image_response = requests.get(image_url)
        image = Image.open(BytesIO(image_response.content))
        
        image_path = os.path.join(IMAGE_DIR, f"scene_{index+1}.png")
        image.save(image_path)
        
        print(f"✅ Image saved at: {image_path}")
        return image_path
    except Exception as e:
        print(f"❌ Error generating image for scene {index+1}: {e}")
        raise

def generate_narration(story_text, filename, gemini_client, voice_id="Kore"):
    """
    Generates narration audio as an MP3 file using the Gemini API.

    Args:
        story_text (str): The text to be converted to speech.
        filename (str): The name of the output audio file (e.g., "narration.mp3").
        gemini_client (genai.GenerativeModel): An initialized Gemini API client.
        voice_id (str): The prebuilt voice name for generation (e.g., 'Kore', 'Puck').
    
    Returns:
        str: The full path to the saved audio file, or None if an error occurred.
    """
    print("🎧 Generating narration with Gemini (for MP3 output)...")
    try:
        # --- Gemini API Call ---
        # This remains the same, as we get raw PCM audio data from the API.
        response = gemini_client.generate_content(
           model="gemini-2.5-flash-preview-tts",
           contents=[f"Say calmly: {story_text}"],
           generation_config=types.GenerationConfig(
              response_modalities=["AUDIO"],
              speech_config=types.SpeechConfig(
                 voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                       voice_name=voice_id,
                    )
                 )
              ),
           )
        )

        # Extract the raw audio data from the response
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        
        # --- File Saving (MP3 Conversion) ---
        # The API returns raw PCM data. We use pydub to interpret this data
        # and then export it to the desired MP3 format.
        audio_path = os.path.join(VIDEO_DIR, filename)
        
        # Create an AudioSegment from the raw PCM data
        # Gemini TTS provides 24000 Hz, 16-bit (2 bytes), mono (1 channel) audio
        audio_segment = AudioSegment(
            data=audio_data,
            sample_width=2,  # 2 bytes = 16-bit
            frame_rate=24000,
            channels=1
        )
        
        # Export the audio segment to an MP3 file
        audio_segment.export(audio_path, format="mp3")
            
        print(f"✅ Narration saved as MP3: {audio_path}")
        return audio_path
        
    except Exception as e:
        # --- Error Handling ---
        print(f"❌ Gemini TTS Error or MP3 Conversion Error: {str(e)}")
        raise

# ================================================================
# 3. VIDEO COMPOSITION FUNCTION (CORRECTED VERSION)
# ================================================================

def images_to_video_ffmpeg(narration_audio_path, video_title="final_video"):
    """Creates a video from images, narration, and background music using FFmpeg."""
    print("🎬 Assembling the video...")
    try:
        image_paths = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.png")))
        if not image_paths:
            raise ValueError("❌ No images found to create a video.")

        narration_audio = MP3(narration_audio_path)
        total_duration = narration_audio.info.length
        duration_per_image = total_duration / len(image_paths)

        music_files = glob.glob(os.path.join(MUSIC_DIR, "*.mp3"))
        if not music_files:
            raise ValueError("❌ No background music found in music/ directory.")
        bg_music_path = random.choice(music_files)

        # Define temporary and final file paths
        list_file = "image_list.txt"
        slideshow_path = os.path.join(VIDEO_DIR, "temp_video.mp4")
        looped_music_path = os.path.join(VIDEO_DIR, "looped_bg_music.mp3")
        quiet_bg_music = os.path.join(VIDEO_DIR, "quiet_bg_music.mp3")
        mixed_audio_path = os.path.join(VIDEO_DIR, "mixed_audio.m4a")
        final_output_path = os.path.join(VIDEO_DIR, f"{video_title.replace(' ', '_').lower()}.mp4")

        # Step 1: Create image list file for ffmpeg
        with open(list_file, 'w', encoding='utf-8') as f:
            for path in image_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
                f.write(f"duration {duration_per_image:.2f}\n")
            f.write(f"file '{os.path.abspath(image_paths[-1])}'\n")

        # Step 2: Create a silent slideshow video from images
        (
            ffmpeg
            .input(list_file, format='concat', safe=0)
            .output(slideshow_path, vcodec='libx264', pix_fmt='yuv420p', r=24, t=total_duration)
            .run(overwrite_output=True, quiet=True)
        )

        # Step 3: Loop background music and lower its volume
        (
            ffmpeg
            .input(bg_music_path, stream_loop=-1)
            .output(looped_music_path, t=total_duration, acodec='libmp3lame')
            .run(overwrite_output=True, quiet=True)
        )
        (
            ffmpeg
            .input(looped_music_path)
            .filter('volume', 0.2) # Lowered volume a bit more for clarity
            .output(quiet_bg_music, acodec='libmp3lame')
            .run(overwrite_output=True, quiet=True)
        )

        # Step 4: Mix narration and quiet background music
        narration = ffmpeg.input(narration_audio_path)
        quiet_music = ffmpeg.input(quiet_bg_music)
        mixed_audio = ffmpeg.filter_([narration, quiet_music], 'amix', inputs=2, duration='first')
        ffmpeg.output(mixed_audio, mixed_audio_path, acodec='aac').run(overwrite_output=True, quiet=True)

        # Step 5: Combine the silent slideshow and the mixed audio
        video_input = ffmpeg.input(slideshow_path)
        audio_input = ffmpeg.input(mixed_audio_path)
        (
            ffmpeg
            .output(video_input, audio_input, final_output_path, vcodec='libx264', acodec='aac', shortest=None)
            .run(overwrite_output=True, quiet=True)
        )

        # Cleanup temporary files
        os.remove(list_file)
        os.remove(slideshow_path)
        os.remove(looped_music_path)
        os.remove(quiet_bg_music)
        os.remove(mixed_audio_path)

        print(f"✅ Final video saved at: {final_output_path}")
        return final_output_path

    except FFmpegError as e:
        print("❌ FFmpeg error occurred:")
        print("STDOUT:", e.stdout.decode('utf-8') if e.stdout else "No stdout")
        print("STDERR:", e.stderr.decode('utf-8') if e.stderr else "No stderr")
        raise
    except Exception as ex:
        print(f"❌ General video creation error: {ex}")
        raise

# ========================
# 4. UTILITY FUNCTIONS
# ========================

def cleanup_images():
    """Removes generated images from the output directory."""
    files = glob.glob(os.path.join(IMAGE_DIR, "*.png"))
    for f in files:
        os.remove(f)

    print("🧹 Cleaned up generated images.")
