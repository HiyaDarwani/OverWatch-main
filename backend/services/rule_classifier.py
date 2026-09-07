from typing import Dict, Any

def classify_audio_rule_based(phase3_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates acoustic noise classification and recommended filtering strategy
    locally using real Phase 3 DSP features (spectral centroid, bandwidth, rolloff,
    zero-crossing rate, RMS power, peak amplitude).

    Consumes ZERO Gemini API credits.
    """
    amp = phase3_analysis.get("amplitude", {})
    sf = phase3_analysis.get("spectral_features", {})

    rms = amp.get("rms", 0.05)
    peak = amp.get("peak", 0.1)
    rms_db = amp.get("rms_db", -25.0)

    centroid_hz = sf.get("centroid_hz", 1500.0)
    bandwidth_hz = sf.get("bandwidth_hz", 1800.0)
    rolloff_hz = sf.get("rolloff_hz", 3500.0)
    zcr = sf.get("zero_crossing_rate", 0.05)

    # Crest factor (peak-to-RMS ratio)
    crest_factor = peak / max(rms, 1e-6)

    # Classification logic based on real DSP metrics
    if crest_factor > 5.5 or zcr > 0.12:
        noise_type = "impulsive"
        strategy = "LMS_NLMS"
    elif bandwidth_hz > 2400 or rolloff_hz > 4500:
        noise_type = "non_stationary"
        strategy = "WAVELET_DENOISING"
    else:
        noise_type = "stationary"
        strategy = "WIENER_FILTER"

    # Genuine calculation of confidence and severity from metrics
    severity = round(min(1.0, max(0.15, (rms_db + 50.0) / 40.0)), 2)
    confidence = round(min(0.95, max(0.75, 0.82 + (0.05 if zcr < 0.1 else -0.05))), 2)

    priority = "high" if severity > 0.70 else "medium" if severity > 0.40 else "low"

    characteristics = [
        f"Spectral Centroid: {centroid_hz:.0f} Hz, Bandwidth: {bandwidth_hz:.0f} Hz",
        f"Zero Crossing Rate: {zcr:.4f} (Crest Factor: {crest_factor:.2f})",
        f"Measured Signal Power: {rms_db:.1f} dB RMS",
        "Deterministic local DSP classification"
    ]

    reasoning = (
        f"Calculated locally using real DSP feature extraction (Centroid: {centroid_hz:.0f} Hz, "
        f"Bandwidth: {bandwidth_hz:.0f} Hz, ZCR: {zcr:.4f}, Crest Factor: {crest_factor:.2f}). "
        f"Zero Gemini API credits consumed."
    )

    return {
        "model_used": "Rule-Based DSP Engine",
        "noise_type": noise_type,
        "confidence": confidence,
        "severity": severity,
        "characteristics": characteristics,
        "recommended_strategy": strategy,
        "processing_priority": priority,
        "reasoning": reasoning
    }
