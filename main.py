from flask import Flask, request
import requests
import json
import psycopg2
from mnemonic import Mnemonic
import os
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
from dotenv import load_dotenv, find_dotenv

# Load enviroment variables
load_dotenv(find_dotenv())


NODE_URL = os.getenv('NODE_URL')
NODE_USER = os.getenv('NODE_USER')
NODE_PASSWORD = os.getenv('NODE_PASSWORD')

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

app = Flask('application')

## PRIVATE FUNCTIONS - NOT PUBLICLY ACCESSIBLE

# Basic function to make rpc calls
def rpc(method, params=[], path=NODE_URL):
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": "minebet",
        "method": method,
        "params": params
    })

    return requests.post(path, auth=(NODE_USER, NODE_PASSWORD), data=payload).json()['result']

def generate_mnemonic():
    mnemo = Mnemonic("english")
    words = mnemo.generate(strength=128)
    words = words.split()
    return words

def save_error(error_message):
    with open("errors.txt", "a") as errorfile:
        errorfile.write(error_message)


def log_in(username, password):
    '''
    @param username -  STRING - user's set username
    @param password -  STRING - user's set password
    '''

    if type(username) != str:
        return type_error('username', 'string')

    if type(password) != str:
        return type_error('password', 'string')

    # Initialize new postgres connection
    # Keeping one connection raises an error where it refuses to insert valid queries if it has failed another query
    # To avoid this we just create a new transaction block
    conn = psycopg2.connect(host=DB_HOST,
                        port="5432",
                        user="postgres",
                        password="BasharHafezAlAssad")

    cursor = conn.cursor()

    select_user_query = "select * from rpc_users where username = %s"
    cursor.execute(select_user_query, (username,))
    user = cursor.fetchall()

    for user_details in user:
        if password == user_details[3]:
            message = "Successfully logged in"
            return True, message, user_details
        else:
            message = "Incorrect login credentials"
            return False, message

    cursor.close()
    conn.close()

def auth_error():
    # This function is a template for an incorrect error auth message.
    # Mostly because I already use a true/false system
    # The code could be refactored to include this directly in the log_in function
    return {
        "status": "error",
        "message": "incorrect login credentials"
    }

def parameter_error(key):
    '''
    @param key - STRING - name of the missing parameter
    '''

    message = "incomplete parameters. please pass in the " + key + " parameter."

    return {
        "status": "error",
        "message": message
    }

def type_error(key, correct_type):
    '''
    @param key - STRING - The parameter with the incorrect type
    '''

    message = "Please pass in the " + key + " parameter as a " + correct_type
    return {
        "status": "error",
        "message": message
    }

## PUBLIC FUNCTIONS - USER CAN ACCESS

@app.route('/create_account', methods=['POST'])
def create_account():
    '''
    @param username - STRING - the username the user wants. Must be unique
    @param password - STRING - the password the user wants
    '''

    # Initialize new postgres connection
    # Keeping one connection raises an error where it refuses to insert valid queries if it has failed another query
    # To avoid this we just create a new transaction block
    conn = psycopg2.connect(host=DB_HOST,
                        port=DB_PORT,
                        user=DB_USER,
                        password=DB_PASSWORD)

    cursor = conn.cursor()

    # Get parameters
    data = request.get_json()
    try:
        username = data["username"]
        password = data["password"]

        if type(username) != str:
            return type_error('username', 'string')

        if type(password) != str:
            return type_error('password', 'string')
    except KeyError as error:
        # tell user what parameter they are missing
        return parameter_error(error.args[0])

    try:
        cursor.execute("INSERT INTO rpc_users (username, password) VALUES(%s, %s)", (username, password))
        conn.commit()
        message = "Thanks for creating your account, " + username + "!"

        return {
            "status": "success",
            "message": message
        }
    except Exception as error:

        # The most common error is that the username exists. If so, we can replace the postgres error with something nicer
        username_taken_error = 'duplicate key value violates unique constraint \"rpc_users_pkey\"\nDETAIL:  Key (username)=(' + username + ') already exists.\n'

        if str(error) == username_taken_error:
            return {
                "status": "error",
                "message": "username taken"
            }
        else:
            return {
                "status": "error",
                "message": str(error)
            }

    cursor.close()
    conn.close()

