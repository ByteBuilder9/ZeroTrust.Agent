import re
import logging
from typing import Tuple
from config_manager import config_manager

logger = logging.getLogger("ZeroTrust.Agent.Scrubber")
compiled_dlp_patterns = {}

def init_scrubber():
    global compiled_dlp_patterns
    patterns = config_manager.config.get("scrubber", {}).get("dlp_patterns", {})
    for label, pattern_str in patterns.items():
        compiled_dlp_patterns[label] = re.compile(pattern_str)
    logger.info(f"Scrubber initialized with {len(compiled_dlp_patterns)} DLP rules.")

def redact_sensitive_data(text: str) -> Tuple[str, bool, str]:
    """
    Scans for and masks sensitive data using compiled regexes.
    Returns (scrubbed_text, was_redacted, reason)
    """
    if not text:
        return text, False, ""

    scrubbed_text = text
    redacted_labels = []
    
    for label, pattern in compiled_dlp_patterns.items():
        if pattern.search(scrubbed_text):
            redacted_labels.append(label)
            scrubbed_text = pattern.sub(f"[REDACTED_{label}]", scrubbed_text)

    was_redacted = len(redacted_labels) > 0
    reason = f"DLP matched: {','.join(redacted_labels)}" if was_redacted else ""

    if was_redacted:
        logger.info(f"DLP engine redacted: {reason}", extra={"extra_info": {"action": "DLP_REDACTION"}})
        
    return scrubbed_text, was_redacted, reason
