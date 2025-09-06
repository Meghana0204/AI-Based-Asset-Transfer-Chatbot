# AI-Based Asset Transfer Chatbot

An AI-powered conversational chatbot designed to simplify **cryptocurrency transactions**.  
Built as a **Telegram bot**, it allows users to **check balances, transfer tokens, and stake assets** using simple natural language commands like:

> *"Send 0.5 ETH to Alice"*  

The bot leverages **AI for natural language understanding** and **Web3 blockchain integration** for secure, real-time asset transfers.

---

## Features

- **Wallet Integration** – Connect to Ethereum wallets seamlessly.  
- **Balance Checks** – Get real-time wallet balances.  
- **Asset Transfers** – Send and receive tokens with simple chat commands.  
- **Staking Support** – Interact with staking features via smart contracts.  
- **AI-Powered Conversations** – Natural language processing using **OpenAI GPT API**.  
- **Secure Backend** – Built with Flask and MongoDB to ensure safe transaction handling.  

---

## Tech Stack

- **Frontend / Interface**: Telegram Bot API  
- **AI / NLP**: OpenAI GPT API  
- **Backend**: Python, Flask, MongoDB  
- **Blockchain**: Ethereum, Web3.py  

---

## Getting Started

### Clone the repository
```bash
git clone https://github.com/Meghana0204/AI-Based-Asset-Transfer-Chatbot.git
cd AI-Based-Asset-Transfer-Chatbot

## Install dependencies
pip install -r requirements.txt
```
---

## Configure environment variables
Create a .env file in the root directory and add:
```bash
OPENAI_API_KEY=your_openai_api_key
TELEGRAM_BOT_TOKEN=your_telegram_token
MONGODB_URI=your_mongo_connection_string
ETH_PROVIDER_URL=https://mainnet.infura.io/v3/your_project_id 
```
---

## Run the application
```bash
python app.py
```

---

## Demo
Example conversation:
```bash
User: Check my ETH balance
Bot: Your wallet balance is 1.245 ETH

User: Send 0.5 ETH to 0xAbC123...
Bot: Transaction successful ✅ Hash: 0x9f8abc...

```
---
## Contributing

Contributions, feature requests, and bug reports are always welcome!
Steps to contribute:
1. Fork the project
2. Create your feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add some amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

## Author
Meghana Pradeep
- 🌐 [LinkedIn](https://linkedin.com/in/meghana-pradeep-29b01329b)  
- 💻 [GitHub](https://github.com/Meghana0204)

## License
This project is licensed under the MIT License – free to use and modify.
