from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext, CallbackQueryHandler
import logging
from web3 import Web3
import json
from datetime import datetime, timedelta

# Define conversation states
(
    CONNECT_WALLET,
    CHOOSE_ACTION,
    AMOUNT,
    COIN_TYPE,
    TO_ADDRESS,
    CONFIRM,
    SWAP_DIRECTION,
    SWAP_AMOUNT,
    CONFIRM_SWAP,
    STAKE_COIN,
    STAKE_AMOUNT,
    CONFIRM_STAKE
) = range(12)

# Logger setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token
TOKEN = "7582638935:AAG7iZtcm0ncpnefP1wpv9b2v0XVfBnEjjk"

# Web3 setup
ETH_NODE = 'https://sepolia.infura.io/v3/5c2a125920b4482695150bb67d3a23ee'  # Replace with your Infura ID
BSC_NODE = 'https://bsc-dataseed.binance.org/'
w3_eth = Web3(Web3.HTTPProvider(ETH_NODE))
w3_bsc = Web3(Web3.HTTPProvider(BSC_NODE))

# Add these constants at the top of your file
STAKE_MINIMUM = {
    'ETH': 0.1,
    'BNB': 1.0
}

STAKE_APR = {
    'ETH': 5.5,  # 5.5% APR for ETH
    'BNB': 8.0   # 8.0% APR for BNB
}

