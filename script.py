import os
import time
import json
import logging
import random
from typing import List, Dict, Any, Optional

import requests
from web3 import Web3
from web3.types import LogReceipt
from eth_abi import decode as abi_decode

# --- Configuration ---
# Configure logging to provide detailed output.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Constants and Mock Data ---
# In a real-world scenario, these would be managed securely.
SOURCE_CHAIN_RPC = os.getenv('SOURCE_CHAIN_RPC', 'https://mock.source.chain.rpc')
DEST_CHAIN_RPC = os.getenv('DEST_CHAIN_RPC', 'https://mock.dest.chain.rpc')
BRIDGE_CONTRACT_ADDRESS = Web3.to_checksum_address('0x1234567890123456789012345678901234567890')
STATE_FILE = 'state.json'
POLLING_INTERVAL_SECONDS = 10
BLOCK_PROCESSING_BATCH_SIZE = 100 # Process up to 100 blocks at a time
CONFIRMATIONS_REQUIRED = 6 # Number of blocks to wait before considering an event final

# Mock ABI for a simple bridge contract event.
# This simulates the event signature for: event TokensLocked(address indexed user, address indexed token, uint256 amount, uint256 destinationChainId);
BRIDGE_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "user", "type": "address"},
            {"indexed": True, "name": "token", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": False, "name": "destinationChainId", "type": "uint256"}
        ],
        "name": "TokensLocked",
        "type": "event"
    }
]
EVENT_SIGNATURE_HASH = Web3.keccak(text="TokensLocked(address,address,uint256,uint256)").hex()

