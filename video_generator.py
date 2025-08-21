import os
import requests
import glob
import random
import json
import ffmpeg
from ffmpeg._run import Error as FFmpegError
import wave
from google import genai
from google.genai import types
from io import BytesIO
from PIL import Image
import re

# Define directories
IMAGE_DIR = "output_images"
VIDEO_DIR = "output_videos"
MUSIC_DIR = "music"

# ========================
# 1. SETUP & CONFIGURATION
# ========================

def initialize_clients(google_api_key, elevenlabs_api_key=None):
    """Initializes all API clients and creates necessary directories."""
    try:
        # Create Gemini client for story generation, image generation, and TTS
        gemini_client = genai.Client(api_key=google_api_key)
        
        # Ensure output directories exist
        os.makedirs(IMAGE_DIR, exist_ok=True)
        os.makedirs(VIDEO_DIR, exist_ok=True)
        os.makedirs(MUSIC_DIR, exist_ok=True)
        
        return gemini_client
    except Exception as e:
        raise ConnectionError(f"Failed to initialize API clients: {e}")

# ========================
# 2. CORE GENERATION FUNCTIONS
# ========================

def generate_story_with_prompts(user_prompt, gemini_client):
    """Generates a story with scenes and image prompts using Gemini."""
    print("✍️  Generating story and image prompts...")
    system_prompt = """
    You are a creative content generator. Based on the user's prompt, generate a JSON object with a 'title' and a list of 5 'scenes'.
    Each scene object must contain two keys:
    1. 'text': A paragraph of the story (about 30-50 words).
    2. 'image_prompt': A descriptive, visually rich prompt for image generation. Focus on art style (e.g., cinematic, digital art, photorealistic), lighting, and mood.
    
    Return only valid JSON format.
    """
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[f"{system_prompt}\n\nUser prompt: {user_prompt}"],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        story_data = json.loads(response.text)
        print("✅ Story generated successfully.")
        return story_data
    except Exception as e:
        print(f"❌ Error generating story: {e}")
        raise

def generate_image_with_gemini(prompt, index, gemini_client):
    """
    Generates an image using Gemini and saves it.
    """
    print(f"🎨 Generating image for scene {index+1} with Gemini...")
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

def clean_story(text):
    """Clean story text for better TTS output"""
    # Remove extra whitespace and normalize text
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove any problematic characters that might cause TTS issues
    text = re.sub(r'[^\w\s.,!?;:\'-]', '', text)
    return text

def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Helper function to save PCM data as a WAV file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def generate_narration_elevenlabs(story_text, filename, elevenlabs_client=None, voice_id="Kore"):
    """
    Generates narration audio using Gemini TTS and saves it as a WAV file.
    Note: Despite the function name, this now uses Gemini TTS for consistency.
    """
    print("🎧 Generating narration with Gemini TTS...")
    
    # Clean the story text
    story_text = clean_story(story_text)
    
    try:
        # Use Gemini client for TTS generation
        client = genai.Client()
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=f"Say calmly and with emotion: {story_text}",
            config=types.GenerateContentConfig(
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
        
        # Fix: Handle the response structure properly
        audio_data = None
        
        # Check if response has candidates and iterate through parts
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data is not None:
                        audio_data = part.inline_data.data
                        break
        
        if audio_data is None:
            raise ValueError("No audio data found in response")
        
        # Save to file using wave module
        os.makedirs(VIDEO_DIR, exist_ok=True)
        # Change extension to .wav since Gemini outputs WAV format
        if filename.endswith('.mp3'):
            filename = filename.replace('.mp3', '.wav')
        audio_path = os.path.join(VIDEO_DIR, filename)
        
        # Use the wave_file helper function to save
        wave_file(audio_path, audio_data)
        
        print(f"✅ Narration saved as WAV: {audio_path}")
        return audio_path

    except Exception as e:
        print(f"❌ Gemini TTS Error: {str(e)}")
        print(f"Response structure debug: {type(response)}")
        if hasattr(response, 'candidates'):
            print(f"Candidates: {len(response.candidates) if response.candidates else 0}")
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                print(f"Candidate content: {hasattr(candidate, 'content')}")
                if hasattr(candidate, 'content'):
                    print(f"Content parts: {hasattr(candidate.content, 'parts')}")
                    if hasattr(candidate.content, 'parts'):
                        print(f"Parts type: {type(candidate.content.parts)}")
                        print(f"Parts length: {len(candidate.content.parts) if candidate.content.parts else 0}")
        raise

# ========================
# 3. VIDEO COMPOSITION
# ========================

def images_to_video_ffmpeg(narration_audio_path, video_title="final_video"):
    """Creates a video from images, narration, and music using FFmpeg."""
    print("🎬 Assembling the video...")
    try:
        image_paths = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.png")))
        if not image_paths:
            raise ValueError("❌ No images found to create a video.")

        # Get audio duration using ffmpeg.probe
        probe = ffmpeg.probe(narration_audio_path)
        total_duration = float(probe['format']['duration'])
        duration_per_image = total_duration / len(image_paths)

        music_files = glob.glob(os.path.join(MUSIC_DIR, "*.mp3"))
        if not music_files:
            print("⚠️ No background music found in music/ directory. Using narration only.")
            bg_music_path = None
        else:
            bg_music_path = random.choice(music_files)

        # Create slideshow from images
        inputs = []
        for img in image_paths:
            inputs.append(
                ffmpeg.input(img, loop=1, t=duration_per_image)
                .filter('scale', 1024, 1024)
                .filter('zoompan', z='1.1', d=duration_per_image*25, s='1024x1024')
            )

        # Concatenate all image inputs
        video_stream = ffmpeg.concat(*inputs, v=1, a=0).filter('fps', fps=25)

        # Prepare audio inputs
        narration_audio = ffmpeg.input(narration_audio_path)
        
        if bg_music_path:
            music_audio = ffmpeg.input(bg_music_path, stream_loop=-1).filter('volume', 0.2)
            # Mix audio tracks
            mixed_audio = ffmpeg.filter([narration_audio, music_audio], 'amix', duration='first', dropout_transition=1)
        else:
            mixed_audio = narration_audio
        
        final_output_path = os.path.join(VIDEO_DIR, f"{video_title.replace(' ', '_').lower()}.mp4")
        
        # Combine video and mixed audio
        (
            ffmpeg
            .output(video_stream, mixed_audio, final_output_path, 
                   vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
            .overwrite_output()
            .run(quiet=True)
        )
        
        print(f"✅ Final video saved: {final_output_path}")
        return final_output_path

    except FFmpegError as e:
        print("❌ FFmpeg error occurred:")
        print("STDOUT:", e.stdout.decode() if e.stdout else "N/A")
        print("STDERR:", e.stderr.decode() if e.stderr else "N/A")
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
