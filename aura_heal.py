"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy)
DEPENDENCIES: sqlite3, websockets, math, ssl, urllib.parse, subprocess, bs4, urllib.error, asyncio, pvm_memory_guard, shutil, PyPDF2, hashlib, symbolic_shield, os, time, io, ast, re, aura_api_rotator, urllib.request, json
FUNCTIONS: compute_rubric_reward, load_api_keys, map_neural_architecture, speak, update_ar_state, commit_to_dkt, call_llm, agentic_optimization, forage_knowledge_from_links, heal_system
SYNOPSIS: This Python module integrates cryptographic, networking, and AI-driven processing capabilities—leveraging SQLite for data persistence, WebSockets for real-time communication, and libraries like `PyPDF2`, `bs4`, and `urllib` for document parsing and web interactions—while enforcing memory safety via `pvm_memory_guard` and `symbolic_shield`, executing system commands securely with `subprocess`, and interfacing with external APIs through `aura_api_rotator`, all orchestrated asynchronously via `asyncio` to deliver functions such as `compute_rubric_reward`, `agentic_optimization`, and `heal_system` for dynamic knowledge acquisition, state management, and system recovery.
[/AURA_MASTER_KEY]
"""
import os
import asyncio
import websockets
import json
import shutil
import subprocess
import hashlib
import time
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
import io
import ast
import re
import ssl

import math

from symbolic_shield import verify_structural_truth
from pvm_memory_guard import sample_rss_mb
from aura_api_rotator import gemini_generate, gemini_key_pool, load_secrets

# ---------------------------------------------------------------------------
# Rubric Reward Matrix  (arXiv:2605.31584 — LongTraceRL process supervision)
# ---------------------------------------------------------------------------
# R_rubric(τ) = I(Y=1) · [ w_ram·F_RAM + w_thermal·F_thermal + w_sat·F_SAT ]
# Only patches with R_rubric ≥ 0.85 are allowed to reach the filesystem.

_PVM_RAM_CEILING_MB: float = 4096.0
_RUBRIC_FLOOR: float = 0.85


def compute_rubric_reward(
    proposed_code: str,
    current_temp_c: float = 42.0,
    w_ram: float = 0.40,
    w_thermal: float = 0.30,
    w_sat: float = 0.30,
) -> tuple[float, dict]:
    """
    Multi-tiered Rubric Reward Matrix.

    Returns
    -------
    (score ∈ [0,1], breakdown dict)

    Sub-fitness components
    ----------------------
    F_RAM      = max(0, 1 − RSS_MB / 4096)       — memory headroom
    F_thermal  = exp(−ω · ΔT)  where ΔT = max(0, T−40)°C, ω=0.15
    F_SAT      = 1 if AST parse + symbolic shield pass, else 0
    """
    # I(Y=1) — hard gate 1: non-trivial code (empty patches are rejected)
    if not proposed_code.strip():
        return 0.0, {"F_RAM": 0, "F_thermal": 0, "F_SAT": 0, "reason": "EMPTY_PATCH"}

    # I(Y=1) — hard gate 2: must parse cleanly
    try:
        ast.parse(proposed_code)
        syntax_ok = True
    except SyntaxError:
        return 0.0, {"F_RAM": 0, "F_thermal": 0, "F_SAT": 0, "reason": "SYNTAX_FAIL"}

    # F_SAT — symbolic shield (5 AST gates)
    f_sat = 1.0 if verify_structural_truth(proposed_code) else 0.0

    # F_RAM — current process RSS vs 4 GB ceiling
    rss = sample_rss_mb()
    f_ram = max(0.0, 1.0 - rss / _PVM_RAM_CEILING_MB)

    # F_thermal — Maxwell-damping thermal penalty
    delta_t = max(0.0, current_temp_c - 40.0)
    omega = 0.15
    f_thermal = math.exp(-omega * delta_t)

    score = w_ram * f_ram + w_thermal * f_thermal + w_sat * f_sat
    breakdown = {
        "F_RAM": round(f_ram, 4),
        "F_thermal": round(f_thermal, 4),
        "F_SAT": f_sat,
        "R_rubric": round(score, 4),
        "passed": score >= _RUBRIC_FLOOR,
    }
    return score, breakdown

try:
    from bs4 import BeautifulSoup
except (ImportError, RuntimeError, OSError):
    BeautifulSoup = None

try:
    import PyPDF2
except (ImportError, RuntimeError, OSError):
    PyPDF2 = None

# --- SYSTEM DIRECTORIES ---
ROOT_DIR = "."
INGEST_DIR = "Knowledge_Ingest"
STAGING_DIR = "Aura_Staging"
MEMORY_DIR = "Aura_Memory"
DB_PATH = os.path.expanduser("~/.mempalace/aura_memory.db")

for d in [INGEST_DIR, STAGING_DIR, MEMORY_DIR]:
    os.makedirs(d, exist_ok=True)

# --- API WATERFALL MESH (UPGRADED) ---
API_PROVIDERS = [
    {
        "name": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_var": "GEMINI_KEY",
        "model": "gemini-1.5-flash", 
        "schema": "openai"
    },
    {
        "name": "Cerebras",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key_var": "CEREBRAS_KEY", 
        "model": "llama3.1-70b", 
        "schema": "openai"
    },
    {
        "name": "SambaNova",
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "key_var": "SAMBANOVA_KEY",
        "model": "Meta-Llama-3.1-70B-Instruct", 
        "schema": "openai"
    },
    {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_var": "OPENROUTER_KEY",
        "model": "meta-llama/llama-3-8b-instruct:free", 
        "schema": "openai"
    },
    {
        "name": "Mistral",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "key_var": "MISTRAL_KEY",
        "model": "mistral-small-latest", 
        "schema": "openai"
    },
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_var": "GROQ_KEY",
        "model": "mixtral-8x7b-32768", 
        "schema": "openai"
    }
]

def load_api_keys() -> dict:
    """Loads API keys from environment variables and falls back to aura_secrets.json."""
    keys = {
        "GEMINI_KEY": os.getenv("GEMINI_KEY"),
        "CEREBRAS_KEY": os.getenv("CEREBRAS_KEY"),
        "SAMBANOVA_KEY": os.getenv("SAMBANOVA_KEY"),
        "OPENROUTER_KEY": os.getenv("OPENROUTER_KEY"),
        "MISTRAL_KEY": os.getenv("MISTRAL_KEY"),
        "GROQ_KEY": os.getenv("GROQ_KEY"),
    }
    sec = load_secrets()
    if sec:
        if not keys["GEMINI_KEY"]:
            pool = gemini_key_pool(sec)
            keys["GEMINI_KEY"] = pool[0] if pool else sec.get("GEMINI_API_KEY")
        if not keys["MISTRAL_KEY"]:
            keys["MISTRAL_KEY"] = sec.get("MISTRAL_API_KEY")
        if not keys["GROQ_KEY"]:
            keys["GROQ_KEY"] = sec.get("GROQ_API_KEY")
        if not keys["OPENROUTER_KEY"]:
            keys["OPENROUTER_KEY"] = sec.get("GITHUB_TOKEN")
    return keys

def map_neural_architecture(filepath, original_code):
    """Maps massive code into a lightweight 3D-ready AST skeleton with decorator and argument awareness."""
    try:
        tree = ast.parse(original_code)
    except SyntaxError:
        return json.dumps({"error": "Syntax invalid"})

    architecture_map = {
        "entity_type": "HyperGraph",
        "file_target": filepath,
        "nodes": []
    }
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            decorators = [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
            class_node = {
                "id": f"Class::{node.name}",
                "type": "CentralCluster",
                "decorators": decorators,
                "orbiting_methods": []
            }
            for sub_node in node.body:
                if isinstance(sub_node, ast.FunctionDef):
                    method_decs = [d.id for d in sub_node.decorator_list if isinstance(d, ast.Name)]
                    class_node["orbiting_methods"].append({
                        "name": sub_node.name,
                        "decorators": method_decs,
                        "args": [arg.arg for arg in sub_node.args.args],
                        "lines": f"{sub_node.lineno}-{sub_node.end_lineno}"
                    })
            architecture_map["nodes"].append(class_node)
            
        elif isinstance(node, ast.FunctionDef):
            decorators = [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
            architecture_map["nodes"].append({
                "id": f"Function::{node.name}",
                "type": "StandaloneNode",
                "decorators": decorators,
                "args": [arg.arg for arg in node.args.args],
                "lines": f"{node.lineno}-{node.end_lineno}"
            })
            
    return json.dumps(architecture_map, indent=2)

# --- HARDWARE & AR BRIDGES ---
def speak(text):
    print(f"[AURA VOICE]: {text}")
    try:
        subprocess.Popen(['termux-tts-speak', text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

async def update_ar_state(shape, lum, temp):
    try:
        async with websockets.connect("ws://127.0.0.1:8081") as ws:
            await ws.send(json.dumps({"shape": shape, "lum": lum, "temp": temp}))
            await asyncio.sleep(0.5)
    except Exception:
        pass 

# --- COGNITIVE MEMORY ---
def commit_to_dkt(filename, improvement_logic):
    timestamp = str(time.time())
    thought_payload = f"{filename}|{improvement_logic}|{timestamp}"
    thought_id = "DKT-" + hashlib.sha256(thought_payload.encode('utf-8')).hexdigest()[:16]

    speak(f"Minting quantum engram. Thought ID: {thought_id[:8]}")

    try:
        # Standardized: Unify database writes inside core memory palace with WAL mode
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS cognitive_evolution
                     (thought_id TEXT, timestamp TEXT, target_file TEXT, logic TEXT)''')
        c.execute("INSERT INTO cognitive_evolution VALUES (?, ?, ?, ?)", 
                  (thought_id, timestamp, filename, improvement_logic))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] DB Error: {e}")

    st3_path = os.path.join(MEMORY_DIR, f"{thought_id}.st3")
    gge_path = os.path.join(MEMORY_DIR, f"{thought_id}.gge")
    
    with open(st3_path, 'w', encoding='utf-8', newline='') as f:
        f.write(f"STATE-SPACE TENSOR MAP\nTHOUGHT: {thought_id}\nFILE: {filename}\nSTATUS: +MUTATE OPTIMAL")
        
    with open(gge_path, 'w', encoding='utf-8', newline='') as f:
        f.write(f"GRAPH-GRAMMAR ENCODING\nNODE: Edge_MotoG\nLOGIC_SHIFT:\n{improvement_logic}")

# --- CLOUD LOGIC EXPERT ---
def call_llm(prompt):
    api_keys = load_api_keys()
    secrets = load_secrets()

    if gemini_key_pool(secrets):
        print("[*] Routing thought to Gemini (rotating key pool)...")
        text, err = gemini_generate(prompt, secrets=secrets)
        if text:
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:-1])
            return text.strip()
        if err:
            print(f"[!] Gemini rotation exhausted: {err[:200]}")

    for provider in API_PROVIDERS:
        key_var = provider["key_var"]
        key_val = api_keys.get(key_var)
        if not key_val or key_val.startswith("YOUR_") or "your_actual_" in key_val.lower():
            continue
            
        try:
            print(f"[*] Routing thought to {provider['name']}...")
            headers = {
                "Content-Type": "application/json", 
                "Authorization": f"Bearer {key_val}"
            }
            payload = {
                "model": provider["model"], 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.1
            }
            
            req_data = json.dumps(payload).encode('utf-8')
            req_obj = urllib.request.Request(
                provider["url"],
                data=req_data,
                headers=headers,
                method="POST"
            )
            
            # Handle Termux SSL Handshake Fallback context gracefully
            try:
                with urllib.request.urlopen(req_obj, timeout=30) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
            except ssl.SSLError:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(req_obj, timeout=30, context=ctx) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
            
            content = res_data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"): 
                content = "\n".join(content.split("\n")[1:-1])
                
            return content
            
        except Exception as e:
            print(f"[!] {provider['name']} failed/timeout: {e}. Cascading to next layer...")
            
    return None

# --- RECURSIVE SUB-AGENT WORKFLOW ---
async def agentic_optimization(filename, original_code, external_knowledge):
    speak(f"Stage 1. Architect mapping Liquid logic against {filename}.")
    await update_ar_state("PhysicsTetrahedron", "HI", "HOT")
    
    # 1. Generate the 3D Graph Skeleton
    vector_map = map_neural_architecture(filename, original_code)
    
    # Save the 3D map to Memory so pulse.py and Chrome AR can render it!
    ast_filepath = os.path.join(MEMORY_DIR, f"{filename.replace('.py', '')}_ast.json")
    with open(ast_filepath, "w", encoding='utf-8', newline='') as f:
        f.write(vector_map)

    safe_knowledge = external_knowledge[:80000] 

    # 2. DEFINE the Architect's prompt FIRST
    plan_prompt = f"""
    You are an Edge AI Architect manipulating a 3D structural graph of a Python system.
    Read this episodic external knowledge: {safe_knowledge}
    
    Instead of flat code, here is the Abstract Syntax Tree (AST) node map of the target:
    {vector_map}
    
    Identify EXACTLY which Node/Function needs to be mutated to integrate the new knowledge. 
    Provide a step-by-step plan. State the exact class and function name to target. DO NOT write full code.
    """

    # 3. GENERATE the plan SECOND
    plan = call_llm(plan_prompt)
    if not plan:
        print("[!] Architect failed. Aborting sequence.")
        return

    with open(f"{STAGING_DIR}/AURA_UPGRADE_PLAN.md", "w", encoding='utf-8', newline='') as f:
        f.write(plan)

    # LET THE API BREATHE TO PREVENT 429 RATE LIMITS
    print("[*] Cooling down API connections (5s)...")
    time.sleep(5)

    speak("Stage 2. Weaver transcribing architecture plan to logic gates.")
    await update_ar_state("PhysicsIcosahedron", "HI", "HOT")

    # 2. The Weaver Sub-Agent (Only sees the compressed plan, not the massive PDFs)
    code_prompt = f"""
    You are a precise Python coder. Follow this plan to rewrite the target code.
    CRITICAL HARDWARE LIMIT: You are deploying to a Motorola Moto G Stylus via Termux.
    DO NOT use `nxsdk`, `loihi`, or any proprietary hardware libraries. 
    Use ONLY standard Python libraries, `numpy`, or `torch`. 
    If the plan asks for spiking libraries, simulate them mathematically using standard Python.
    PLAN: {plan}
    ORIGINAL CODE: {original_code}
    Return ONLY the raw, refactored Python code. No markdown tags. No explanations.
    """

    new_code = call_llm(code_prompt)
    if not new_code: return False

    # --- RUBRIC REWARD GATE (arXiv:2605.31584) + YOUVAN SOUND SHIELD ---
    # Read current device temperature for F_thermal component
    _temp = 42.0
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as _tf:
            _temp = float(_tf.read().strip()) / 1000.0
    except (IOError, FileNotFoundError):
        pass

    rubric_score, rubric_breakdown = compute_rubric_reward(new_code, current_temp_c=_temp)
    if rubric_score < _RUBRIC_FLOOR:
        speak(
            f"Rubric Reward {rubric_score:.3f} < {_RUBRIC_FLOOR} threshold. "
            f"Rejecting patch. Breakdown: {rubric_breakdown}"
        )
        return False
    print(f"[✓] Rubric Reward: {rubric_score:.3f}  {rubric_breakdown}")

    staging_file = os.path.join(STAGING_DIR, f"test_{filename}")
    with open(staging_file, "w", encoding='utf-8', newline='') as f:
        f.write(new_code)

    speak("Stage 3. Sandbox test initiated.")
    try:
        subprocess.run(['python3', '-m', 'py_compile', staging_file], check=True, capture_output=True)
        shutil.copy(filename, f"{filename}.bak")
        shutil.move(staging_file, filename)
        
        commit_to_dkt(filename, plan[:100] + "...") 
        
        speak("Integration successful. Architecture optimal.")
        await update_ar_state("PhysicsSphere", "HI", "COLD") 
        return True

    except subprocess.CalledProcessError:
        speak("Hallucination detected. Syntax invalid. Purging staging file.")
        if os.path.exists(staging_file):
            os.remove(staging_file)
        await update_ar_state("PhysicsTetrahedron", "HI", "HOT")
        return False

# --- EPISODIC KNOWLEDGE FORAGER ---
def forage_knowledge_from_links(link_file_path):
    speak("Foraging external knowledge from URLs.")
    extracted_knowledge = "--- KNOWLEDGE L1 CACHE ---\n"
    
    if not os.path.exists(link_file_path):
        return extracted_knowledge
        
    with open(link_file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and line.startswith("http")]

    for url in urls:
        print(f"[>] Foraging: {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AuraOS/1.0'}
            req_obj = urllib.request.Request(url, headers=headers)
            
            # Non-blocking read with adaptive Termux SSL context fallback
            try:
                with urllib.request.urlopen(req_obj, timeout=15) as response_obj:
                    content_bytes = response_obj.read()
                    content_type = response_obj.headers.get('content-type', '')
            except ssl.SSLError:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(req_obj, timeout=15, context=ctx) as response_obj:
                    content_bytes = response_obj.read()
                    content_type = response_obj.headers.get('content-type', '')

            extracted_knowledge += f"\n\n=== EPISODE SOURCE: {url} ===\n"

            # Parse dynamically with guarded fallbacks
            if ("pdf" in url.lower() or "application/pdf" in content_type) and PyPDF2 is not None:
                pdf_file = io.BytesIO(content_bytes)
                reader = PyPDF2.PdfReader(pdf_file)
                pages_to_read = min(15, len(reader.pages))
                for i in range(pages_to_read):
                    extracted_knowledge += reader.pages[i].extract_text() + "\n"
                print(f"  [+] PDF indexed.")
            elif BeautifulSoup is not None:
                soup = BeautifulSoup(content_bytes.decode('utf-8', errors='ignore'), 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                extracted_knowledge += text[:5000] + "\n"
                print(f"  [+] Web text indexed.")
            else:
                # Raw regex HTML tag-stripper acts as a zero-dependency fallback
                raw_text = content_bytes.decode('utf-8', errors='ignore')
                clean_text = re.sub(r'<[^>]+>', ' ', raw_text)
                extracted_knowledge += " ".join(clean_text.split())[:5000] + "\n"
                print(f"  [+] Plain text extracted (Parsers offline).")
                
        except Exception as e:
            print(f"  [!] Failed to forage {url}: {e}")

    return extracted_knowledge

async def heal_system():
    speak("Autoimmune sequence initiated. Scanning knowledge ingest sector.")
    
    external_knowledge = ""
    for k_file in os.listdir(INGEST_DIR):
        filepath = os.path.join(INGEST_DIR, k_file)
        
        if k_file == "links.txt":
            external_knowledge += forage_knowledge_from_links(filepath)
        elif k_file.endswith(('.txt', '.md')) and k_file != "links.txt":
            with open(filepath, 'r', encoding='utf-8') as f:
                external_knowledge += f"\n=== EPISODE SOURCE: LOCAL FILE ({k_file}) ===\n"
                external_knowledge += f.read() + "\n"

    files_to_heal = [f for f in os.listdir(ROOT_DIR) if f.endswith('.py') and f not in ["aura_heal.py", "pulse.py"]]
    
    for file in files_to_heal:
        with open(file, 'r', encoding='utf-8') as f:
            original_code = f.read()
        await agentic_optimization(file, original_code, external_knowledge)

    speak("Sequence complete. Neural geometry resting.")
    await update_ar_state("PhysicsSphere", "MID", "NEUT")

if __name__ == "__main__":
    asyncio.run(heal_system())
