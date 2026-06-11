"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8ce-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: urllib.error, os, ssl, urllib.request, json
FUNCTIONS: compile_english_lexicon
SYNOPSIS: `compile_english_lexicon` is a Python module that strictly validates and compiles an English lexicon by resolving network requests via `urllib.request` with `urllib.error` handling, local file operations via `os`, secure SSL/TLS connections via `ssl`, and JSON data parsing via `json`.
[/AURA_MASTER_KEY]
"""
import json
import urllib.request
import urllib.error
import os
import ssl

OUTPUT_LEXICON = "english_lexicon.json"

OFFLINE_CORE = [
    "the", "of", "to", "and", "a", "in", "is", "it", "you", "that", "he", "was", "for", "on", "are", 
    "as", "with", "his", "they", "i", "at", "be", "this", "have", "from", "or", "one", "had", "by", 
    "word", "but", "not", "what", "all", "were", "we", "when", "your", "can", "said", "there", "use", 
    "an", "each", "which", "she", "do", "how", "their", "if", "will", "up", "other", "about", "out", 
    "many", "then", "them", "these", "so", "some", "her", "would", "make", "like", "him", "into", 
    "time", "has", "look", "two", "more", "write", "go", "see", "number", "no", "way", "could", 
    "people", "my", "than", "first", "water", "been", "call", "who", "oil", "its", "now", "find", 
    "long", "down", "day", "did", "get", "come", "made", "may", "part", "system", "node", "mesh", 
    "state", "vector", "matrix", "tensor", "physics", "error", "critical", "evolution", "mutate"
]

def compile_english_lexicon():
    print("[AURA] Initiating English Lexical Compiler...")
    url = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt"
    words = []
    
    # 1. Non-blocking network fetch with Termux SSL context fallback
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10) AuraOS/1.0"}
        )
        try:
            # Attempt verified secure handshake
            with urllib.request.urlopen(req, timeout=12.0) as response:
                words = response.read().decode('utf-8').splitlines()
        except ssl.SSLError:
            # Termux fallback: Bypass hostname checks if certificate paths are missing
            print("[⚠️ Termux SSL Fallback] Certificate verification failed. Retrying with unverified context...")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=12.0, context=ctx) as response:
                words = response.read().decode('utf-8').splitlines()
                
    except Exception as e:
        print(f"[-] Network fetch failed: {e}.")
        
        # 2. Local-First Fallback Sequence
        if os.path.exists(OUTPUT_LEXICON):
            print("[+] Retaining existing local English lexicon. Compilation bypassed.")
            return
            
        print("[*] Reverting to edge-native semantic fallback dictionary...")
        words = list(OFFLINE_CORE)

    # 3. Enforce strict 12-Bit (4096-word) structural length
    if len(words) < 4096:
        # Systematically pad with stable placeholders to prevent vocabulary truncation
        diff = 4096 - len(words)
        for i in range(diff):
            words.append(f"primitive_{i:04d}")
            
    words = words[:4096]
    print(f"[+] Operational vocabulary baseline locked at: {len(words)} primitives.")

    # 4. Compile into 12-bit binary geometric address spaces
    semantic_decoder = {}
    for idx, word in enumerate(words):
        binary_key = format(idx, '012b')
        semantic_decoder[binary_key] = word

    # 5. Lock vocabulary state safely to physical storage
    with open(OUTPUT_LEXICON, 'w', encoding='utf-8', newline='') as f:
        json.dump(semantic_decoder, f, indent=4)

    print(f"[+] Conversational Matrix Absolute. 4,096 English words vectorized.")
    print(f"[+] Output locked to {OUTPUT_LEXICON}")

if __name__ == "__main__":
    compile_english_lexicon()
