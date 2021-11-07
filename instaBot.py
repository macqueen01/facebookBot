from flask import Flask, request
from flask.globals import current_app
import requests
import sqlalchemy
from sqlalchemy import create_engine, text



app = Flask(__name__)
app.config.from_pyfile("config.py")
db = create_engine(app.config['DB_URL'], encoding='utf-8', max_overflow=0)
app.database = db

FB_API_URL = 'https://graph.facebook.com/v2.6/me/messages'
VERIFY_TOKEN='JAE_KIM'
PAGE_ACCESS_TOKEN='EAAGXAu5Gu5gBAHhCXYv9uLSmu8aY60rawtJ9xzhNdtRGtZAvZA5Gpna6pQo5MKujpWYqxpsCPv6nTGH02Qd3T7IA2UGjnyl2pKZCEHoWIIRlUXH91zwM8azsnoHKzzj8RrhTy4QB9HcvTuwZCI43siiqREqPT5GeMfEy74WkLAp34OcHvNC9'
def send_message(recipient_id, text):
    """Send a response to Facebook"""
    payload = {
        'message': {
            'text': text
        },
        'recipient': {
            'id': recipient_id
        },
        'notification_type': 'regular'
    }

    auth = {
        'access_token': PAGE_ACCESS_TOKEN
    }

    response = requests.post(
        FB_API_URL,
        params=auth,
        json=payload
    )

    return response.json()

def get_bot_response(message):
    """This is just a dummy function, returning a variation of what
    the user said. Replace this function with one connected to chatbot."""
    return "This is a dummy response to '{}'".format(message)


def verify_webhook(req):
    if req.args.get("hub.verify_token") == VERIFY_TOKEN:
        return req.args.get("hub.challenge")
    else:
        return "incorrect"

def respond(sender, message):
    """Formulate a response to the user and
    pass it on to a function that sends it."""
    response = get_bot_response(message)
    send_message(sender, response)


def is_user_message(message):
    """Check if the message is a message from the user"""
    return (message.get('message') and
            message['message'].get('text') and
            not message['message'].get("is_echo"))


@app.route("/webhook", methods=['GET'])
def listen():
    """This is the main function flask uses to
    listen at the `/webhook` endpoint"""
    if request.method == 'GET':
        return verify_webhook(request)

@app.route("/webhook", methods=['POST'])
def talk():
    payload = request.get_json()
    event = payload['entry'][0]['messaging']
    for x in event:
        if is_user_message(x):
            contents = x['message']['text'].__str__()
            sender_id = x['sender']['id']

            # get all the senders from the 'senders' table

            senders = current_app.database.execute(text("""
            SELECT * FROM senders
            """),{}).fetchall()

            # send "This message should be longer that 100 letters and shorter than 1500 letters" if the message is not in the range
            if len(contents) < 100 or len(contents) > 1500:
                send_message(sender_id, "This message should be longer that 100 letters and shorter than 1500 letters")

            else:
                if sender_id not in [sender['id'] for sender in senders]:
                    current_app.database.execute(text("""
                    INSERT INTO senders (id, numSends)
                    VALUES (:id, :numSends)
                    """), {'id': sender_id, 'numSends': 1})
                else:
                    current_app.database.execute(text("""
                    UPDATE senders
                    SET numSends = numSends + 1
                    WHERE id = :id
                    """), {'id': sender_id})


                # add the message from the sender to 'messages' table
                current_app.database.execute(text("""
                INSERT INTO messages (
                    id,
                    message
                ) VALUES (
                    :sender_id,
                    :text
                )"""), {'sender_id' : sender_id, 'text' : contents})

            respond(sender_id, contents)

    return "ok"

@app.route('/')
def hello():
    return 'hello'

if __name__ == '__main__':
    app.run(threaded=True, port=5000)

