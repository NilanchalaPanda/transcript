"""
Batch Dialogue Timestamp Mapper
Processes multiple audio files with their corresponding scripts from CSV
Supports both Hindi and Tamil languages
"""

import json
import csv
import re
from pathlib import Path
import logging
from typing import List, Dict, Optional
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are available"""
    missing_deps = []

    try:
        import whisperx
        logger.info("✅ WhisperX available")
    except ImportError:
        missing_deps.append("whisperx")

    try:
        import librosa
        logger.info("✅ librosa available")
    except ImportError:
        missing_deps.append("librosa")

    if missing_deps:
        logger.error(f"❌ Missing dependencies: {missing_deps}")
        logger.info("Install with: pip install whisperx librosa")
        return False

    return True

def parse_csv_scripts(csv_path: str, language: str) -> List[str]:
    """Parse the CSV file to extract all scripts"""
    scripts = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip the header row
            if row and row[0].strip() in ["Hindi", "Tamil"]:
                continue

            # Get the first column (script text)
            if row and row[0].strip():
                scripts.append(row[0].strip())

    logger.info(f"📋 Loaded {len(scripts)} scripts from CSV")
    return scripts

def parse_dialogue_script(script_text: str) -> List[Dict[str, str]]:
    """Parse a script text into dialogue lines with speaker labels"""
    dialogues = []

    # Split by newlines and process each line
    lines = script_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove any timestamp annotations like [00:00:01]
        line = re.sub(r'\s*\[[\d:]+\]\s*', '', line)

        # Match pattern "A: text" or "B: text"
        match = re.match(r'^([AB]):\s*(.+)$', line)
        if match:
            speaker = match.group(1)
            text = match.group(2).strip()
            dialogues.append({
                "speaker": speaker,
                "text": text
            })

    return dialogues

def map_dialogue_timestamps(
    merged_audio_path: str,
    dialogue_script: List[Dict[str, str]],
    output_json_path: str,
    file_number: int,
    language_code: str = "hi"
) -> Optional[List[Dict]]:
    """Map dialogue to timestamps for a single audio file"""

    import whisperx
    import librosa

    # Check if merged audio exists
    if not Path(merged_audio_path).exists():
        logger.error(f"❌ File not found: {merged_audio_path}")
        return None

    try:
        # Device settings
        device = "cpu"

        # Load alignment model
        lang_name = "Hindi" if language_code == "hi" else "Tamil"
        logger.info(f"🔄 Loading {lang_name} alignment model...")

        # For Tamil, use Hindi model as fallback since Tamil models don't align well
        if language_code == "ta":
            logger.warning("⚠️  Tamil alignment models have limited accuracy. Using Hindi model which may provide better alignment...")
            # Use Hindi model for Tamil - it often works better for timestamp alignment
            # even though it's not the native language
            model, metadata = whisperx.load_align_model(language_code="hi", device=device)
        else:
            model, metadata = whisperx.load_align_model(language_code=language_code, device=device)

        # Load the merged conversation audio
        logger.info(f"🎤 Loading merged audio: {Path(merged_audio_path).name}")
        merged_audio_data = whisperx.load_audio(merged_audio_path)
        duration = librosa.get_duration(y=merged_audio_data, sr=16000)
        logger.info(f"📊 Duration: {duration:.2f} seconds, Dialogues: {len(dialogue_script)}")

        # Combine all dialogue text in conversation order
        full_conversation_text = " ".join([line['text'] for line in dialogue_script])

        # Create segment for the entire conversation
        segments = [{
            "text": full_conversation_text,
            "start": 0.0,
            "end": duration
        }]

        # Perform forced alignment on the full conversation
        logger.info("🔄 Aligning conversation...")
        result = whisperx.align(segments, model, metadata, merged_audio_data, device=device)

        # Extract all words with timestamps
        all_words = []
        for segment in result["segments"]:
            if "words" in segment:
                all_words.extend(segment["words"])

        logger.info(f"✅ Aligned {len(all_words)} words")

        if not all_words:
            logger.error("❌ No words were aligned!")
            return None

        # Map words back to individual dialogue lines
        all_results = []
        word_idx = 0

        for idx, dialogue in enumerate(dialogue_script):
            dialogue_text = dialogue['text'].strip()
            dialogue_words = dialogue_text.split()
            n_words = len(dialogue_words)

            if n_words == 0:
                logger.warning(f"⚠️  Empty dialogue at index {idx + 1}")
                continue

            if word_idx >= len(all_words):
                logger.warning(f"⚠️  Ran out of words at dialogue {idx + 1}")
                break

            # Get the words for this dialogue line
            end_word_idx = min(word_idx + n_words - 1, len(all_words) - 1)
            start_word = all_words[word_idx]
            end_word = all_words[end_word_idx]

            start_time = start_word.get("start", 0.0)
            end_time = end_word.get("end", start_time + 1.0)

            all_results.append({
                "index": idx + 1,
                "speaker": dialogue['speaker'],
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "text": dialogue_text
            })

            word_idx += n_words

        # Save to JSON
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Saved timestamps to {Path(output_json_path).name}")

        return all_results

    except Exception as e:
        logger.error(f"❌ Error processing file {file_number:02d}: {e}")
        import traceback
        traceback.print_exc()
        return None

def batch_process_audio_files(language: str = "hindi"):
    """Main function to batch process all audio files

    Args:
        language: Either 'hindi' or 'tamil'
    """

    # Check dependencies first
    if not check_dependencies():
        return

    # Normalize language input
    language = language.lower()
    if language not in ["hindi", "tamil"]:
        logger.error(f"❌ Invalid language: {language}. Must be 'hindi' or 'tamil'")
        return

    # Set language-specific parameters
    lang_code = "hi" if language == "hindi" else "ta"
    lang_title = language.capitalize()

    # Hindi uses MH_XX.wav format, Tamil uses XX.wav format
    if language == "hindi":
        file_prefix = "MH"
        file_pattern = "MH_*.wav"
    else:
        file_prefix = "MT"  # For output files
        file_pattern = "*.wav"  # Tamil audio files are just numbered

    # Define paths
    base_path = Path(__file__).parent
    csv_path = base_path / f"{lang_title} Scripts.csv"
    merged_audio_dir = base_path / "Merged" / lang_title
    output_dir = base_path / "JSON with Timestamps" / lang_title

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Output directory: {output_dir}")

    # Check if CSV exists
    if not csv_path.exists():
        logger.error(f"❌ CSV file not found: {csv_path}")
        return

    # Parse all scripts from CSV
    logger.info(f"📖 Reading scripts from: {csv_path}")
    scripts = parse_csv_scripts(str(csv_path), language)

    if not scripts:
        logger.error("❌ No scripts found in CSV")
        return

    # Find all merged audio files
    all_files = sorted(merged_audio_dir.glob(file_pattern))
    # Filter out hidden files like .DS_Store
    audio_files = [f for f in all_files if f.suffix == '.wav']
    logger.info(f"🎵 Found {len(audio_files)} audio files")

    if not audio_files:
        logger.error(f"❌ No audio files found in {merged_audio_dir}")
        return

    # Process each audio file
    logger.info("\n" + "="*60)
    logger.info("🚀 Starting batch processing...")
    logger.info("="*60 + "\n")

    success_count = 0
    failed_files = []

    for audio_file in audio_files:
        # Extract file number from filename
        # Hindi: MH_01.wav -> 1, Tamil: 01.wav -> 1
        if language == "hindi":
            match = re.match(r'MH_(\d+)\.wav', audio_file.name)
        else:
            match = re.match(r'(\d+)\.wav', audio_file.name)

        if not match:
            logger.warning(f"⚠️  Skipping file with unexpected name: {audio_file.name}")
            continue

        file_number = int(match.group(1))

        # Get corresponding script (1-indexed in scripts list)
        if file_number > len(scripts):
            logger.error(f"❌ No script found for {audio_file.name} (index {file_number})")
            failed_files.append(audio_file.name)
            continue

        script_text = scripts[file_number - 1]

        # Parse the script
        dialogue_script = parse_dialogue_script(script_text)

        if not dialogue_script:
            logger.error(f"❌ No dialogues parsed from script for {audio_file.name}")
            failed_files.append(audio_file.name)
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {audio_file.name} ({file_number}/{len(audio_files)})")
        logger.info(f"{'='*60}")

        # Define output path
        output_json = output_dir / f"{file_prefix}_{file_number:02d}.json"

        # Process the file
        result = map_dialogue_timestamps(
            str(audio_file),
            dialogue_script,
            str(output_json),
            file_number,
            lang_code
        )

        if result:
            success_count += 1
            logger.info(f"✅ Successfully processed {audio_file.name}")
        else:
            failed_files.append(audio_file.name)
            logger.error(f"❌ Failed to process {audio_file.name}")

    # Final summary
    logger.info("\n" + "="*60)
    logger.info("📊 BATCH PROCESSING SUMMARY")
    logger.info("="*60)
    logger.info(f"✅ Successfully processed: {success_count}/{len(audio_files)} files")

    if failed_files:
        logger.info(f"❌ Failed files ({len(failed_files)}):")
        for failed in failed_files:
            logger.info(f"   - {failed}")
    else:
        logger.info("🎉 All files processed successfully!")

    logger.info(f"\n📁 Output location: {output_dir}")
    logger.info("="*60)

if __name__ == "__main__":
    logger.info("🚀 Starting Batch Dialogue Timestamp Mapper")
    logger.info("="*60)

    # Get language from command line argument (default: hindi)
    language = sys.argv[1] if len(sys.argv) > 1 else "hindi"

    logger.info(f"📝 Language: {language.capitalize()}")
    logger.info("="*60 + "\n")

    batch_process_audio_files(language)