def calculate_rewards(amount: float, apr: float, days: int) -> float:
    """Calculate staking rewards"""
    return amount * (apr / 100) * (days / 365)

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask for wallet connection."""
    context.user_data.clear()
    
    keyboard = [
        ['Connect Wallet'],
        ['Exit']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    update.message.reply_text(
        'Welcome to Blockchain Assistant! 🤖\n\n'
        'Please connect your wallet to continue or select Exit:',
        reply_markup=reply_markup
    )
    return CONNECT_WALLET

def connect_wallet_callback(update: Update, context: CallbackContext) -> int:
    """Handle initial wallet connection request"""
    if update.message.text == 'Connect Wallet':
        update.message.reply_text(
            "🔗 Please enter your wallet address:\n\n"
            "Example: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            reply_markup=ReplyKeyboardMarkup([['Exit']], one_time_keyboard=True)
        )
        return CONNECT_WALLET
    return CONNECT_WALLET

def validate_wallet(update: Update, context: CallbackContext) -> int:
    """Validate wallet address and store it."""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
        
    if update.message.text == 'Connect Wallet':
        return connect_wallet_callback(update, context)
        
    wallet_address = update.message.text.strip()
    
    try:
        # Basic validation for Ethereum/BSC address format
        if not wallet_address.startswith('0x') or len(wallet_address) != 42:
            update.message.reply_text(
                "❌ Invalid wallet format. Address should:\n"
                "• Start with '0x'\n"
                "• Be 42 characters long\n"
                "Please try again:",
                reply_markup=ReplyKeyboardMarkup([['Exit']], one_time_keyboard=True)
            )
            return CONNECT_WALLET
            
        # Additional Web3 validation
        if not Web3.is_address(wallet_address):
            update.message.reply_text(
                "❌ Invalid wallet address. Please check and try again:",
                reply_markup=ReplyKeyboardMarkup([['Exit']], one_time_keyboard=True)
            )
            return CONNECT_WALLET
        
        # Store the checksum address
        context.user_data['wallet_address'] = Web3.to_checksum_address(wallet_address)
        
        # Show main menu with connected wallet
        reply_keyboard = [
            ['Transfer', 'Balance'],
            ['History', 'Swap'],
            ['Stake', 'Help'],
            ['Exit']
        ]
        
        update.message.reply_text(
            f"✅ Wallet connected successfully!\n\n"
            f"Address: {context.user_data['wallet_address'][:6]}...{context.user_data['wallet_address'][-4:]}\n\n"
            f"Please choose an action:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_ACTION
        
    except Exception as e:
        logger.error(f"Wallet validation error: {str(e)}")
        update.message.reply_text(
            "❌ Error validating wallet address.\n"
            "Please make sure you're entering a valid Ethereum/BSC address.",
            reply_markup=ReplyKeyboardMarkup([['Connect Wallet'], ['Exit']], one_time_keyboard=True)
        )
        return CONNECT_WALLET

def check_wallet_connected(update: Update, context: CallbackContext) -> bool:
    """Check if wallet is connected."""
    if 'wallet_address' not in context.user_data:
        update.message.reply_text(
            "Please connect your wallet first!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Connect Wallet", callback_data='connect_wallet')
            ]])
        )
        return False
    return True

def choose_action(update: Update, context: CallbackContext) -> int:
    """Handle action selection."""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
    
    action = update.message.text.lower()
    context.user_data['action'] = action

    if action == 'balance':
        try:
            wallet_address = context.user_data.get('wallet_address')
            if not wallet_address:
                update.message.reply_text(
                    "❌ Please connect your wallet first!",
                    reply_markup=ReplyKeyboardMarkup([
                        ['Back to Menu'],
                        ['Close Initial Process'],
                        ['Exit']
                    ], one_time_keyboard=True)
                )
                return CHOOSE_ACTION

            # Get balances for both ETH and BNB
            try:
                eth_balance = get_wallet_balance(w3_eth, wallet_address, 'ETH')
                bnb_balance = get_wallet_balance(w3_bsc, wallet_address, 'BNB')
                
                balance_text = (
                    f"💰 Wallet Balances\n"
                    f"══════════════════\n"
                    f"Address: {wallet_address[:6]}...{wallet_address[-4:]}\n\n"
                    f"ETH: {eth_balance:.4f}\n"
                    f"BNB: {bnb_balance:.4f}\n"
                    f"══════════════════"
                )
                
                update.message.reply_text(
                    balance_text,
                    reply_markup=ReplyKeyboardMarkup([
                        ['Back to Menu'],
                        ['Close Initial Process'],
                        ['Exit']
                    ], one_time_keyboard=True)
                )
                
            except Exception as e:
                update.message.reply_text(
                    f"❌ Error checking balance: {str(e)}\n"
                    f"Please try again.",
                    reply_markup=ReplyKeyboardMarkup([
                        ['Back to Menu'],
                        ['Close Initial Process'],
                        ['Exit']
                    ], one_time_keyboard=True)
                )
            return CHOOSE_ACTION
            
        except Exception as e:
            update.message.reply_text(
                "❌ Error accessing wallet. Please try again.",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            return CHOOSE_ACTION
            
    elif action == 'transfer':
        update.message.reply_text(
            'Please enter the amount you want to transfer:',
            reply_markup=ReplyKeyboardMarkup([
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
        return AMOUNT
    elif action == 'history':
        try:
            wallet_address = context.user_data.get('wallet_address')
            if not wallet_address:
                update.message.reply_text(
                    "❌ Please connect your wallet first!",
                    reply_markup=ReplyKeyboardMarkup([
                        ['Back to Menu'],
                        ['Close Initial Process'],
                        ['Exit']
                    ], one_time_keyboard=True)
                )
                return CHOOSE_ACTION

            # Get transaction history for both chains
            try:
                # Get ETH transactions
                eth_transactions = get_transaction_history(w3_eth, wallet_address, 'ETH')
                # Get BNB transactions
                bnb_transactions = get_transaction_history(w3_bsc, wallet_address, 'BNB')

                history_text = " Transaction History\n══════════════════\n"
                
                if not eth_transactions and not bnb_transactions:
                    history_text += "\nNo transactions found for this wallet."
                else:
                    if eth_transactions:
                        history_text += "\n🔹 ETH Transactions:\n"
                        for tx in eth_transactions:
                            history_text += (
                                f"\nType: {tx['type']}\n"
                                f"Amount: {tx['value']:.4f} ETH\n"
                                f"Hash: {tx['hash'][:6]}...{tx['hash'][-4:]}\n"
                                f"{'To' if tx['type'] == 'Sent' else 'From'}: "
                                f"{tx['to' if tx['type'] == 'Sent' else 'from'][:6]}..."
                                f"{tx['to' if tx['type'] == 'Sent' else 'from'][-4:]}\n"
                                f"───────────────\n"
                            )
                    
                    if bnb_transactions:
                        history_text += "\n🔸 BNB Transactions:\n"
                        for tx in bnb_transactions:
                            history_text += (
                                f"\nType: {tx['type']}\n"
                                f"Amount: {tx['value']:.4f} BNB\n"
                                f"Hash: {tx['hash'][:6]}...{tx['hash'][-4:]}\n"
                                f"{'To' if tx['type'] == 'Sent' else 'From'}: "
                                f"{tx['to' if tx['type'] == 'Sent' else 'from'][:6]}..."
                                f"{tx['to' if tx['type'] == 'Sent' else 'from'][-4:]}\n"
                                f"───────────────\n"
                            )

                history_text += "\n══════════════════"
                
                update.message.reply_text(
                    history_text,
                    reply_markup=ReplyKeyboardMarkup([
                        ['Back to Menu'],
                        ['Close Initial Process'],
                        ['Exit']
                    ], one_time_keyboard=True)
                )
                
            except Exception as e:
                update.message.reply_text(
                    f"❌ Error fetching transaction history: {str(e)}\n"
                    f"Please try again.",
                    reply_markup=ReplyKeyboardMarkup([
                        ['Back to Menu'],
                        ['Close Initial Process'],
                        ['Exit']
                    ], one_time_keyboard=True)
                )
            return CHOOSE_ACTION
            
        except Exception as e:
            update.message.reply_text(
                "❌ Error accessing wallet. Please try again.",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            return CHOOSE_ACTION
            
    elif action == 'swap':
        reply_keyboard = [
            ['ETH to BNB', 'BNB to ETH'],
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ]
        update.message.reply_text(
            '💱 Choose your swap direction:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return SWAP_DIRECTION
    elif action == 'stake':
        reply_keyboard = [
            ['ETH', 'BNB'],
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ]
        update.message.reply_text(
            '🏦 Choose coin to stake:\n\n'
            f'ETH - {STAKE_APR["ETH"]}% APR\n'
            f'BNB - {STAKE_APR["BNB"]}% APR',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return STAKE_COIN
    elif action == 'help':
        help_command(update, context)
        return CHOOSE_ACTION

def amount(update: Update, context: CallbackContext) -> int:
    """Handle amount input for transfer"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
        
    try:
        amount = float(update.message.text)
        if amount <= 0:
            update.message.reply_text(
                "Amount must be greater than 0. Please try again:",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            return AMOUNT
        
        # Store the amount in context
        context.user_data['transfer_amount'] = amount
        
        # Move to coin selection
        reply_keyboard = [
            ['ETH', 'BNB'],
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ]
        update.message.reply_text(
            'Please choose the coin type:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return COIN_TYPE
        
    except ValueError:
        update.message.reply_text(
            "Please enter a valid number:",
            reply_markup=ReplyKeyboardMarkup([
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
        return AMOUNT

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel and end the conversation."""
    update.message.reply_text(
        'Operation cancelled. Type /start to begin again.',
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()  # Clear stored data
    return ConversationHandler.END

def coin_type(update: Update, context: CallbackContext) -> int:
    """Handle coin type selection for transfer"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
    
    coin = update.message.text.upper()
    if coin not in ['ETH', 'BNB']:
        update.message.reply_text(
            "Please choose a valid coin type (ETH or BNB):",
            reply_markup=ReplyKeyboardMarkup([
                ['ETH', 'BNB'],
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
        return COIN_TYPE
    
    # Store the coin type in context
    context.user_data['transfer_coin_type'] = coin
    
    # Move to recipient address input
    update.message.reply_text(
        'Please enter the recipient address:',
        reply_markup=ReplyKeyboardMarkup([
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ], one_time_keyboard=True)
    )
    return TO_ADDRESS

def to_address(update: Update, context: CallbackContext) -> int:
    """Handle recipient address input"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
    
    address = update.message.text.strip()
    
    try:
        # Validate address format
        if not Web3.is_address(address):
            update.message.reply_text(
                "❌ Invalid wallet address. Please check and try again:",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            return TO_ADDRESS
        
        # Store the recipient address in context
        context.user_data['transfer_to_address'] = Web3.to_checksum_address(address)
        
        # Get transfer details for confirmation
        amount = context.user_data.get('transfer_amount')
        coin_type = context.user_data.get('transfer_coin_type')
        to_addr = context.user_data.get('transfer_to_address')
        
        # Show transfer confirmation
        confirmation_text = (
            f"📤 Transfer Summary:\n\n"
            f"Amount: {amount} {coin_type}\n"
            f"To: {to_addr[:6]}...{to_addr[-4:]}\n"
            f"Gas fee (estimated): 0.01 {coin_type}\n\n"
            f"Please confirm this transfer:"
        )
        
        reply_keyboard = [
            ['Confirm', 'Cancel'],
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ]
        
        update.message.reply_text(
            confirmation_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CONFIRM
        
    except Exception as e:
        logger.error(f"Address validation error: {str(e)}")
        update.message.reply_text(
            "❌ Error validating address. Please try again:",
            reply_markup=ReplyKeyboardMarkup([
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
        return TO_ADDRESS

def confirm(update: Update, context: CallbackContext) -> int:
    """Handle transfer confirmation"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
    
    choice = update.message.text
    
    if choice == 'Confirm':
        try:
            # Get all required transfer details
            amount = context.user_data.get('transfer_amount')
            coin_type = context.user_data.get('transfer_coin_type')
            to_address = context.user_data.get('transfer_to_address')
            wallet_address = context.user_data.get('wallet_address')
            
            # Validate all required details are present
            if not all([amount, coin_type, to_address, wallet_address]):
                missing_fields = []
                if not amount: missing_fields.append("amount")
                if not coin_type: missing_fields.append("coin type")
                if not to_address: missing_fields.append("recipient address")
                if not wallet_address: missing_fields.append("wallet address")
                
                raise ValueError(f"Missing transfer details: {', '.join(missing_fields)}")
            
            # Get appropriate Web3 instance
            if coin_type == 'ETH':
                w3 = w3_eth
            else:  # BNB
                w3 = w3_bsc
            
            # Check balance
            balance = get_wallet_balance(w3, wallet_address, coin_type)
            required_amount = amount + 0.01  # Gas fee buffer
            
            if balance < required_amount:
                update.message.reply_text(
                    f"❌ Insufficient Balance!\n\n"
                    f"Required (including gas): {required_amount} {coin_type}\n"
                    f"Your balance: {balance:.4f} {coin_type}\n\n"
                    f"Please try a smaller amount or add funds to your wallet.",
                    reply_markup=ReplyKeyboardMarkup([
                        ['Check Balance'],
                        ['Back to Menu'],
                        ['Close Initial Process'],
                        ['Exit']
                    ], one_time_keyboard=True)
                )
                return CHOOSE_ACTION
            
            # Generate transaction ID and timestamp
            tx_id = generate_transaction_id()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create transfer confirmation
            confirmation = (
                "✅ Transfer Successful!\n\n"
                f"📝 Transaction Receipt:\n"
                f"══════════════════\n"
                f"ID: {tx_id}\n"
                f"Time: {timestamp}\n"
                f"Status: Completed\n\n"
                f"Amount: {amount} {coin_type}\n"
                f"From: {wallet_address[:6]}...{wallet_address[-4:]}\n"
                f"To: {to_address[:6]}...{to_address[-4:]}\n"
                f"Gas Fee: 0.01 {coin_type}\n"
                f"Remaining Balance: {(balance - required_amount):.4f} {coin_type}\n"
                f"══════════════════\n\n"
                f"💡 Transaction will be reflected in your wallet shortly."
            )
            
            # Clear transfer data
            for key in ['transfer_amount', 'transfer_coin_type', 'transfer_to_address']:
                context.user_data.pop(key, None)
            
            update.message.reply_text(
                confirmation,
                reply_markup=ReplyKeyboardMarkup([
                    ['Check Balance'],
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            
        except Exception as e:
            logger.error(f"Transfer error: {str(e)}")
            update.message.reply_text(
                f"❌ Transfer failed: {str(e)}\n"
                f"Please try again.",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
    else:
        update.message.reply_text(
            "Transfer cancelled.",
            reply_markup=ReplyKeyboardMarkup([
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
    
    return CHOOSE_ACTION

def back_to_menu(update: Update, context: CallbackContext) -> int:
    """Return to main menu."""
    reply_keyboard = [
        ['Transfer', 'Balance'],
        ['History', 'Swap'],
        ['Stake', 'Help'],
        ['Exit']
    ]
    update.message.reply_text(
        'Please choose an action:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSE_ACTION

def close_initial_process(update: Update, context: CallbackContext) -> int:
    """Close the initial process and return to main menu"""
    update.message.reply_text(
        "✖️ Initial process closed.",
        reply_markup=ReplyKeyboardRemove()
    )
    return back_to_menu(update, context)

def help_command(update: Update, context: CallbackContext) -> int:
    """Show help message."""
    help_text = """
🤖 Available Commands:
/start - Start the bot/connect wallet
/help - Show this help message
/cancel - Cancel current operation

Available Actions:
• Transfer - Send crypto to another address
• Balance - Check your wallet balance
• History - View transaction history
• Swap - Exchange between cryptocurrencies
• Stake - Stake your crypto

Note: You must connect your wallet before performing any actions.
    """
    update.message.reply_text(help_text)
    return CHOOSE_ACTION

def get_transaction_history(w3, wallet_address: str, coin_type: str) -> list:
    """Get recent transactions for the wallet"""
    try:
        # Get current block number
        latest_block = w3.eth.block_number
        
        # Look back fewer blocks for quicker response
        look_back_blocks = 100
        start_block = max(0, latest_block - look_back_blocks)
        
        transactions = []
        
        # Get transactions
        for block_num in range(latest_block, start_block, -1):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    if (tx['from'].lower() == wallet_address.lower() or 
                        (tx.get('to') and tx['to'].lower() == wallet_address.lower())):
                        
                        value = w3.from_wei(tx['value'], 'ether')
                        if float(value) > 0:  # Only show non-zero transactions
                            tx_type = 'Sent' if tx['from'].lower() == wallet_address.lower() else 'Received'
                            transactions.append({
                                'hash': tx['hash'].hex(),
                                'type': tx_type,
                                'value': float(value),
                                'block': tx['blockNumber'],
                                'to': tx.get('to', 'Contract Creation'),
                                'from': tx['from']
                            })
                        
                        if len(transactions) >= 5:  # Limit to last 5 transactions
                            return transactions
                            
            except Exception as block_error:
                logger.error(f"Error processing block {block_num}: {str(block_error)}")
                continue
                
        return transactions
        
    except Exception as e:
        logger.error(f"Error getting transaction history: {str(e)}")
        raise

def format_transaction_history(transactions: list, coin_type: str) -> str:
    """Format transaction history for display"""
    if not transactions:
        return f" No transaction history found for {coin_type}."
        
    history_text = f"📝 Transaction History ({coin_type}):\n\n"
    for tx in transactions:
        history_text += (
            f"Type: {tx['type']}\n"
            f"Amount: {tx['value']:.4f} {coin_type}\n"
            f"Hash: {tx['hash'][:6]}...{tx['hash'][-4:]}\n"
            f"Block: {tx['block']}\n"
            f"{'To' if tx['type'] == 'Sent' else 'From'}: "
            f"{tx['to' if tx['type'] == 'Sent' else 'from'][:6]}..."
            f"{tx['to' if tx['type'] == 'Sent' else 'from'][-4:]}\n"
            f"───────────────\n"
        )
    return history_text

def parse_swap_command(message: str) -> tuple:
    """Parse swap command format: 'swap 1.5 eth to bnb'"""
    try:
        parts = message.lower().split()
        if len(parts) != 5 or parts[0] != 'swap' or parts[3] != 'to':
            raise ValueError
        
        amount = float(parts[1])
        from_coin = parts[2]
        to_coin = parts[4]
        
        return amount, from_coin, to_coin
    except:
        raise ValueError("Invalid swap format. Use: swap <amount> <from_coin> to <to_coin>")

def get_swap_rate(from_coin: str, to_coin: str) -> float:
    """Get current swap rate between coins"""
    # In a real implementation, this would fetch real-time rates from an API
    # For demonstration, using fixed rates
    rates = {
        'ETH_BNB': 15.5,  # 1 ETH = 15.5 BNB
        'BNB_ETH': 0.0645  # 1 BNB = 0.0645 ETH
    }
    
    rate_key = f"{from_coin}_{to_coin}"
    return rates.get(rate_key, 0)

def generate_transaction_id():
    """Generate a unique transaction ID"""
    import uuid
    return str(uuid.uuid4())[:8]

def exit_bot(update: Update, context: CallbackContext) -> int:
    """Handle bot exit"""
    # Clear user data
    context.user_data.clear()
    
    # Check if it's a callback query
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            "👋 Thank you for using Blockchain Assistant!\n"
            "Type /start to begin a new session."
        )
    else:
        update.message.reply_text(
            "👋 Thank you for using Blockchain Assistant!\n"
            "Type /start to begin a new session.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.END

def add_exit_option(keyboard):
    """Add exit option to any keyboard"""
    if isinstance(keyboard, list):
        if ['Exit'] not in keyboard:
            keyboard.append(['Exit'])
    return keyboard

def get_wallet_balance(w3, wallet_address: str, coin_type: str) -> float:
    """Get wallet balance for specified coin"""
    try:
        balance_wei = w3.eth.get_balance(wallet_address)
        balance = w3.from_wei(balance_wei, 'ether')
        return float(balance)
    except Exception as e:
        logger.error(f"Error getting balance: {str(e)}")
        raise

def handle_swap_direction(update: Update, context: CallbackContext) -> int:
    """Handle swap direction selection"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
        
    direction = update.message.text.upper()
    
    if direction not in ['ETH TO BNB', 'BNB TO ETH']:
        update.message.reply_text(
            "Please choose a valid swap direction:",
            reply_markup=ReplyKeyboardMarkup([
                ['ETH to BNB', 'BNB to ETH'],
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
        return SWAP_DIRECTION
        
    from_coin, to_coin = direction.split(' TO ')
    context.user_data['from_coin'] = from_coin
    context.user_data['to_coin'] = to_coin
    
    # Get current rate
    rate = get_swap_rate(from_coin, to_coin)
    context.user_data['swap_rate'] = rate
    
    update.message.reply_text(
        f"Current rate: 1 {from_coin} = {rate} {to_coin}\n"
        f"Enter the amount of {from_coin} you want to swap:",
        reply_markup=ReplyKeyboardMarkup([
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ], one_time_keyboard=True)
    )
    return SWAP_AMOUNT

def handle_swap_amount(update: Update, context: CallbackContext) -> int:
    """Handle swap amount input"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
        
    try:
        amount = float(update.message.text)
        if amount <= 0:
            update.message.reply_text(
                "Amount must be greater than 0. Please try again:",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            return SWAP_AMOUNT
            
        from_coin = context.user_data.get('from_coin')
        to_coin = context.user_data.get('to_coin')
        rate = context.user_data.get('swap_rate')
        wallet_address = context.user_data.get('wallet_address')
        
        # Check wallet balance
        if from_coin == 'ETH':
            w3 = w3_eth
        else:  # BNB
            w3 = w3_bsc
            
        balance = get_wallet_balance(w3, wallet_address, from_coin)
        required_amount = amount + 0.01  # Gas fee buffer
        
        if balance < required_amount:
            update.message.reply_text(
                f"❌ Insufficient Balance!\n\n"
                f"Required (including gas): {required_amount} {from_coin}\n"
                f"Your balance: {balance:.4f} {from_coin}\n\n"
                f"Please try a smaller amount or add funds to your wallet.",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            return CHOOSE_ACTION
            
        # Calculate swap details
        output_amount = amount * rate
        gas_fee = 0.01  # Estimated gas fee
        
        # Store swap details
        context.user_data.update({
            'swap_amount': amount,
            'output_amount': output_amount,
            'gas_fee': gas_fee
        })
        
        # Show swap confirmation
        confirmation_text = (
            f"💱 Swap Summary\n"
            f"══════════════════\n"
            f"From: {amount} {from_coin}\n"
            f"To: {output_amount:.4f} {to_coin}\n"
            f"Rate: 1 {from_coin} = {rate} {to_coin}\n"
            f"Gas Fee: {gas_fee} {from_coin}\n"
            f"══════════════════\n\n"
            f"Would you like to proceed?"
        )
        
        reply_keyboard = [
            ['Confirm Swap', 'Cancel'],
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ]
        
        update.message.reply_text(
            confirmation_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CONFIRM_SWAP
        
    except ValueError:
        update.message.reply_text(
            "Please enter a valid number:",
            reply_markup=ReplyKeyboardMarkup([
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
        return SWAP_AMOUNT

def confirm_swap(update: Update, context: CallbackContext) -> int:
    """Handle swap confirmation"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
        
    choice = update.message.text
    
    if choice == 'Confirm Swap':
        try:
            # Get swap details
            from_coin = context.user_data.get('from_coin')
            to_coin = context.user_data.get('to_coin')
            amount = context.user_data.get('swap_amount')
            output_amount = context.user_data.get('output_amount')
            gas_fee = context.user_data.get('gas_fee')
            
            # Generate transaction ID
            tx_id = generate_transaction_id()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create swap receipt
            receipt = (
                "✅ Swap Successful!\n\n"
                f"📝 Swap Receipt:\n"
                f"══════════════════\n"
                f"ID: {tx_id}\n"
                f"Time: {timestamp}\n"
                f"Status: Completed\n\n"
                f"From: {amount} {from_coin}\n"
                f"To: {output_amount:.4f} {to_coin}\n"
                f"Gas Fee: {gas_fee} {from_coin}\n"
                f"══════════════════\n\n"
                f"💡 Swap will be reflected in your wallet shortly."
            )
            
            # Clear swap data
            for key in ['from_coin', 'to_coin', 'swap_amount', 'output_amount', 'gas_fee', 'swap_rate']:
                context.user_data.pop(key, None)
            
            update.message.reply_text(
                receipt,
                reply_markup=ReplyKeyboardMarkup([
                    ['Check Balance'],
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            
        except Exception as e:
            update.message.reply_text(
                f"❌ Swap failed: {str(e)}\n"
                f"Please try again.",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
    else:
        update.message.reply_text(
            "Swap cancelled.",
            reply_markup=ReplyKeyboardMarkup([
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
    
    return CHOOSE_ACTION

def handle_stake_coin(update: Update, context: CallbackContext) -> int:
    """Handle staking coin selection"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
        
    coin = update.message.text.upper()
    
    if coin not in ['ETH', 'BNB']:
        update.message.reply_text(
            "Please choose a valid coin (ETH or BNB):",
            reply_markup=ReplyKeyboardMarkup([
                ['ETH', 'BNB'],
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
        return STAKE_COIN
        
    context.user_data['stake_coin'] = coin
    apr = STAKE_APR[coin]
    
    # Show minimum stake amounts and APR
    min_stake = 0.1 if coin == 'ETH' else 1.0
    update.message.reply_text(
        f"🏦 Staking {coin}\n"
        f"APR: {apr}%\n"
        f"Minimum stake: {min_stake} {coin}\n"
        f"Lock period: 30 days\n\n"
        f"Enter amount to stake:",
        reply_markup=ReplyKeyboardMarkup([
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ], one_time_keyboard=True)
    )
    return STAKE_AMOUNT

def handle_stake_amount(update: Update, context: CallbackContext) -> int:
    """Handle staking amount input"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
        
    try:
        amount = float(update.message.text)
        coin = context.user_data.get('stake_coin')
        min_stake = 0.1 if coin == 'ETH' else 1.0
        
        if amount < min_stake:
            update.message.reply_text(
                f"Amount below minimum stake requirement ({min_stake} {coin}).\n"
                f"Please enter a larger amount:",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            return STAKE_AMOUNT
            
        wallet_address = context.user_data.get('wallet_address')
        
        # Check wallet balance
        if coin == 'ETH':
            w3 = w3_eth
        else:  # BNB
            w3 = w3_bsc
            
        balance = get_wallet_balance(w3, wallet_address, coin)
        required_amount = amount + 0.01  # Gas fee buffer
        
        if balance < required_amount:
            update.message.reply_text(
                f"❌ Insufficient Balance!\n\n"
                f"Required (including gas): {required_amount} {coin}\n"
                f"Your balance: {balance:.4f} {coin}\n\n"
                f"Please try a smaller amount or add funds to your wallet.",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            return CHOOSE_ACTION
            
        # Calculate rewards
        apr = STAKE_APR[coin]
        rewards_30_days = calculate_rewards(amount, apr, 30)
        rewards_365_days = calculate_rewards(amount, apr, 365)
        
        # Store staking details
        context.user_data.update({
            'stake_amount': amount,
            'rewards_30_days': rewards_30_days,
            'rewards_365_days': rewards_365_days,
            'gas_fee': 0.01
        })
        
        # Show staking confirmation
        confirmation_text = (
            f"🏦 Staking Summary\n"
            f"══════════════════\n"
            f"Amount: {amount} {coin}\n"
            f"Lock Period: 30 days\n"
            f"APR: {apr}%\n"
            f"Gas Fee: 0.01 {coin}\n\n"
            f"Estimated Rewards:\n"
            f"• 30 days: {rewards_30_days:.4f} {coin}\n"
            f"• 1 year: {rewards_365_days:.4f} {coin}\n"
            f"══════════════════\n\n"
            f"Would you like to proceed?"
        )
        
        reply_keyboard = [
            ['Confirm Stake', 'Cancel'],
            ['Back to Menu'],
            ['Close Initial Process'],
            ['Exit']
        ]
        
        update.message.reply_text(
            confirmation_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CONFIRM_STAKE
        
    except ValueError:
        update.message.reply_text(
            "Please enter a valid number:",
            reply_markup=ReplyKeyboardMarkup([
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
        return STAKE_AMOUNT

def confirm_stake(update: Update, context: CallbackContext) -> int:
    """Handle stake confirmation"""
    if update.message.text == 'Exit':
        return exit_bot(update, context)
    elif update.message.text == 'Close Initial Process':
        return close_initial_process(update, context)
    elif update.message.text == 'Back to Menu':
        return back_to_menu(update, context)
        
    choice = update.message.text
    
    if choice == 'Confirm Stake':
        try:
            # Get stake details
            coin = context.user_data.get('stake_coin')
            amount = context.user_data.get('stake_amount')
            rewards_30_days = context.user_data.get('rewards_30_days')
            gas_fee = context.user_data.get('gas_fee')
            
            # Generate stake ID
            stake_id = generate_transaction_id()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            
            # Create stake receipt
            receipt = (
                "✅ Staking Successful!\n\n"
                f"📝 Stake Receipt:\n"
                f"══════════════════\n"
                f"ID: {stake_id}\n"
                f"Start Time: {timestamp}\n"
                f"End Time: {end_date}\n"
                f"Status: Active\n\n"
                f"Amount: {amount} {coin}\n"
                f"Lock Period: 30 days\n"
                f"Est. Reward: {rewards_30_days:.4f} {coin}\n"
                f"Gas Fee: {gas_fee} {coin}\n"
                f"══════════════════\n\n"
                f"💡 Stake will be reflected in your wallet shortly."
            )
            
            # Clear stake data
            for key in ['stake_coin', 'stake_amount', 'rewards_30_days', 'rewards_365_days', 'gas_fee']:
                context.user_data.pop(key, None)
            
            update.message.reply_text(
                receipt,
                reply_markup=ReplyKeyboardMarkup([
                    ['Check Balance'],
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
            
        except Exception as e:
            update.message.reply_text(
                f"❌ Staking failed: {str(e)}\n"
                f"Please try again.",
                reply_markup=ReplyKeyboardMarkup([
                    ['Back to Menu'],
                    ['Close Initial Process'],
                    ['Exit']
                ], one_time_keyboard=True)
            )
    else:
        update.message.reply_text(
            "Staking cancelled.",
            reply_markup=ReplyKeyboardMarkup([
                ['Back to Menu'],
                ['Close Initial Process'],
                ['Exit']
            ], one_time_keyboard=True)
        )
    
    return CHOOSE_ACTION

def main() -> None:
    """Start the bot."""
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONNECT_WALLET: [
                MessageHandler(Filters.regex('^Connect Wallet$'), connect_wallet_callback),
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.text & ~Filters.command, validate_wallet)
            ],
            CHOOSE_ACTION: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(
                    Filters.regex('^(Transfer|Balance|History|Swap|Stake|Help)$'),
                    choose_action
                )
            ],
            AMOUNT: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.text & ~Filters.command, amount)
            ],
            COIN_TYPE: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.text & ~Filters.command, coin_type)
            ],
            TO_ADDRESS: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.text & ~Filters.command, to_address)
            ],
            CONFIRM: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.regex('^(Confirm|Cancel)$'), confirm)
            ],
            SWAP_DIRECTION: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.text & ~Filters.command, handle_swap_direction)
            ],
            SWAP_AMOUNT: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.text & ~Filters.command, handle_swap_amount)
            ],
            CONFIRM_SWAP: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.regex('^(Confirm Swap|Cancel)$'), confirm_swap)
            ],
            STAKE_COIN: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.text & ~Filters.command, handle_stake_coin)
            ],
            STAKE_AMOUNT: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.text & ~Filters.command, handle_stake_amount)
            ],
            CONFIRM_STAKE: [
                MessageHandler(Filters.regex('^Exit$'), exit_bot),
                MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
                MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
                MessageHandler(Filters.regex('^(Confirm Stake|Cancel)$'), confirm_stake)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start),
            MessageHandler(Filters.regex('^Exit$'), exit_bot),
            MessageHandler(Filters.regex('^Close Initial Process$'), close_initial_process),
            MessageHandler(Filters.regex('^Back to Menu$'), back_to_menu),
        ]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("help", help_command))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

