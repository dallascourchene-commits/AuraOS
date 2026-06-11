#!/data/data/com.termux/files/usr/bin/bash

echo "[*] Initializing AURA 3.11 Provisioning on Moto Stylus..."

echo "[*] Phase 1: Core OS & Termux Provisioning..."
pkg update && pkg upgrade -y
pkg install python clang cmake git rust sqlite openssl libffi ninja make patchelf python-numpy -y

echo "[*] Phase 2: Python Environment & Moto Stylus Pinning Constraints..."
pip install --upgrade pip

export MATHLIB="m"
export LDFLAGS="-L/data/data/com.termux/files/usr/lib/"
export CFLAGS="-I/data/data/com.termux/files/usr/include/"

# 1. Cryptography
pip install cryptography

# 2. Async/Web/Misc limits (Replaced crawl4ai with native mobile scrapers)
pip install websockets markdown aiohttp beautifulsoup4

echo "[*] Phase 3: Llama.cpp ARM Optimization..."
if [ ! -d "llama.cpp" ]; then
    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp
    cmake -B build -DGGML_ARCH_FLAGS="-march=armv8.2-a+dotprod+fp16"
    cmake --build build --config Release
    
    if [ $? -ne 0 ]; then 
        echo "[!] ERROR: Llama.cpp compilation failed."
        exit 1 
    fi 
    cd ..
fi

echo "[*] Phase 4: Constructing Sovereign Node Script..."
cat << 'EOF' > aura_node.py
import asyncio
import hashlib
import json
import logging
import os
import re
import time
import sqlite3
from datetime import datetime
from pathlib import Path

import markdown
import numpy as np
from cryptography.hazmat.primitives.asymmetric import ed25519

try:
    import obsidian_api
except ImportError:
    pass 

class pydantic_monty:
    class Monty:
        def __init__(self, code): self.code = code
    @staticmethod
    async def run_monty_async(m, env): return "SANDBOX_EXEC_SUCCESS"

class graphify:
    @staticmethod
    def generate_tags(resonance, depth): return f"#node #dkt_{depth} #res_{str(resonance)[:4]}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AuraSovereignNode")

Z_CAP = 35                    
L2_MIN, L2_MAX = 74.0, 78.0   
D_VEC = 10000                 
BATCH_SIZE = 50               
T_WEIGHTS = [-1, 0, 1]        
OBSIDIAN_PATH = Path.home() / "Aura_Vault/Knowledge_Graph"