@app.route('/get_transaction', methods=['POST'])
def get_transaction():

    '''
    @param txn_number - STRING - The transaction number, as a hash
    @param full - BOOL - whether you want the full transaction details or an overview of the transaction
    '''

    # Get parameters
    data = request.get_json()
    try:
        txn_number = data["txn_number"]
        full = data["full"]

        if type(txn_number) != str:
                return type_error('txn_number', 'string')

        if type(full) != bool:
            return type_error('full', 'boolean')
    except KeyError as error:
        # tell user what parameter they are missing
        return parameter_error(error.args[0])

    try:
        result = rpc("getrawtransaction", params = [txn_number, True])
        if result == None:
            return "No transaction found"
        else:
            if full:
                return result
            else:
                # Process result, and provide key details (e.g. transaction fee and total amt)
                time = result["time"]
                confirmations = result["confirmations"]
                inputs = result["vin"]
                outputs = result["vout"]
                transaction_id = result["txid"]
                tx_hash = result["hash"]

                # Initialize values to calculate
                total_outputs = []
                transaction_value = 0
                output_values = []

                for output_item in outputs:
                    # calculate total output
                    value = output_item["value"]
                    address = output_item["scriptPubKey"]["address"]


                    details = {
                       "value": value,
                       "address": address,
                    }

                    total_outputs.append(details)
                    transaction_value += value
                    output_values.append(value)

                # this assumes that the transaction fee is the lowest vout
                transaction_fee = min(output_values)

                total_received = transaction_value - transaction_fee

                payload = {
                     "time": time,
                     "confirmations": confirmations,
                     "transaction value": transaction_value,
                     "total recieved": total_received,
                     "transaction fee": transaction_fee,
                     "recepient details": total_outputs
                }

                return {
                    "status": "success",
                    "transaction_details": payload,
                }

    except Exception as error:
        return error
        # return "Connection error occured. Please try again later"

@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    '''
    @param name - STRING - name of the wallet in question
    @param username - STRING - user's set username
    @param password - STRING - user's set password
    '''

    # Initialize new postgres connection
    # Keeping one connection raises an error where it refuses to insert valid queries if it has failed another query
    # To avoid this we just create a new transaction block
    conn = psycopg2.connect(host=DB_HOST,
                        port=DB_PORT,
                        user=DB_USER,
                        password=DB_PASSWORD)

    cursor = conn.cursor()

    # Get parameters
    data = request.get_json()
    try:
        username = data["username"]
        password = data["password"]
        name = data["name"]
    except KeyError as error:
        # tell user what parameter they are missing
        return parameter_error(error.args[0])

    auth = log_in(username, password)

    if auth[0]:
        # GENERATE RANDOM MNUMONIC
        mnemonic = generate_mnemonic()
        # We gotta convert he list to words to return to the user
        mnemonic_words = ' '.join(mnemonic)

        try:
            # convert wallet name to a unique name with their id 
            user_id = auth[2][0]
            username = auth[2][2]
            wallet_name = user_id + '_' + str(name)
            result = rpc("createwallet", params = [wallet_name])
            if result == None:
                status = "error"
                message = "Looks like you already have a wallet with this name."
                mnemonic_words  = None
            else:
                if result["warning"] != '':
                    message = "Wallet created successfully, with a warning: " + result["warning"] + ". Your mneumonic is " + mnemonic_words + ". Please keep this phrase safe, as you'll need it to access your wallet."
                    status = "success"
                    try:
                        cursor.execute("INSERT INTO wallets (name, user, user_id, mnemonic) VALUES(%s, %s, %s, %s)", (wallet_name, username, user_id, mnemonic))
                        conn.commit()
                    except:
                        message = "Internal error. Please contact hobbleabbas@gmail.com"

                else:
                    status = "success"
                    try:
                        cursor.execute("INSERT INTO wallets (wallet_name, user_id, username, mnemonic) VALUES(%s, %s, %s, %s)", (wallet_name, user_id, username, json.dumps(mnemonic)))
                        # cursor.execute("INSERT INTO wallets (name, user, user_id, mnemonic) VALUES(%s, %s, %s, %s)", (wallet_name, username, user_id, mnemonic))
                        conn.commit()
                        message = "Wallet '" + name + "' created successfully. Your mneumonic is " + mnemonic_words + ". Please keep this phrase safe, as you'll need it to access your wallet."
                    except Exception as error:
                        status = "error"
                        mnemonic = None
                        message = "Internal error. Please contact hobbleabbas@gmail.com"
                        message = str(error)
            return {
                "status": status,
                "message": message,
                "mnemonic": mnemonic_words,
            }

        except:
            return "Connection error occured. Please try again later"
    else:
        return auth[1]

    cursor.close()
    conn.close()


