import hashlib
import time
import json
import random
import socket
import os
import matplotlib.pyplot as plt
from flask import Flask, jsonify, request, render_template
import websockets
import asyncio

app = Flask(__name__, template_folder='templates')
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
        block_data = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "nonce": self.nonce,
            "difficulty": self.difficulty
        }, sort_keys=True)
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
        self.mining_reward = 50  # Dharma Lovers (DLS Coin) recompensa inicial
        self.tokens = {}
        self.contracts = {}
        self.halving_interval = 210000
        self.block_time_target = 10
        self.last_block_time = time.time()

    def create_genesis_block(self):
        return Block(0, "0", int(time.time()), [], self.difficulty)

    def adjust_difficulty(self):
        if len(self.chain) % 10 == 0:
            current_time = time.time()
            time_taken = current_time - self.last_block_time
            self.last_block_time = current_time
            
            if time_taken < self.block_time_target:
                self.difficulty += 1
            elif time_taken > self.block_time_target:
                self.difficulty = max(1, self.difficulty - 1)

    def apply_halving(self):
        if len(self.chain) % self.halving_interval == 0:
            self.mining_reward = max(1, self.mining_reward // 2)

    def add_block(self, miner_address):
        previous_block = self.chain[-1]
        self.pending_transactions.append({"from": "network", "to": miner_address, "amount": self.mining_reward})
        new_block = Block(len(self.chain), previous_block.hash, int(time.time()), self.pending_transactions, self.difficulty)
        if new_block.hash is not None:
            self.chain.append(new_block)
            self.pending_transactions = []
            self.adjust_difficulty()
            self.apply_halving()
            asyncio.create_task(self.broadcast_block(new_block))
        return new_block

    async def broadcast_block(self, block):
        for node in nodes:
            try:
                async with websockets.connect(node) as ws:
                    await ws.send(json.dumps(block.__dict__))
            except Exception as e:
                print(f"Erro ao conectar com {node}: {e}")

blockchain = Blockchain()

@app.route('/')
def index():
    return render_template('index.html', blocks=blockchain.chain)

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    new_nodes = request.json.get("nodes")
    if not new_nodes:
        return jsonify({"message": "Nenhum nó fornecido"}), 400
    for node in new_nodes:
        nodes.add(node)
    return jsonify({"message": "Nós registrados com sucesso", "total_nodes": list(nodes)})

@app.route('/blocks', methods=['GET'])
def get_blocks():
    return jsonify([block.__dict__ for block in blockchain.chain])

@app.route('/mine', methods=['POST'])
def mine_block():
    miner_address = request.json.get('miner_address', 'Miner1')
    block = blockchain.add_block(miner_address)
    return jsonify({"message": "Bloco minerado!", "block": block.__dict__})

@app.route('/transactions', methods=['POST'])
def create_transaction():
    data = request.json
    blockchain.pending_transactions.append(data)
    return jsonify({"message": "Transação adicionada!", "transaction": data})

@app.route('/pending_transactions', methods=['GET'])
def get_pending_transactions():
    return jsonify(blockchain.pending_transactions)

if __name__ == '__main__':
    try:
        app.run(host="0.0.0.0", port=5000)
    except SystemExit:
        print("Erro ao iniciar o servidor Flask. Verifique o ambiente e tente novamente.")
