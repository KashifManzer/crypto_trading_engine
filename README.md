# Work Trial: Cross-Exchange Trading Engine Core

This project is a foundational implementation of a high-performance application designed to interact with multiple cryptocurrency exchanges, as outlined in the work trial.

Project Architecture
The system is built using Python with asyncio for high-performance, non-blocking I/O. The design is modular, centered around an abstract base class (ExchangeConnector) that defines a common interface for all exchange integrations. This ensures that adding a new exchange is a straightforward process of implementing the required methods.

Modularity: Each exchange is a self-contained class inheriting from a common base, making the system easy to extend.

Performance: Asynchronous requests via aiohttp allow for concurrent data fetching from multiple APIs, minimizing wait times.

Reliability: Standardized data structures and error handling are enforced by the base connector. The use of a universal symbol mapper ensures consistency across exchanges.

Setup and Installation
Clone the Repository:

`https://github.com/KashifManzer/crypto_trading_engine.git` <br>
`cd crypto_trading_engine`

Create a Virtual Environment:

`python -m venv venv` <br>
`source venv/bin/activate` <br>
On Windows, use <br>
`venv\Scripts\activate` <br>

Install Dependencies:

`pip install -r requirements.txt`

Configure API Keys:
Create a `.env` file in the project root directory. This file will securely store your API keys outside of the codebase. Add your keys to this file, following the format in the provided env.example.

First, copy the example file:
`cp env.example .env`

Then edit the `.env` file with your actual API keys:

BINANCE_API_KEY="YOUR_BINANCE_KEY"
BINANCE_API_SECRET="YOUR_BINANCE_SECRET"

KUCOIN_API_KEY="YOUR_KUCOIN_KEY"
KUCOIN_API_SECRET="YOUR_KUCOIN_SECRET"
KUCOIN_PASSPHRASE="YOUR_KUCOIN_PASSPHRASE"

BYBIT_API_KEY="YOUR_BYBIT_KEY"
BYBIT_API_SECRET="YOUR_BYBIT_SECRET"

OKX_API_KEY="YOUR_OKX_KEY"
OKX_API_SECRET="YOUR_OKX_SECRET"
OKX_PASSPHRASE="YOUR_OKX_PASSPHRASE"

BITMART_API_KEY="YOUR_BITMART_KEY"
BITMART_API_SECRET="YOUR_BITMART_SECRET"
BITMART_MEMO="YOUR_BITMART_MEMO"

**Note**: Currently, only Binance is fully implemented. Other exchanges are template implementations that will return mock data.

How to Run
Data Fetching Examples
You can use the core/engine.py as a starting point to test data fetching functionalities. You can run it directly to see an example output.

python -m core.engine

This will fetch the best bid/ask for BTC/USDT across all configured exchanges.

Running the Performance Test (Task 2)
To demonstrate the system's ability to handle rapid execution, run the performance test script. This script will attempt to place and then immediately cancel a specified number of orders.

# Example: Run test for 10 orders on Binance for the BTC/USDT pair

python -m scripts.performance_test --exchange binance --pair BTC/USDT --count 10

Note: This test will attempt to execute real orders. Use with caution on a live account, preferably with a very small quantity or on a testnet if available.

Running the Data Persistence Pipeline (Task 5)
To capture L2 order book data and save it as Parquet files, run the data pipeline script.

# Example: Capture data for 1 minute (60 seconds) from Binance for BTC/USDT, polling every 5 seconds.

python -m scripts.data_pipeline --exchange binance --pair BTC/USDT --duration 60 --interval 5

Data will be saved in the data/ directory, partitioned by exchange, pair, and date.

Task 6: Open-Ended Challenge: Architectural Review & Strategy Proposal
System Design & Scalability: Critique and Evolution
Critique of the Current Prototype
The current implementation, while successfully meeting the trial's requirements, has several weaknesses that would be critical in a live, production environment:

Potential Bottlenecks:

API Rate Limits: The heavy reliance on REST API calls for data like order books and order status updates will quickly lead to rate-limiting by exchanges, especially with many pairs or high-frequency polling.

Network Latency: The request/response nature of REST introduces inherent latency. For high-frequency trading, this delay is unacceptable. Real-time market data should be streamed.

Single Point of Failure: The application runs as a single process. If it crashes, all data collection, monitoring, and trading logic halts. There is no built-in redundancy.

Evolution to a Production-Grade System
To evolve this prototype into a highly-available, low-latency system, I would implement the following architectural changes:

Architecture: Transition from a monolithic application to an event-driven microservices architecture. Components (data ingestion, order management, strategy execution, PnL monitoring) would be decoupled and communicate via a message queue.

Technologies & Frameworks:

Data Ingestion: Immediately switch from REST polling to WebSockets for all real-time data feeds (L2 order books, trades, funding rates). This provides a persistent, low-latency stream of data pushed from the exchange.

Messaging Queue: Use a high-throughput message bus like Kafka or RabbitMQ as the central nervous system. A dedicated "Market Data Ingestor" service for each exchange would subscribe to WebSocket feeds and publish normalized data onto specific topics (e.g., l2_order_books.binance.btc_usdt). Downstream services (strategy, logging, etc.) would subscribe to these topics.

Caching Layer: Implement Redis for storing real-time, ephemeral state. This includes the latest snapshot of the order book for every pair, open order statuses, and current positions. This dramatically reduces the need to query exchange APIs for frequently needed data.

Deployment & Orchestration: Containerize all microservices using Docker and orchestrate them with Kubernetes. This provides automated scaling, self-healing (restarting failed containers), and high availability.

Error Handling & Resilience
A robust strategy for resilience is paramount.

API & Connection Handling:

For REST calls, implement a sophisticated retry mechanism with exponential backoff for transient errors (e.g., 5xx status codes, network timeouts). For permanent errors (4xx like invalid parameters), the system should log the error and trigger alerts without retrying. A circuit breaker pattern should be used to stop sending requests to an unresponsive service.

WebSocket connections must have an automatic reconnection logic with heartbeat checks. Upon reconnection, the system must query REST endpoints to fetch the latest order book snapshot to ensure its state is synchronized before resuming processing of live updates.

State Consistency:

The exchange is always the ultimate source of truth. The system's internal state (in Redis and a persistent DB like PostgreSQL/TimescaleDB) is a replica that can become stale.

I would build a Reconciliation Service that runs periodically (e.g., every few minutes). It would query all open orders and positions from each exchange API and compare them against the system's internal database. Any discrepancies found would be corrected, and alerts would be triggered, ensuring the system's state never drifts permanently from reality.
