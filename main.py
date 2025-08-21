import os
import requests
import glob
import random
import json
import ffmpeg
from ffmpeg._run import Error as FFmpegError
import openai
import elevenlabs
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from elevenlabs.client import ElevenLabs
# ========================
# 1. SETUP & CONFIGURATION
# ========================

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Check if API keys are set
if not OPENAI_API_KEY or not ELEVENLABS_API_KEY:
    raise ValueError("❌ API keys for OpenAI and ElevenLabs must be set in the .env file.")

# Initialize API clients
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
elevenlabs.api_key = ELEVENLABS_API_KEY
# Initialize ElevenLabs client
elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")  # Or replace with your API key directly
)


# Define directories
IMAGE_DIR = "output_images"
VIDEO_DIR = "output_videos"
MUSIC_DIR = "music"

# ========================
# 2. CORE GENERATION FUNCTIONS
# ========================

def generate_story_with_prompts(user_prompt):
    """
    Generates a content with scenes and image prompts using OpenAI's GPT model.
    """
    print("✍️  Generating story and image prompts...")
    system_prompt = """
    You are a general content generator. Based on the user's prompt, generate texts.
    The content should be strictly structured as a JSON object with a 'title' and a list of 5 'scenes'.
    Each scene in the list should be an object containing two keys:
    1. 'text': A paragraph of the story (about 30-50 words).
    2. 'image_prompt': A descriptive, visually rich prompt for an image generation AI (like DALL-E).
    
    Strict output format:
    {
      "title": "The Last Stargazer",
      "scenes": [
        {
          "text": "In a city of perpetual twilight, Elias adjusted the lens of his grandfather's brass telescope...",
          "image_prompt": "A solitary figure on a futuristic city rooftop at dusk, looking through a vintage brass telescope..."
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
        print(story_data)
        return story_data
    except Exception as e:
        print(f"❌ Error generating story: {e}")
        raise

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os

# Gemini client
gemini_client = genai.Client()

def generate_image(prompt, index):
    """
    Generates an image using Gemini and saves it.
    """
    print(f"🎨 Generating image for scene {index+1}...")
    try:
        # Generate content (image + optional text)
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )

        # Make sure output directory exists
        os.makedirs(IMAGE_DIR, exist_ok=True)
        image_path = os.path.join(IMAGE_DIR, f"scene_{index+1}.png")

        # Loop through candidates and save images
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(image_path)
                print(f"✅ Image saved at: {image_path}")
                return image_path
        
        print(f"⚠️ No image data returned for scene {index+1}")
        return None

    except Exception as e:
        print(f"❌ Error generating image for scene {index+1}: {e}")
        return None

def clean_story(story_text):
    # Stub: implement your cleaning logic here if needed
    return story_text

def generate_narration(story_text, filename, voice_id="G17SuINrv2H9FC6nvetn"):
    story_text=clean_story(story_text)
    # voice_id="yFJbqk0f3hzpxkA3vSqT"
    try:
        # Stream audio
        audio_stream = elevenlabs.text_to_speech.stream(
            text=story_text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2"
        )

        # Collect chunks
        audio_bytes = b""
        for chunk in audio_stream:
            if isinstance(chunk, bytes):
                audio_bytes += chunk

        # Save to file
        os.makedirs("output_videos", exist_ok=True)
        audio_path = os.path.join("output_videos", filename)
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        print("🎧 Narration saved:", audio_path)
        return audio_path

    except Exception as e:
        print("❌ ElevenLabs TTS Error:", str(e))
        return None

# ========================
# 3. VIDEO COMPOSITION FUNCTION
# ========================

import os
import glob
import random
import ffmpeg
from mutagen.mp3 import MP3

def images_to_video_ffmpeg(image_dir, narration_audio_path, output_dir):
    try:
        music_dir = "music"
        image_paths = sorted(glob.glob(os.path.join(image_dir, "*.png")))
        if not image_paths:
            raise ValueError("❌ No images found in the provided directory.")

        narration_audio = MP3(narration_audio_path)
        total_duration = narration_audio.info.length
        duration_per_image = total_duration / len(image_paths)

        music_files = glob.glob(os.path.join(music_dir, "*.mp3"))
        if not music_files:
            raise ValueError("❌ No background music found in music/ directory.")
        bg_music_path = random.choice(music_files)

        os.makedirs(output_dir, exist_ok=True)
        list_file = "image_list.txt"
        slideshow_path = os.path.join(output_dir, "temp_video.mp4")
        looped_music_path = os.path.join(output_dir, "looped_bg_music.mp3")
        quiet_bg_music = os.path.join(output_dir, "quiet_bg_music.mp3")
        mixed_audio_path = os.path.join(output_dir, "mixed_audio.m4a")
        final_output = os.path.join(output_dir, "final_video1.mp4")

        # Step 1: Create image list file
        with open(list_file, 'w') as f:
            for path in image_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
                f.write(f"duration {duration_per_image:.2f}\n")
            f.write(f"file '{os.path.abspath(image_paths[-1])}'\n")

        # Step 2: Create slideshow video
        ffmpeg.input(list_file, format='concat', safe=0).output(
            slideshow_path,
            vcodec='libx264',
            pix_fmt='yuv420p',
            r=1/duration_per_image
        ).run(overwrite_output=True)

        # Step 3: Loop background music and lower its volume
        ffmpeg.input(bg_music_path, stream_loop=-1).output(
            looped_music_path,
            t=total_duration,
            acodec='libmp3lame'
        ).run(overwrite_output=True)

        ffmpeg.input(looped_music_path).filter('volume', 0.5).output(
            quiet_bg_music,
            acodec='libmp3lame'
        ).run(overwrite_output=True)

        # Step 4: Mix narration and quiet background music
        narration = ffmpeg.input(narration_audio_path)
        quiet_music = ffmpeg.input(quiet_bg_music)

        mixed_audio = ffmpeg.filter_(
            [narration, quiet_music],
            'amix',
            inputs=2,
            duration='first',
            dropout_transition=0
        )

        ffmpeg.output(mixed_audio, mixed_audio_path, acodec='aac').run(overwrite_output=True)

        # Step 5: Combine slideshow + mixed audio
        video_input = ffmpeg.input(slideshow_path)
        audio_input = ffmpeg.input(mixed_audio_path)

        ffmpeg.output(
            video_input,
            audio_input,
            final_output,
            vcodec='libx264',
            acodec='aac',
            shortest=None
        ).run(overwrite_output=True)


        # Cleanup
        os.remove(list_file)
        os.remove(slideshow_path)
        os.remove(looped_music_path)
        os.remove(quiet_bg_music)
        os.remove(mixed_audio_path)

        print("✅ Final video saved at:", final_output)
        return final_output

    except FFmpegError as e:
        print("❌ FFmpeg error occurred:")
        print("STDOUT:", e.stdout.decode('utf-8') if e.stdout else "No stdout")
        print("STDERR:", e.stderr.decode('utf-8') if e.stderr else "No stderr")
        raise
    except Exception as ex:
        print("❌ General error:", ex)
        raise
# ========================
# 4. MAIN WORKFLOW
# ========================

def main():
    """
    Main function to run the entire video generation pipeline.
    """
    try:
        # --- Get User Input ---
        user_prompt = input("👉 Enter a prompt for your requirement: ")
        
        # --- Generate Content ---
        story_data = generate_story_with_prompts(user_prompt)
        
        if not story_data or 'scenes' not in story_data:
            print("❌ Failed to generate valid story data. Exiting.")
            return

        # Combine text for narration
        full_narration_text = story_data.get('title', '') + ". " + " ".join([scene['text'] for scene in story_data['scenes']])

        # --- Generate Media ---
        narration_path = generate_narration(full_narration_text, "narration.mp3")
        
        image_paths = []
        for i, scene in enumerate(story_data['scenes']):
            img_path = generate_image(scene['image_prompt'], i)
            if img_path:
                image_paths.append(img_path)
        
        if not narration_path or not image_paths:
            print("❌ Failed to generate required media (audio/images). Exiting.")
            return
            
        # --- Create Video ---
        images_to_video_ffmpeg(IMAGE_DIR, narration_path, VIDEO_DIR)

    except Exception as e:
        print(f"An unexpected error occurred in the main workflow: {e}")
    finally:
        # Clean up the image directory after the run
        if os.path.exists(IMAGE_DIR):
            for file in glob.glob(os.path.join(IMAGE_DIR, "*.png")):
                os.remove(file)
            print("🧹 Cleaned up generated images.")


if __name__ == "__main__":
    main()
