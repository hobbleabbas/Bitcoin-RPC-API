# Bitcoin RPC API

This is a simple abstraction over Bitcoin's RPC API that can be used to allow multiple users to host and manage their BTC on your wallet. 

## What is this reference?

These docs explain what the API is, how it works, what various code does, and how to make calls to it (or run it locally).

The API is a simple RPC backend that you can use to create wallets, send coins, and more. You can use our server (in which case we store a copy of the private key behind an auth system), or download a copy yourself (for your own personal node)

## Authentication

### Creating an account

**Parameters**

- Username (string)
- Password (string)

**Method Name:  `create_account`**

**Publicly Accessible: `true`**

**Returns**

- `status` **(string)** Whether the call succeeded
- `message` **(string)** Either a welcome message (if it succeeded) or an error explaining why the call failed

For ease of use, this is a username/password auth, not a bearer or auth token.

To create an account, make the following curl request. Remember to replace the username and password parameters with your own.

```bash
curl 
--header "Content-Type: application/json" \
--request POST \
--data '{"username":"xyz","password":"xyz"}' \
http://206.189.196.8:5000/create_account
```

### Logging into an account

**Parameters**

- Username (string)
- Password (string)

**Method Name:  `log_in`**

**Publicly Accessible: `false`**

**Returns**

- `status` **(bool)** Whether the user authenticated
- `message` **(string)** Either a success message or an "incorrect login credentials" message if the call failed
- `user_details` **(tuple)** Only returns if a user authenticated successfully. Contains user's id, name, and password. Used to construct wallet names, for examples.

To log in, make the same request but just with the `log_in` method. Note that the API doesn't currently support session authentication.

## Create a wallet

**Parameters**

- Name (string) - name of the new wallet. If you already have a wallet with the same name, this will return an error
- Username (string)
- Password (string)

**Method Name:  `create_wallet`**

**Publicly Accessible: `true`**

**Returns**

- `status` **(string)** Whether the call succeeded
- `message` **(string)** A message about your new wallet. If there was an error in creating it, the error message will be returned here.
- `mneumonic` **(string)** Your wallet mnemonic. Needed to do a full export of your wallet

You can create as many wallets as you would like. To create a wallet, simply pass in the wallet name, your username, and your password. The call will return an error if you already have a wallet with the same name

```bash
curl 
--header "Content-Type: application/json" \
--request POST \
--data '{"username":"xyz","password":"xyz" "name": "mynewwallet"}' \
http://206.189.196.8:5000/create_wallet
```

## Query a transaction

**Parameters**

- Transaction (string) - the transaction hash
- Full transaction (bool) - whether you want the full transaction or just a summary. Default set to false

**Method Name:  `get_transaction`**

**Publicly Accessible: `true`**

**Returns**

- `status` **(string)** Whether the call succeeded
- `transaction_details` **(object)** JSON object with transaction details
    - If you passed in the `full` parameter as false, you will receive the following info:
        - Confirmations
        - Recipient details (a list containing objects with each address that received a payment as well as the value of said payment)
        - Time
        - Total amount received
        - Total amount paid in fees (implied by lowest amount recieved)
        - Transaction value

To make this request, pass in a transaction hash, and if you would like the full transaction details, pass in the `full transaction` parameter as True. By default it is set to false. 

```bash
curl 
--header "Content-Type: application/json" \
--request POST \
--data '{"txn_number":"xyz","full":false}' \
http://67.205.146.132:5000/get_transaction
```

## Retrieve a wallet

**Parameters**

- Name (string) - the wallet's name
- Username (string) - your username
- Password (string) - your password

**Method Name:** **`retrieve_wallet`**

**Publicly Accessible: `true`**

**Returns**

- `status` **(string)** Whether the call succeeded
- `message` **(string)** If your call fails, there will be a message explaining why
- `wallet_details` **(object)** If the call succeeds, you will be returned an object with your wallet details

```bash
curl 
--header "Content-Type: application/json" \
--request POST \
--data '{"username":"xyz","password":"xyz", "name": "mywallet"}' \
http://67.205.146.132:5000/retrieve_wallet
```

## Send coins

**Parameters** 

- Username (string) - your username
- Password (string) - your password
- Wallet (string) - the name of the wallet you want to send coins from
- Amount (string or float) - amount of BTC to send
- Recipient Address (string) - address to send BTC to
- fees (bool, default = `False`) - whether you want to include transaction fees

```bash
curl 
--header "Content-Type: application/json" \
--request POST \
--data '{"username":"xyz","password":"xyz", "wallet": "abcd", "amount": "0.2", "recipient_address": "abcd-efgh-ijkl", "fees": "true"}' \
http://67.205.146.132:5000/send_coins
```

## List your wallets

**Parameters**

- Username (string) - your username
- Password (string) - your password

**Method Name:** **`list_wallets`**

**Publicly Accessible: `true`**

**Returns**

- `status` **(string)** Whether the call succeeded
- `message` **(string)** A message about your wallets. If you have wallets this returns the wallet names
- `number_of_wallets` **(int)** Number of wallets in your account

```bash
curl 
--header "Content-Type: application/json" \
--request POST \
--data '{"username":"xyz","password":"xyz"}' \
http://206.189.196.8:5000/list_wallets
```

## Self Deploying
To deploy yourself:
- Create a Bitcoin node 
- Clone this repository
- Install all needed packages (flask, python-dotenv, psycopg2, and mnemonic)
- Create a new Postgres instance (personally I'm using a Supabase free tier instance)
- Recommended: Currently passwords are stored in plain text for speed, I would recommend hashing it
- Create a .env file with your config and DB details (see .env.example)

Fork this repository as a repl: https://replit.com/@hobbleabbas/Bitcoin-RPC-API#main.py