class StateDB:
    """Manages the persistent state of the listener, such as the last processed block."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads the state from a JSON file, creating it if it doesn't exist."""
        try:
            with open(self.filepath, 'r') as f:
                logging.info(f"Loading state from {self.filepath}")
                return json.load(f)
        except FileNotFoundError:
            logging.warning(f"State file not found. Initializing with default state.")
            return {"last_processed_block": 0, "processed_event_hashes": []}
        except json.JSONDecodeError:
            logging.error(f"Error decoding state file. Starting with fresh state.")
            return {"last_processed_block": 0, "processed_event_hashes": []}

    def save_state(self):
        """Saves the current state to the JSON file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.state, f, indent=4)
                logging.debug(f"State successfully saved to {self.filepath}")
        except IOError as e:
            logging.error(f"Failed to save state to {self.filepath}: {e}")

    def get_last_processed_block(self) -> int:
        """Returns the last block number that was successfully processed."""
        return self.state.get("last_processed_block", 0)

    def set_last_processed_block(self, block_number: int):
        """Updates the last processed block number in the state."""
        self.state["last_processed_block"] = block_number

    def is_event_processed(self, event_hash: str) -> bool:
        """Checks if a specific event has already been processed to prevent duplicates."""
        # This is a simple implementation; a real system might use a more scalable DB.
        return event_hash in self.state.get("processed_event_hashes", [])

    def mark_event_as_processed(self, event_hash: str):
        """Marks an event as processed."""
        if "processed_event_hashes" not in self.state:
            self.state["processed_event_hashes"] = []
        self.state["processed_event_hashes"].append(event_hash)
        # Prune old events to keep state file size manageable
        max_events = 10000
        if len(self.state["processed_event_hashes"]) > max_events:
            self.state["processed_event_hashes"] = self.state["processed_event_hashes"][-max_events:]


class MockBlockchainConnector:
    """A mock connector to simulate interactions with a blockchain RPC endpoint."""
    def __init__(self, rpc_url: str, chain_name: str):
        self.rpc_url = rpc_url
        self.chain_name = chain_name
        self.w3 = Web3() # Using Web3 for its utilities, without a real provider
        self.current_block = random.randint(10000, 20000)
        self.is_connected = False
        logging.info(f"[{self.chain_name}] MockConnector initialized for {self.rpc_url}")

    def connect(self):
        """Simulates connecting to the RPC endpoint."""
        try:
            # In a real scenario, this might ping the endpoint.
            # We simulate a potential connection failure.
            if 'fail' in self.rpc_url:
                raise requests.exceptions.ConnectionError("Mock connection failed")
            self.is_connected = True
            logging.info(f"[{self.chain_name}] Successfully connected to mock RPC endpoint.")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"[{self.chain_name}] Failed to connect to {self.rpc_url}: {e}")
            self.is_connected = False

    def get_latest_block(self) -> int:
        """Simulates fetching the latest block number and advances the chain state."""
        if not self.is_connected:
            raise ConnectionError("Not connected to the blockchain RPC.")
        # Simulate chain progression
        self.current_block += random.randint(1, 3)
        return self.current_block

    def get_events_for_range(self, from_block: int, to_block: int) -> List[LogReceipt]:
        """Simulates fetching event logs for a given block range."""
        if not self.is_connected:
            raise ConnectionError("Not connected to the blockchain RPC.
")
        
        logs = []
        for block_num in range(from_block, to_block + 1):
            # Sporadically generate a mock event
            if random.random() < 0.2: # 20% chance to have an event in a block
                mock_log = self._create_mock_log(block_num)
                logs.append(mock_log)
                logging.info(f"[{self.chain_name}] Found mock event in block {block_num}")
        return logs

    def _create_mock_log(self, block_number: int) -> LogReceipt:
        """Generates a single mock log entry consistent with the ABI."""
        user_address = Web3.to_checksum_address(f'0x{random.randbytes(20).hex()}')
        token_address = Web3.to_checksum_address(f'0x{random.randbytes(20).hex()}')
        amount = random.randint(100, 100000) * 10**18
        dest_chain_id = 2 # The ID of the destination chain

        # Encode data part according to ABI
        data = abi_decode(['uint256', 'uint256'], b'')[0](amount, dest_chain_id)

        log_entry = {
            'address': BRIDGE_CONTRACT_ADDRESS,
            'topics': [
                EVENT_SIGNATURE_HASH,
                '0x' + user_address[2:].zfill(64),
                '0x' + token_address[2:].zfill(64)
            ],
            'data': '0x' + data.hex(),
            'blockNumber': block_number,
            'transactionHash': '0x' + random.randbytes(32).hex(),
            'transactionIndex': random.randint(0, 10),
            'logIndex': random.randint(0, 5),
            'removed': False
        }
        return log_entry


class EventParser:
    """Parses raw event logs into a structured format based on a contract ABI."""
    def __init__(self, abi: List[Dict[str, Any]]):
        self.event_abi = next((item for item in abi if item['type'] == 'event'), None)
        if not self.event_abi:
            raise ValueError("Provided ABI does not contain a valid event definition.")
        
        self.indexed_inputs = [inp for inp in self.event_abi['inputs'] if inp['indexed']]
        self.non_indexed_inputs = [inp for inp in self.event_abi['inputs'] if not inp['indexed']]

    def parse_log(self, log: LogReceipt) -> Optional[Dict[str, Any]]:
        """Decodes a raw log into a dictionary of event parameters."""
        try:
            parsed_event = {"event_name": self.event_abi['name']}

            # Decode indexed topics (skipping the first topic, which is the event signature)
            for i, inp in enumerate(self.indexed_inputs):
                topic_data = log['topics'][i + 1]
                # Addresses are directly represented in topics
                if inp['type'] == 'address':
                    parsed_event[inp['name']] = Web3.to_checksum_address(f"0x{topic_data[-40:]}")
                else:
                    # For other types, proper decoding is needed
                    parsed_event[inp['name']] = abi_decode([inp['type']], topic_data)[0]
            
            # Decode non-indexed data
            data_types = [inp['type'] for inp in self.non_indexed_inputs]
            decoded_data = abi_decode(data_types, bytes.fromhex(log['data'][2:]))
            
            for i, inp in enumerate(self.non_indexed_inputs):
                parsed_event[inp['name']] = decoded_data[i]
            
            # Add metadata
            parsed_event['transactionHash'] = log['transactionHash']
            parsed_event['blockNumber'] = log['blockNumber']

            return parsed_event
        except Exception as e:
            logging.error(f"Failed to parse log {log.get('transactionHash')}: {e}")
            return None


class TransactionRelayer:
    """Simulates the process of relaying a transaction to the destination chain."""
    def __init__(self, dest_connector: MockBlockchainConnector):
        self.dest_connector = dest_connector

    def simulate_relay_transaction(self, event_data: Dict[str, Any]):
        """Simulates signing and sending a mint transaction on the destination chain."""
        logging.info(f"[{self.dest_connector.chain_name}] Relaying transaction for user {event_data['user']}...")
        logging.info(f"[{self.dest_connector.chain_name}]   - Amount: {event_data['amount'] / 10**18}")
        logging.info(f"[{self.dest_connector.chain_name}]   - Original Tx: {event_data['transactionHash']}")
        
        # Simulate network latency and transaction processing
        time.sleep(random.uniform(1, 3))
        
        # Simulate potential failure
        if random.random() < 0.05: # 5% failure chance
            logging.error(f"[{self.dest_connector.chain_name}] FAILED to relay transaction for {event_data['transactionHash']}.")
            return False
        
        mock_dest_tx_hash = '0x' + random.randbytes(32).hex()
        logging.info(f"[{self.dest_connector.chain_name}] Transaction successfully relayed. Destination Tx Hash: {mock_dest_tx_hash}")
        return True


class CrossChainBridgeListener:
    """The main orchestrator that listens for events and coordinates the bridging process."""
    def __init__(self, source_chain_rpc: str, dest_chain_rpc: str, contract_address: str):
        self.source_connector = MockBlockchainConnector(source_chain_rpc, 'SourceChain')
        self.dest_connector = MockBlockchainConnector(dest_chain_rpc, 'DestChain')
        self.contract_address = contract_address
        self.state_db = StateDB(STATE_FILE)
        self.event_parser = EventParser(BRIDGE_ABI)
        self.relayer = TransactionRelayer(self.dest_connector)
        self.is_running = False

    def run(self):
        """Starts the main event listening loop."""
        logging.info("Initializing Cross-Chain Bridge Listener...")
        self.source_connector.connect()
        self.dest_connector.connect()

        if not self.source_connector.is_connected:
            logging.critical("Cannot start listener: failed to connect to source chain.")
            return
        
        self.is_running = True
        logging.info("Listener started. Polling for new blocks...")
        
        while self.is_running:
            try:
                self._process_new_blocks()
                time.sleep(POLLING_INTERVAL_SECONDS)
            except KeyboardInterrupt:
                self.shutdown()
            except Exception as e:
                logging.error(f"An unexpected error occurred in the main loop: {e}")
                time.sleep(POLLING_INTERVAL_SECONDS * 2) # Longer sleep after an error

    def _process_new_blocks(self):
        """Fetches and processes blocks since the last check."""
        last_processed = self.state_db.get_last_processed_block()
        latest_block = self.source_connector.get_latest_block()

        # The `to_block` is calculated ensuring we have enough confirmations.
        # This is a simplified re-org protection mechanism.
        to_block = latest_block - CONFIRMATIONS_REQUIRED
        from_block = last_processed + 1

        if from_block > to_block:
            logging.debug(f"No new blocks to process. Current head: {latest_block}, waiting for confirmations.")
            return
        
        # To avoid overwhelming the RPC, process in batches.
        if to_block - from_block > BLOCK_PROCESSING_BATCH_SIZE:
            to_block = from_block + BLOCK_PROCESSING_BATCH_SIZE - 1

        logging.info(f"Scanning blocks from {from_block} to {to_block}...")
        
        try:
            logs = self.source_connector.get_events_for_range(from_block, to_block)
            
            if not logs:
                logging.debug(f"No relevant events found in blocks {from_block}-{to_block}.")
            else:
                for log in logs:
                    event_hash = Web3.keccak(text=f"{log['transactionHash']}{log['logIndex']}").hex()
                    if self.state_db.is_event_processed(event_hash):
                        logging.warning(f"Skipping already processed event: {event_hash}")
                        continue

                    parsed_event = self.event_parser.parse_log(log)
                    if parsed_event:
                        logging.info(f"Processing new event: {parsed_event}")
                        if self.relayer.simulate_relay_transaction(parsed_event):
                            self.state_db.mark_event_as_processed(event_hash)
            
            # Update state only after the batch is processed
            self.state_db.set_last_processed_block(to_block)
            self.state_db.save_state()

        except Exception as e:
            logging.error(f"Error processing block range {from_block}-{to_block}: {e}")

    def shutdown(self):
        """Performs a graceful shutdown of the listener."""
        if self.is_running:
            logging.info("Shutting down the listener...")
            self.is_running = False
            self.state_db.save_state()
            logging.info("Final state saved. Goodbye!")


if __name__ == '__main__':
    listener = CrossChainBridgeListener(
        source_chain_rpc=SOURCE_CHAIN_RPC,
        dest_chain_rpc=DEST_CHAIN_RPC,
        contract_address=BRIDGE_CONTRACT_ADDRESS
    )
    listener.run()
