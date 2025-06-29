import socket
import json
from pathlib import Path
from app.core.summarizer.summarizer import Summarizer
from app.core.summarizer.topk_precomputer import TopKPrecomputer

PORT_CONFIG_FILE = Path("app/config/ports.json")

def load_port(region: str) -> int:
    if not PORT_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Port config file not found at {PORT_CONFIG_FILE}")
    with open(PORT_CONFIG_FILE, "r") as f:
        port_config = json.load(f)
    if region not in port_config:
        raise ValueError(f"No port configured for region '{region}'")
    return port_config[region]

def start_region_receiver(region: str, host="localhost"):
    port = load_port(region)
    summarizer = Summarizer(region=region)
    topk = TopKPrecomputer()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((host, port))
        server.listen()
        print(f"[RECEIVER {region.upper()}] Listening on {host}:{port}...")
        while True:
            conn, addr = server.accept()
            with conn:
                data = conn.recv(4096)
                if not data:
                    continue
                try:
                    msg = json.loads(data.decode())
                    if msg.get("region") != region:
                        continue

                    print(f"[RECEIVER {region.upper()}] Received file: {msg['file']}")
                    summarizer.update()
                    topk.precompute_top_k(regions=[region])

                except Exception as e:
                    print(f"[RECEIVER {region.upper()}] Error: {e}")