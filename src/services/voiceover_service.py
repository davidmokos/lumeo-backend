import os
import logging
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import openai
import modal
import ffmpeg

from src.database.lecture_repository import LectureRepository
from src.database.storage import StorageClient
from src.schema.lecture import Lecture
from src.schema.scene import Scene

from src.common import vol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# class VoiceoverService:
#     def __init__(self, lecture_id: str):
#         self.lecture_id = lecture_id
#         self.lecture_repo = LectureRepository()
#         self.storage_client = StorageClient()
    
#     def add_audio(self, scene: Scene) -> Scene:
#         pass
    
#     def merge_scenes(self, scenes: list[Scene]) -> Lecture:
#         pass
        


def generate_audio(voiceover_text: str, output_path: str) -> str:
    """
    Generates audio from text using ElevenLabs API.
    
    Args:
        voiceover_text: The text to convert to speech
        output_path: Path where the audio file should be saved
        
    Returns:
        Path to the generated audio file
    """
    logger.info(f"Generating audio for text: {voiceover_text[:50]}...")
    
    try:
        client = ElevenLabs()
        audio = client.text_to_speech.convert(
            text=voiceover_text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        
        # Save the audio to file, handling the streaming response
        with open(output_path, "wb") as f:
            for chunk in audio:
                if chunk:
                    f.write(chunk)
            
        logger.info(f"Audio saved to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        raise

def generate_subtitles(audio_path: str, vtt_file_path: str) -> str:
    """
    Generates VTT subtitles from audio using OpenAI's Whisper API.
    
    Args:
        audio_path: Path to the audio file
        vtt_file_path: Path where the VTT file should be saved
        
    Returns:
        Path to the generated VTT file
    """
    logger.info(f"Generating subtitles for audio: {audio_path}")
    
    try:
        with open(audio_path, "rb") as audio_file:
            # Call OpenAI's Whisper API with direct VTT output
            transcript = openai.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="vtt"
            )
        
        # Save the VTT content directly
        with open(vtt_file_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        
        logger.info(f"Subtitles saved to {vtt_file_path}")
        return vtt_file_path
    except Exception as e:
        logger.error(f"Error generating subtitles: {str(e)}")
        raise


def embed_audio_and_subtitles(sandbox: modal.Sandbox, video_path: str, audio_path: str, vtt_file_path: str, output_path: str) -> str:
    """
    Embeds audio and subtitles into a video using ffmpeg.
    
    Args:
        sandbox: Modal sandbox instance for running ffmpeg
        video_path: Path to the input video
        audio_path: Path to the audio file
        vtt_file_path: Path to the VTT subtitle file
        output_path: Path where the output video should be saved
        
    Returns:
        Path to the output video with embedded audio and subtitles
    """
    logger.info(f"Embedding audio and subtitles into video: {video_path}")
    
    vol.reload()
    
    logger.info(sandbox.ls(path="/data"))
    
    try:
        # Step 1: Combine video and audio
        temp_output = output_path + ".temp.mp4"
        
        # First command: combine video and audio
        result = sandbox.exec(
            "ffmpeg",
            "-i", video_path,      # First input: video
            "-i", audio_path,      # Second input: audio
            "-c:v", "copy",        # Copy video without re-encoding
            "-c:a", "aac",         # Convert audio to AAC
            "-map", "0:v:0",       # Take video from first input
            "-map", "1:a:0",       # Take audio from second input
            "-y",                  # Overwrite output file if exists
            temp_output
        )
        
        # Wait for the first command to complete
        result.wait()
        
        if result.returncode != 0:
            error = result.stderr.read()
            raise Exception(f"ffmpeg error in audio embedding: {error}")
            
        # Step 2: Add subtitles
        result = sandbox.exec(
            "ffmpeg",
            "-i", temp_output,     # Input: combined video
            "-i", vtt_file_path,   # Input: subtitles
            "-c:v", "copy",        # Copy video without re-encoding
            "-c:a", "copy",        # Copy audio without re-encoding
            "-c:s", "mov_text",    # Subtitle codec for MP4
            "-y",                  # Overwrite output file if exists
            output_path
        )
        
        # Wait for the second command to complete
        result.wait()
        
        if result.returncode != 0:
            error = result.stderr.read()
            raise Exception(f"ffmpeg error in subtitle embedding: {error}")
        
        # Clean up temporary file
        sandbox.exec("rm", "-f", temp_output).wait()
        
        logger.info(f"Video with audio and subtitles saved to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error embedding audio and subtitles: {str(e)}")
        # Clean up temporary file in case of error
        try:
            sandbox.exec("rm", "-f", temp_output).wait()
        except:
            pass
        raise

def embed_audio_and_subtitles_new(video_path: str, audio_path: str, vtt_file_path: str, output_path: str) -> str:
    """
    Embeds audio and subtitles into a video using ffmpeg-python.
    
    Args:
        video_path: Path to the input video
        audio_path: Path to the audio file
        vtt_file_path: Path to the VTT subtitle file
        output_path: Path where the output video should be saved
        
    Returns:
        Path to the output video with embedded audio and subtitles
    """
    logger.info(f"Embedding audio and subtitles into video: {video_path}")
    
    try:
        # Step 1: Combine video and audio
        temp_output = output_path + ".temp.mp4"
        
        # First step: combine video and audio
        video = ffmpeg.input(video_path)
        audio = ffmpeg.input(audio_path)
        
        combined = ffmpeg.output(
            video.video,
            audio.audio,
            temp_output,
            vcodec='copy',  # Copy video without re-encoding
            acodec='aac',   # Convert audio to AAC
            y=None          # Overwrite output file if exists
        )
        combined.run(overwrite_output=True)
            
        # Step 2: Add subtitles
        combined_video = ffmpeg.input(temp_output)
        subtitles = ffmpeg.input(vtt_file_path)
        
        final = ffmpeg.output(
            combined_video,
            subtitles,
            output_path,
            vcodec='copy',     # Copy video without re-encoding
            acodec='copy',     # Copy audio without re-encoding
            scodec='mov_text', # Subtitle codec for MP4
            y=None             # Overwrite output file if exists
        )
        final.run(overwrite_output=True)
        
        # Clean up temporary file
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        logger.info(f"Video with audio and subtitles saved to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error embedding audio and subtitles: {str(e)}")
        # Clean up temporary file in case of error
        if os.path.exists(temp_output):
            os.remove(temp_output)
        raise

def add_voiceover_and_subtitles(
    sandbox: modal.Sandbox,
    video_path: str,
    voiceover_text: str,
    output_video_path: str,
    slide_id: str = ""
) -> str:
    """
    Adds voiceover and subtitles to a video.
    
    Args:
        sandbox: Modal sandbox instance for running ffmpeg
        video_path: Path to the input video
        voiceover_text: Text for voiceover and subtitles
        output_video_path: Path where the final video should be saved
        
    Returns:
        Path to the output video with voiceover and subtitles
    """
    logger.info("Starting voiceover and subtitles process")
    
    try:
        # Generate paths for intermediate files
        audio_path = f"/data/voiceover_{slide_id}.mp3"
        vtt_path = f"/data/subtitles_{slide_id}.vtt"
        
        # Generate audio from text
        generate_audio(voiceover_text, audio_path)
        
        # Generate subtitles from audio
        generate_subtitles(audio_path, vtt_path)
        
        # Embed subtitles in video
        final_video = embed_audio_and_subtitles_new(video_path, audio_path, vtt_path, output_video_path)
        
        logger.info("Voiceover and subtitles process completed successfully")
        return final_video
    except Exception as e:
        logger.error(f"Error in voiceover and subtitles process: {str(e)}")
        raise

def merge_videos(sandbox: modal.Sandbox, video_paths: list[str], output_path: str) -> str:
    """
    Merges multiple videos into a single video file using ffmpeg.
    
    Args:
        sandbox: Modal sandbox instance for running ffmpeg
        video_paths: List of paths to input video files
        output_path: Path where the merged video should be saved
        
    Returns:
        Path to the merged video file
    """
    logger.info(f"Merging {len(video_paths)} videos")
    
    try:
        # Create a temporary file list for ffmpeg concat
        concat_file = "/data/concat_list.txt"
        
        # Write the file list in ffmpeg concat format
        with sandbox.open(concat_file, "w") as f:
            for video_path in video_paths:
                f.write(f"file '{video_path}'\n")
        
        # Run ffmpeg concat demuxer
        result = sandbox.exec(
            "ffmpeg",
            "-f", "concat",           # Use concat demuxer
            "-safe", "0",             # Don't restrict files to relative paths
            "-i", concat_file,        # Input file list
            "-c", "copy",             # Copy streams without re-encoding
            "-y",                     # Overwrite output file if exists
            output_path
        )
        
        # Wait for the process to complete
        result.wait()
        
        if result.returncode != 0:
            error = result.stderr.read()
            raise Exception(f"ffmpeg error in video merging: {error}")
        
        # Clean up the temporary file
        sandbox.exec("rm", "-f", concat_file).wait()
        
        logger.info(f"Videos merged successfully to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error merging videos: {str(e)}")
        # Clean up temporary file in case of error
        try:
            sandbox.exec("rm", "-f", concat_file).wait()
        except:
            pass
        raise
