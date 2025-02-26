import hashlib
import time
import json
import os
import threading
import logging
from flask import Flask, jsonify, request, render_template
import asyncio
import websockets

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Criar as pastas templates e static se não existirem
templates_dir = "templates"
static_dir = "static/js"
os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

# Criar index.html se não existir
index_html_path = os.path.join(templates_dir, "index.html")
if not os.path.exists(index_html_path):
    with open(index_html_path, "w") as f:
        f.write("""<!DOCTYPE html>
<html lang=\"pt\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>DLS Coin - Blockchain</title>
    <script src=\"/static/js/index.js\"></script>
</head>
<body>
    <h1>Bem-vindo à DLS Coin</h1>
    <p>Blocos minerados:</p>
    <ul>
        {% for block in blocks %}
            <li>Bloco {{ block.index }} - Hash: {{ block.hash }}</li>
        {% endfor %}
    </ul>
    <h2>Baixe a carteira:</h2>
    <a href='/download/win'>Baixar para Windows</a> | <a href='/download/linux'>Baixar para Linux</a>
    <h2>Explorer da Blockchain:</h2>
    <a href='/explorer'>Acessar Explorer</a>
</body>
</html>""")

# Criar explorer.html
explorer_html_path = os.path.join(templates_dir, "explorer.html")
if not os.path.exists(explorer_html_path):
    with open(explorer_html_path, "w") as f:
        f.write("""<!DOCTYPE html>
<html lang=\"pt\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Explorer DLS Coin</title>
</head>
<body>
    <h1>Explorer da Blockchain DLS Coin</h1>
    <ul>
        {% for block in blocks %}
            <li>Bloco {{ block.index }} - Hash: {{ block.hash }}</li>
        {% endfor %}
    </ul>
</body>
</html>""")

# Criar arquivos JavaScript se não existirem
js_files = ["index.js", "Wallet.js", "asyncToGenerator.js", "index.umd.js"]
for js_file in js_files:
    js_path = os.path.join(static_dir, js_file)
    if not os.path.exists(js_path):
        with open(js_path, "w") as f:
            f.write(f"console.log('Carregando {js_file}');")

app = Flask(__name__, template_folder='templates', static_folder='static')
nodes = set()

class Block:
    def __init__(self, index, previous_hash, timestamp, transactions, difficulty):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.nonce = 0
        self.difficulty = difficulty
        self.hash = self.mine_block()

    def compute_hash(self):
        block_data = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(block_data.encode()).hexdigest()

    def mine_block(self):
        while True:
            self.hash = self.compute_hash()
            if self.hash.startswith('0' * self.difficulty):
                return self.hash
            self.nonce += 1

class Blockchain:
    def __init__(self):
        self.difficulty = 4
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []
        self.mining_reward = 50
        self.halving_interval = 210000
        self.block_time_target = 10
        self.last_block_time = time.time()

    def create_genesis_block(self):
        return Block(0, "0", int(time.time()), [], self.difficulty)

    def adjust_difficulty(self):
        if len(self.chain) % 10 == 0:
            time_taken = time.time() - self.last_block_time
            self.last_block_time = time.time()
            self.difficulty = max(1, self.difficulty + 1 if time_taken < self.block_time_target else self.difficulty - 1)

    def apply_halving(self):
        if len(self.chain) % self.halving_interval == 0:
            self.mining_reward = max(1, self.mining_reward // 2)

    def add_block(self, miner_address):
        previous_block = self.chain[-1]
        self.pending_transactions.append({"from": "network", "to": miner_address, "amount": self.mining_reward})
        new_block = Block(len(self.chain), previous_block.hash, int(time.time()), self.pending_transactions, self.difficulty)
        if new_block.hash:
            self.chain.append(new_block)
            self.pending_transactions = []
            self.adjust_difficulty()
            self.apply_halving()
            threading.Thread(target=lambda: asyncio.run(self.broadcast_block(new_block))).start()
        return new_block

    async def broadcast_block(self, block):
        for node in nodes:
            try:
                async with websockets.connect(f"{node}/ws") as ws:
                    await ws.send(json.dumps(block.__dict__))
            except Exception as e:
                logging.error(f"Erro ao conectar com {node}: {e}")

blockchain = Blockchain()

@app.route('/')
def index():
    return render_template('index.html', blocks=blockchain.chain)

@app.route('/explorer')
def explorer():
    return render_template('explorer.html', blocks=blockchain.chain)

@app.route('/blocks', methods=['GET'])
def get_blocks():
    return jsonify([block.__dict__ for block in blockchain.chain])

@app.route('/mine', methods=['POST'])
def mine_block():
    miner_address = request.json.get('miner_address', 'Miner1')
    block = blockchain.add_block(miner_address)
    return jsonify({"message": "Bloco minerado!", "block": block.__dict__})

if __name__ == '__main__':
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        logging.error(f"Erro ao iniciar o servidor Flask: {e}")
