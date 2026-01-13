"""
Audio processing service.
Handles audio file operations and metadata extraction.
"""
from fastapi import UploadFile
import aiofiles
import os
import ffmpeg
from typing import Optional


class AudioService:
    """Service for audio file operations."""

    async def save_uploaded_file(self, upload_file: UploadFile, destination: str) -> int:
        """
        Save uploaded file to disk asynchronously.

        Args:
            upload_file: Uploaded file from FastAPI
            destination: Destination file path

        Returns:
            File size in bytes

        Raises:
            Exception: If file save fails
        """
        file_size = 0

        async with aiofiles.open(destination, 'wb') as f:
            # Read and write file in chunks
            while chunk := await upload_file.read(8192):  # 8KB chunks
                await f.write(chunk)
                file_size += len(chunk)

        return file_size

    async def get_audio_duration(self, file_path: str) -> Optional[float]:
        """
        Get duration of audio file using ffmpeg.

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds, or None if unable to determine

        Raises:
            Exception: If ffmpeg probe fails
        """
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            print(f"Warning: Could not get audio duration: {e}")
            return None

    async def convert_audio_format(
        self,
        input_path: str,
        output_path: str,
        output_format: str = "mp3"
    ) -> bool:
        """
        Convert audio file to different format using ffmpeg.

        Args:
            input_path: Input file path
            output_path: Output file path
            output_format: Target format (mp3, wav, etc.)

        Returns:
            True if conversion successful

        Raises:
            Exception: If conversion fails
        """
        try:
            (
                ffmpeg
                .input(input_path)
                .output(output_path, format=output_format)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return True
        except ffmpeg.Error as e:
            print(f"FFmpeg error: {e.stderr.decode()}")
            raise Exception(f"Audio conversion failed: {e.stderr.decode()}")

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from disk.

        Args:
            file_path: Path to file

        Returns:
            True if deleted, False if file doesn't exist
        """
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
