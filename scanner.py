import re
import unicodedata
from typing import Tuple
from config_manager import config_manager
import logging

logger = logging.getLogger("ZeroTrust.Agent.Scanner")
compiled_patterns = []

def init_scanner():
    global compiled_patterns
    patterns = config_manager.config.get("scanner", {}).get("high_risk_patterns", [])
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
    logger.info(f"Scanner initialized with {len(compiled_patterns)} signatures.")

def deobfuscate(text: str) -> str:
    """
    Strips non-printable characters, normalizes unicode, and removes excess whitespace
    to reveal the true semantic payload.
    """
    normalized = unicodedata.normalize('NFKC', text)
    printable = "".join(c for c in normalized if unicodedata.category(c)[0] != "C" or c in "\n\t\r")
    clean_text = re.sub(r'\s+', ' ', printable).strip()
    return clean_text

def analyze_intent(text: str) -> Tuple[bool, str]:
    """
    MVP: Heuristic Signature Scanner.
    Returns (is_high_risk, matched_reason).
    """
    clean_text = deobfuscate(text)
    
    for pattern in compiled_patterns:
        if pattern.search(clean_text):
            return True, f"Matched high-risk signature: {pattern.pattern}"
            
    return False, "Benign"
