# {repo_name}

A simulation of a robust event listener for a cross-chain bridge. This Python script demonstrates the architectural patterns required to reliably listen for on-chain events on a source blockchain and trigger corresponding actions on a destination blockchain.

This project is an architectural showcase, simulating blockchain interactions without requiring a live RPC endpoint. It highlights best practices for building reliable blockchain services, including state management, error handling, and modular design.

## Concept

Cross-chain bridges allow users to transfer assets or data from one blockchain to another. A critical component of any bridge is the "relayer" or "oracle" network that monitors the source chain for specific events and relays them to the destination chain.

This script simulates such a component. Its primary functions are to:
1.  **Monitor** a `Bridge` smart contract on a source chain.
2.  **Listen** for a `TokensLocked` event, which is emitted when a user deposits assets.
3.  **Parse** the event data to extract details like the user, token, amount, and destination chain.
4.  **Relay** this information to a destination chain by simulating the submission of a new transaction (e.g., a `mint` transaction to issue wrapped tokens).

The listener specifically targets an event with a structure like this:
```solidity
// Simplified event from a source Bridge.sol contract
event TokensLocked(
    address indexed user,
    address indexed token,
    uint256 amount,
    uint256 destinationChainId
);
```

## Code Architecture

The script is structured into several distinct classes, each with a single responsibility to ensure modularity and testability.

```
+----------------------------+
|           main.py          | (Entry Point)
+-------------+--------------+
              |
              | Instantiates
              v
+-------------+----------------------+
|   CrossChainBridgeListener       | (Orchestrator)
+----------------------------------+
| - source_connector: MockBlockchainConnector
| - dest_connector: MockBlockchainConnector
| - state_db: StateDB
| - event_parser: EventParser
| - relayer: TransactionRelayer
| - run() : Main Loop
+------------------+---------------+------------------+
                   |               |                  |
                   v               v                  v
+------------------+     +---------+--------+    +----+-------------+
| MockBlockchainConnector |     |   EventParser    |    | TransactionRelayer |
+------------------+     +------------------+    +------------------+
| - get_latest_block()  |     | - parse_log()    |    | - simulate_relay() |
| - get_events...()     |     +------------------+    +------------------+
+------------------+
                   |
                   v
+------------------+
|      StateDB     |
+------------------+
| - load_state()   |
| - save_state()   |
+------------------+
```

-   `MockBlockchainConnector`: Simulates a connection to a blockchain's JSON-RPC endpoint. It generates a stream of mock blocks and events, removing the need for a live Ganache instance or public testnet connection. This makes the simulation self-contained.
-   `EventParser`: Takes raw log data (as provided by an RPC node) and decodes it into a human-readable, structured format using a predefined contract ABI.
-   `TransactionRelayer`: Simulates the action of creating, signing, and broadcasting a transaction on the destination chain. It includes simulated latency and failure modes.
-   `StateDB`: Manages persistent state in a simple `state.json` file. It's responsible for tracking the last block number processed and which events have already been handled, ensuring the listener can resume from where it left off and avoid duplicate processing.
-   `CrossChainBridgeListener`: The core class that orchestrates the entire process. It contains the main polling loop, coordinates the other components, and handles high-level logic like batching and block confirmations.

## How it Works

The listener operates in a continuous polling loop:

1.  **Initialization**: On startup, the listener initializes all components and connects to the (simulated) source and destination chain RPC endpoints.
2.  **State Loading**: It loads its previous state from `state.json` using the `StateDB` class. This tells it which block to start scanning from.
3.  **Polling Loop**: The listener enters an infinite loop, periodically checking for new blocks.
4.  **Block Confirmation**: To handle potential blockchain re-organizations (reorgs), the listener waits for a certain number of blocks (`CONFIRMATIONS_REQUIRED`) to pass before processing events. This ensures the events it acts upon are on a finalized portion of the chain.
5.  **Event Fetching**: For the confirmed block range, it calls the `MockBlockchainConnector` to fetch all logs that match the bridge contract's address and the `TokensLocked` event signature.
6.  **Parsing & Deduplication**: Each fetched log is parsed by the `EventParser`. A unique hash for the event is generated, and the `StateDB` is checked to ensure it has not been processed before.
7.  **Transaction Relaying**: For each new, valid event, the `TransactionRelayer` is invoked to simulate the corresponding transaction on the destination chain.
8.  **State Persistence**: After processing a batch of blocks, the listener updates the `last_processed_block` in its state via `StateDB` and saves it to disk.
9.  **Graceful Shutdown**: If the process is interrupted (e.g., with Ctrl+C), it catches the signal, saves its current state, and exits gracefully.

## Getting Started

Follow these steps to run the simulation.

**1. Clone the Repository**
```bash
git clone https://github.com/your-username/{repo_name}.git
cd {repo_name}
```

**2. Set Up a Virtual Environment**
It's highly recommended to use a virtual environment to manage dependencies.
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

**3. Install Dependencies**
This project has no external runtime dependencies. A `requirements.txt` file may be included for development tools, which can be installed using:
```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables (Optional)**
The script uses default mock RPC URLs. You can override them via environment variables if you wish to modify the simulation parameters.
```bash
export SOURCE_CHAIN_RPC="https://mock.source.chain.rpc"
export DEST_CHAIN_RPC="https://mock.dest.chain.rpc"
```

**5. Run the Script**
Start the listener by running the main script. The simulation will begin, and you will see its activity logged to the console.
```bash
python main.py
```

### Expected Output
You will see log messages indicating the listener's activity, such as connecting to chains, scanning blocks, and processing simulated events.

```
2023-10-27 14:30:00 - INFO - [main] - Initializing Cross-Chain Bridge Listener...
2023-10-27 14:30:00 - INFO - [MockBlockchainConnector] - [SourceChain] MockConnector initialized for https://mock.source.chain.rpc
2023-10-27 14:30:00 - INFO - [MockBlockchainConnector] - [DestChain] MockConnector initialized for https://mock.dest.chain.rpc
2023-10-27 14:30:00 - INFO - [StateDB] - Loading state from state.json
2023-10-27 14:30:00 - INFO - [main] - Listener started. Polling for new blocks...
2023-10-27 14:30:00 - INFO - [main] - Scanning blocks from 15001 to 15112...
2023-10-27 14:30:00 - INFO - [MockBlockchainConnector] - [SourceChain] Found mock event in block 15005
2023-10-27 14:30:00 - INFO - [main] - Processing new event: {'event_name': 'TokensLocked', 'user': '0xabc...def', 'token': '0x123...456', 'amount': 1000000000000000000, 'destinationChainId': 2, 'transactionHash': '0xaaa...bbb', 'blockNumber': 15005}
2023-10-27 14:30:00 - INFO - [TransactionRelayer] - [DestChain] Relaying transaction for user 0xabc...def
...
```