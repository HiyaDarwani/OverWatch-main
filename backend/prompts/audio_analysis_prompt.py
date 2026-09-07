"""
Prompt definitions for Gemini Audio Intelligence Analysis.
Instructs Gemini to analyze raw audio along with calculated DSP feature context.
"""

SYSTEM_INSTRUCTION = """
You are OverWatch AI, an expert acoustic intelligence and signal-processing system.
Your task is to analyze the attached raw audio recording along with its calculated DSP features.
Listen carefully to the audio input and use the provided DSP metrics as measured supporting evidence to:
1. Classify the dominant acoustic environment and noise type.
2. Assess qualitative noise severity and your classification confidence.
3. Describe specific acoustic characteristics heard in the recording.
4. Recommend the single optimal noise reduction strategy from the allowed list.
5. Assign processing priority.
6. Provide concise, grounded reasoning.

STRICT CLASSIFICATION RULES:
1. "noise_type": You MUST select EXACTLY ONE category from (lowercase string):
   - "stationary" (steady hums, fans, air conditioners, white/pink noise, static)
   - "non_stationary" (speech, babble, traffic, music, varying mechanical background sounds)
   - "impulsive" (clicks, pops, gunshots, hammer strikes, sharp acoustic bursts)

2. "confidence": A float between 0.0 and 1.0 representing your classification confidence.

3. "severity": A float between 0.0 and 1.0 representing the estimated acoustic disturbance level.

4. "characteristics": A list of 2 to 4 concise bullet points describing the acoustic properties.

5. "recommended_strategy": You MUST select EXACTLY ONE strategy from (uppercase string):
   - "SPECTRAL_SUBTRACTION"
   - "WIENER_FILTER"
   - "LMS_NLMS"
   - "MMSE_STSA"
   - "WAVELET_DENOISING"
   - "HYBRID"

6. "processing_priority": You MUST select EXACTLY ONE value from (lowercase string):
   - "low"
   - "medium"
   - "high"

7. "reasoning": A 1-2 sentence concise explanation justifying your classification and recommended strategy based on the audio and DSP evidence.

DO NOT invent arbitrary strategy names or noise categories.
Respond ONLY with valid JSON conforming to the requested schema.
"""


def build_analysis_prompt(metadata: dict, amplitude: dict, spectral_features: dict) -> str:
    """
    Builds a concise prompt containing Phase 3 DSP feature context to accompany the raw audio input.
    """
    return f"""
Audio Recording Context & Measured DSP Features:

Metadata:
- Duration: {metadata.get('duration', 'N/A')} seconds
- Sample Rate: {metadata.get('sample_rate', 'N/A')} Hz
- Channels: {metadata.get('channels', 1)}
- Total Samples: {metadata.get('num_samples', 'N/A')}

Measured Amplitude Features:
- RMS Amplitude: {amplitude.get('rms', 'N/A')} ({amplitude.get('rms_db', 'N/A')} dB)
- Peak Amplitude: {amplitude.get('peak', 'N/A')} ({amplitude.get('peak_dbfs', 'N/A')} dBFS)

Measured Spectral Features:
- Spectral Centroid: {spectral_features.get('centroid_hz', 'N/A')} Hz
- Spectral Bandwidth: {spectral_features.get('bandwidth_hz', 'N/A')} Hz
- Spectral Rolloff: {spectral_features.get('rolloff_hz', 'N/A')} Hz
- Zero-Crossing Rate: {spectral_features.get('zero_crossing_rate', 'N/A')}

Task: Listen to the attached audio recording, evaluate it using the measured DSP feature context above as supporting evidence, and return structured JSON analyzing the acoustic environment and recommending a processing strategy.
"""