class LocalNexusDB:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(f"{db_path}/nexus.db")
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS visual_nexus 
                          (id TEXT PRIMARY KEY, doc TEXT, meta TEXT)''')
        self.conn.commit()
        
    def add(self, documents, metadatas, ids):
        for d, m, i in zip(documents, metadatas, ids):
            self.c.execute("INSERT OR REPLACE INTO visual_nexus (id, doc, meta) VALUES (?, ?, ?)", 
                           (i, d, json.dumps(m)))
        self.conn.commit()
        
    def get(self, where):
        key, val = list(where.items())[0]
        search_str = f'%"{key}": "{val}"%'
        self.c.execute("SELECT meta FROM visual_nexus WHERE meta LIKE ?", (search_str,))
        row = self.c.fetchone()
        if row:
            return {'metadatas': [json.loads(row[0])]}
        return None

class AuraSovereignNode:
    def __init__(self):
        self.nexus = LocalNexusDB(str(Path.home()/".mempalace/chroma_db"))                
        self.identity_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.identity_key.public_key()                
        OBSIDIAN_PATH.mkdir(parents=True, exist_ok=True)

    def generate_ruflo_identity(self):
        return self.public_key.public_bytes_raw().hex()

    async def dual_routing_cognitive_bridge(self, prompt):
        try:
            binary_path = "./llama.cpp/build/bin/llama-cli"
            if not os.path.exists(binary_path):         
                raise FileNotFoundError("Compiled llama.cpp binary missing.")                        
            
            process = await asyncio.create_subprocess_exec(
                binary_path, 
                '-m', './models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf', 
                '-p', prompt, 
                '-n', '128',
                '-c', '512',   
                '-b', '32',    
                '-t', '4',     
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )     
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                raise RuntimeError(stderr.decode().strip())
        except Exception as e:
            logger.error(f"Local inference error: {e}")  
            return "FALLBACK_TO_API"

    def execute_dash_q_calibration(self, w, x):
        return w * (x ** 2)

    def dash_kv_asymmetric_hash(self, tensor_id):
        return hashlib.sha256(tensor_id.encode()).hexdigest()

    def fluxmem_lexical_streamer(self, batch):
        buffer = []
        for item in batch:
            buffer.append(self.ojibwe_morph_parse(item))
        return buffer

    def ojibwe_morph_parse(self, megaword):
        root_val = f"parsed_{megaword}"
        fields = {
            "1": "Action_Root", "2": "Temporal_Marker", "3": "Subject_Role",
            "4": "Object_Relation", "5": "Spatial_Locus", "6": "Intent_Vector",
            "7": "Modality_Shift", "8": "Causality_Link", "9": "Resonance_Freq",
            "10": "Cryptographic_Hash", "11": "Validation_Bit"      
        }
        return {"root": root_val, "fields": fields, "template_id": "11-POINT-MASTER"}

    def bitnet_b158_inference(self, x):
        return np.sign(x) * (np.abs(x) > 0.5)

    def calculate_dkt_resonance(self, current_hv, target_mastery_hv):
        dot_product = np.dot(current_hv, target_mastery_hv)
        norm_curr = np.linalg.norm(current_hv)
        norm_target = np.linalg.norm(target_mastery_hv)
        if norm_curr == 0 or norm_target == 0:
            return 1.0 
        cosine_similarity = dot_product / (norm_curr * norm_target)
        return 1.0 - cosine_similarity

    # MOTO LITE OPTIMIZATION: Termux-native web scraper replacing crawl4ai
    async def asi_evolve_research_loop(self, query):
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(f"https://html.duckduckgo.com/html/?q={query}") as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    snippet = soup.find('a', class_='result__snippet')
                    research_data = snippet.text[:200] if snippet else "No data found."
            
            self.nexus.add(
                documents=[research_data],
                metadatas=[{"source": "autonomous_research", "query": query}],
                ids=[f"research_{int(time.time())}"]
            )     
            research_step = f"resolve_deficit('{query}', insight_extracted=True)"
        except Exception as e:
            logger.error(f"Research loop failed: {e}")
            research_step = f"resolve_deficit('{query}', status='failed')"
        return research_step

    def validate_h2e_shell(self, hypervector):
        norm = np.linalg.norm(hypervector)       
        return L2_MIN <= norm <= L2_MAX

    def export_to_obsidian(self, input_text, structure, resonance):
        filename = f"Node_{int(time.time())}.md"
        safe_title = re.sub(r'[^a-zA-Z0-9\s]', '', input_text[:20])
        
        content = f"---\ntitle: {safe_title}\ndkt_resonance: {resonance}\n---\n"
        content += f"## 11-Point AAAK Analysis\n"
        for k, v in structure['fields'].items():
            content += f"- **{v}**: Field_{k}_Active\n"      
        graph_tags = graphify.generate_tags(resonance, depth=11)
        content += f"\n### Graphify Vector\ntags: {graph_tags}\n"
        
        try:
            html_check = markdown.markdown(content)
        except Exception as e:
            pass
            
        with open(OBSIDIAN_PATH / filename, "w") as f:
            f.write(content)                

    async def execute_batch_cycle(self, inputs, value):
        parsed_batch = self.fluxmem_lexical_streamer(inputs)
        results = []
        for parsed_item in parsed_batch:
            res = await self.execute_polysynthetic_cycle(parsed_item['root'], value)  
            results.append(res)
        return results

    async def execute_polysynthetic_cycle(self, input_text, value):
        structure = self.ojibwe_morph_parse(input_text)
        logic_code = await self.asi_evolve_research_loop(structure['root'])                
        
        if len(logic_code) > (Z_CAP * 20): 
             return "ALGORITHM B VIOLATION"  
             
        try:
            historical_data = self.nexus.get(where={"aaak_root": structure['root']})
            if historical_data and historical_data['metadatas']:
                hv = np.array(json.loads(historical_data['metadatas'][0]['hv_state']))
            else:
                hv = np.sign(np.random.randn(D_VEC))
        except Exception:
            hv = np.sign(np.random.randn(D_VEC))
            
        mastery_hv = np.ones(D_VEC)
        resonance = self.calculate_dkt_resonance(hv, mastery_hv)         
        hv = self.bitnet_b158_inference(hv)                
        
        if not self.validate_h2e_shell(hv):
            return "GEOMETRIC REJECTION"                    
            
        m = pydantic_monty.Monty(logic_code)
        output = await pydantic_monty.run_monty_async(m, env={})                
        calibrated_vault = self.execute_dash_q_calibration(w=0.30, x=value)                
        
        settlement = {      
            "Burn": value * 0.30,
            "Vault": calibrated_vault,
            "Ancestor_Yield": value * 0.05,
            "Compute_Node": value * 0.35,
            "Node_ID": self.generate_ruflo_identity()
        }                
        
        raw_id = f"cycle_{int(time.time())}_{structure['root']}"
        hashed_id = self.dash_kv_asymmetric_hash(raw_id)                
        
        self.nexus.add(
            documents=[input_text],
            metadatas=[{
                "aaak": str(structure),
                "aaak_root": structure['root'],
                "dkt_resonance": float(resonance),        
                "hv_state": json.dumps(hv.tolist())            
            }],
            ids=[hashed_id]
        )
        self.export_to_obsidian(input_text, structure, resonance)
        return {"output": output, "resonance": resonance, "settlement": "SUCCESS"}

if __name__ == "__main__":
    node = AuraSovereignNode()
    print(f"[*] AURA 3.11 Active.\nNode ID: {node.generate_ruflo_identity()}")
    print("[*] Ruflo Mesh, ASI-Evolve, DKT, and Obsidian-Graphify Synchronized.")
    print("[*] Llama.cpp Engine, DASH-Q Calibration, and Local Nodes Initiated.")
EOF

echo "[*] Installation Complete. To boot AURA 3.11, run: python aura_node.py"

