from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

# Node access params
RPC_URL = "http://alice:password@127.0.0.1:18443"

def main():
    try:
        # General client for non-wallet-specific commands
        client = AuthServiceProxy(RPC_URL)

        # Get blockchain info (optional, just to test connection)
        blockchain_info = client.getblockchaininfo()
        print("Blockchain Info:", blockchain_info)

        # Create/Load the wallets, named 'Miner' and 'Trader'.
        # Have logic to optionally create/load them if they do not exist or are not loaded already.
        def ensure_wallet(name):
            # Get currently loaded wallets
            loaded = client.listwallets()
            if name in loaded:
                return
            try:
                client.createwallet(name)
            except JSONRPCException as e:
                # If wallet already exists on disk, load it
                if "Database already exists" in str(e) or "already exists" in str(e):
                    try:
                        client.loadwallet(name)
                    except JSONRPCException as load_err:
                        print(f"Failed to load wallet {name}: {load_err}")
                        raise
                else:
                    raise

        ensure_wallet("Miner")
        ensure_wallet("Trader")

        # Wallet-specific RPC connections
        miner = AuthServiceProxy(f"{RPC_URL}/wallet/Miner")
        trader = AuthServiceProxy(f"{RPC_URL}/wallet/Trader")

        # Generate spendable balances in the Miner wallet.
        # Determine how many blocks need to be mined. (101 to make coinbase spendable)
        mining_address = miner.getnewaddress("Mining Reward", "bech32")
        miner.generatetoaddress(101, mining_address)
        print(f"Miner balance: {miner.getbalance()} BTC")

        # Load the Trader wallet and generate a new address.
        trader_address = trader.getnewaddress("Received", "bech32")
        print(f"Trader address: {trader_address}")

        # Send 20 BTC from Miner to Trader.
        txid = miner.sendtoaddress(trader_address, 20)
        print(f"Transaction sent: {txid}")

        # Check the transaction in the mempool.
        mempool_entry = client.getmempoolentry(txid)
        print("Mempool entry:", mempool_entry)

        # Mine 1 block to confirm the transaction.
        miner.generatetoaddress(1, mining_address)

        # Extract all required transaction details.
        # Get the confirmed transaction
        tx = client.getrawtransaction(txid, True)

        # Input details – take first input (assuming single input)
        vin = tx["vin"][0]
        prev_tx = client.getrawtransaction(vin["txid"], True)
        prev_out = prev_tx["vout"][vin["vout"]]

        miner_input_address = prev_out["scriptPubKey"]["address"]
        miner_input_amount = prev_out["value"]

        # Output details – find trader output and change (if any)
        trader_output_amount = None
        change_address = None
        change_amount = 0.0

        for vout in tx["vout"]:
            addr = vout["scriptPubKey"]["address"]
            value = vout["value"]
            if addr == trader_address:
                trader_output_amount = value
            else:
                change_address = addr
                change_amount = value

        # If no change output, set placeholders
        if change_address is None:
            change_address = "N/A"
            change_amount = 0.0

        fee = miner_input_amount - trader_output_amount - change_amount

        blockhash = tx["blockhash"]
        block = client.getblock(blockhash)
        height = block["height"]

        # Write the data to ../out.txt in the specified format given in readme.md.
        with open("../out.txt", "w") as f:
            f.write(f"{txid}\n")
            f.write(f"{miner_input_address}\n")
            f.write(f"{miner_input_amount}\n")
            f.write(f"{trader_address}\n")
            f.write(f"{trader_output_amount}\n")
            f.write(f"{change_address}\n")
            f.write(f"{change_amount}\n")
            f.write(f"{fee}\n")
            f.write(f"{height}\n")
            f.write(f"{blockhash}\n")

        print("All done. Results written to ../out.txt")

    except Exception as e:
        print("Error occurred: {}".format(e))

if __name__ == "__main__":
    main()