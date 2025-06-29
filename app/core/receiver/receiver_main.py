import socket
import json
from app.core.summarizer.summarizer import Summarizer
from app.core.summarizer.topk_precomputer import TopKPrecomputer

def start_region_receiver(region: str, host="localhost", port=9001):
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