@app.route('/retrieve_wallet', methods=['POST'])
def retrieve_wallet():
    '''
    @param name - STRING -  wallet's name
    @param username - STRING - user's set username
    @param password - STRING - user's set password
    @param export - BOOL - whether you want all details including privatekey
    @param mnemonic - STRING - To get full export you must provide your mnemonic
    '''

    # Get parameters
    data = request.get_json()
    try:
        username = data["username"]
        password = data["password"]
        name = data["name"]
    except KeyError as error:
        # tell user what parameter they are missing
        return parameter_error(error.args[0])


    auth = log_in(username, password)

    if auth[0]:

        try:
            # convert wallet name to a unique name with their id 
            user_id = auth[2][0]
            username = auth[2][2]
            wallet_name = user_id + '_' + str(name)

            # build a path with the specific wallet
            path = NODE_URL + "/wallet/" + wallet_name
            result = rpc("getwalletinfo", path = path)
            return {
                "status":"success",
                "wallet_details": result
            }
        except:
            return {
                "status": "error",
                "message": "Connection error occured. Please try again later"
            }
    else:
        return auth[1]

@app.route('/list_wallets', methods=['POST'])
def list_wallets():
    '''
    @param username - STRING - user's set username
    @param password - STRING - user's set password
    '''
    data = request.get_json()
    try:
        username = data["username"]
        password = data["password"]
        
    except KeyError as error:
        # tell user what parameter they are missing
        return parameter_error(error.args[0])

    auth = log_in(username, password)

    if auth[0]:
        try:
            result = rpc("listwallets")

            user_wallets = []

            for wallet in result:
                wallet_uuid = wallet[0:36]

                if wallet_uuid == auth[2][0]:
                    user_wallets.append(wallet[37:])

            if len(user_wallets) == 0:
                message = "You don't have any wallets. Create one with the create_wallet command."
            else:
                # Put together a message with the names of the wallets
                wallets_string  = ""

                for wallet in user_wallets:
                    wallets_string += " '" + wallet + "' "

                message = "You have " + str(len(user_wallets)) + " wallet(s) in your account. Your wallets: " + wallets_string

            return {
                "status": "success",
                "message": message,
                "number_of_wallets": len(user_wallets)
            }


        except Exception as error_message:
            save_error(error_message)
            error = "Connection error occured. Please try again later"
            return error
    else:
        return auth_error()

@app.route('/send_coins', methods=['POST'])
def send_coins():
    '''
    @param username - STRING - user's set username
    @param password - STRING - user's set password
    @param wallet - STRING - the wallet to send from
    @param amount - STRING - how much btc to send
    @param recipient_address - STRING - where to send the btc
    @param fees - BOOL - whether you want to pay fees or not
    '''

    data = request.get_json()
    try:
        username = data["username"]
        password = data["password"]
        wallet = data["wallet"]
        amount = float(data["amount"])
        recipient_address = data["recipient_address"]
        fees = data["fees"]

        if type(fees) != bool:
            return type_error('fees', 'boolean')

        if type(wallet) != str:
            return type_error('wallet', 'string')

        if type(recipient_address) != str:
            return type_error('recipient_address', 'string')

    except KeyError as error:
        # tell user what parameter they are missing
        return parameter_error(error.args[0])

    auth = log_in(username, password)

    if auth[0]:
        try:
            # convert wallet name to a unique name with their id
            user_id = auth[2][0]
            username = auth[2][2]
            wallet_name = user_id + '_' + wallet

            # build a path with the specific wallet
            path = NODE_URL + "/wallet/" + wallet_name
            result = rpc("sendtoaddress", params = [recipient_address, amount, "Transacted with the Bank of Bapu API", " ", fees, False], path=path)

            # Returning insufficient funds is bad practice, but handling parameter types means this is the most likely case
            # Send to address via rpc doesn't return an error it seems, though the cli does

            if result:
                return {
                    "status": "success",
                    "transaction_id": result
                }
            else:
                return {
                    "status": "error",
                    "message": "You likely have insufficient funds or passed in a mainnet address. To check your balance use the retrieve_wallet call"
                }


        except:
            error = "Connection error occured. Please try again later"
            return error
    else:
        return auth[1]

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)