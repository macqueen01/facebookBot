from flask import Flask, request, render_template
from flask.globals import current_app
import requests
import sqlalchemy
from sqlalchemy import create_engine, text



app = Flask(__name__)
app.config.from_pyfile("config.py")
db = create_engine(app.config['DB_URL'], encoding='utf-8', max_overflow=0)
app.database = db

FB_API_URL = 'https://graph.facebook.com/v2.6/me/messages'
VERIFY_TOKEN=app.config['VERIFY_TOKEN']
PAGE_ACCESS_TOKEN=app.config['PAGE_ACCESS_TOKEN']


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

def askName():
    return "편지가 거의 전송됐어 ! 이름을 알려 줄 수 있겠어 ? \n  '!이름 : 홍길동' \n 형식으로 적어주면 돼 !"

def askAddress():
    return "편지 보내줘서 너무 고마워 ! 집 주소를 알려주면 내가 답장을 보낼 수 있을거 같아... 주소를 알려줄 수 있어 ? \n '!주소 : 나의(도) 마음(시) 속(마을)' \n 형식으로 적어주면 쇽샥쇽샥 답장 써줄게 ! 곤란하다고 느껴지면 \n '!싫은데' \n 로 답해줘 !"

def sadRespond():
    return "ㅠㅠㅠ 알겠어... 난 서운하지 않아 ! 언제든지 주소를 알려주면 바로 답장할 할게. \n '!주소 : 나의(시) 마음(도) 속(마을)' \n 형식으로 적어주면 쇽샥쇽샥 답장 써줄게 !"

def happyRespond():
    return "방금 우체부에게 답장을 전해줬어. 눈 깜빡하는 순간 너의 집앞에 내 답장이 ! ㅎㅎㅎ"

def addressButNotLetter():
    return "편지를 먼저 보내줄 수 있어 ? 편지를 보낸 다음 주소를 보내주면 고마울거 같아 !"


def verify_webhook(req):
    if req.args.get("hub.verify_token") == VERIFY_TOKEN:
        return req.args.get("hub.challenge")
    else:
        return "incorrect"

def casualRespond(sender, emotion):
    """Formulate a response to the user and
    pass it on to a function that sends it."""
    if emotion == 'askAddr':
        response = askAddress()
    elif emotion == 'askName':
        response = askName()
    elif emotion == 'sad':
        response = sadRespond()
    elif emotion == 'happy':
        response = happyRespond()
    elif emotion == 'addressFirst':
        response = addressButNotLetter()
    return send_message(sender, response)


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

            if '!싫은데' in contents.split() or '!싫은데' in contents:
                return casualRespond(sender_id, 'sad')
                
            # get all the senders from the 'senders' table

            senders = current_app.database.execute(text("""
            SELECT * FROM senders
            """),{}).fetchall()

            # When user sends '!이름 : 홍길동' format

            if '!이름' in contents.split() or '!이름' in contents:
                if sender_id in [sender['id'] for sender in senders]:
                    if None == [sender['name'] for sender in senders if sender['id'] == sender_id][0]:
                        current_app.database.execute(text("""
                        UPDATE senders SET name = :name WHERE id = :id"""),{'name': contents, 'id': sender_id})
                        return send_message(sender_id, "이름 접수 완료 ! " + askAddress())
                    else:
                        if None == [sender['address'] for sender in senders if sender['id'] == sender_id][0]:
                            return send_message(sender_id, '이미 아는 이름이야 ! ' + askAddress())
                        return send_message(sender_id, '이미 아는 이름이야 ! 편지 써줘서 고마워 !')
                else:
                    return send_message(sender_id, '편지를 쓰지 않은것 같아 ! 먼저 편지를 써줄 수 있겠어 ?')

            # When user sends '!주소 : 나의(시) 마음(도) 속(마을)' format

            if '!주소' in contents.split() or '!주소' in contents:
                if sender_id in [sender['id'] for sender in senders]:
                    if [sender['address'] for sender in senders if sender['id'] == sender_id][0] is not None:
                        return send_message(sender_id, '이미 주소를 알고 있어 ! 편지 써줘서 고마워 !')
                    current_app.database.execute(text("""
                    UPDATE senders SET address = :address WHERE id = :id"""),{'address': contents, 'id': sender_id})
                    return casualRespond(sender_id, 'happy')
                else:
                    return casualRespond(sender_id, 'addressFirst')

            # send "This message should be longer that 100 letters and shorter than 1500 letters" if the message is not in the range

            if len(contents) < 100 or len(contents) > 1500:
                return send_message(sender_id, "편지는 최소한 100 자 이상, 1500자 이하까지만 보내질 수 있어. 미안... 더 길게 쓰거나 더 짧게 써줄 수 있어 ?")

            # message is in the range, and asks name and address in order (There could be null name and address, but name is recommended)
            
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

                if [sender['name'] for sender in senders if sender['id']==sender_id][0] is not None:
                    if [sender['address'] for sender in senders if sender['id']==sender_id][0] is not None:
                        return casualRespond(sender_id, 'happy')
                    else:
                        return casualRespond(sender_id, 'askAddr')
                else:
                    return casualRespond(sender_id, 'askName')

    return "ok"

@app.route('/')
def hello():
    return """<!DOCTYPE html>
<html>
<head>
<title>개인정보 처리 방침 (재우에게 인편을)</title>
</head>
<body>
<div class="container">
<div class="header">
<h1>Use of Personal Information</h1>
<h3> <strong>Mocking_Jae</strong> 에 인편과 주소, 그리고 이름을 보내주셨다면,<br/>
     이 데이터들은 데이터베이스에 하루동안 저장되어 있다가 그날 재우에게 전달됩니다.<br/>
    앱 상에서 벌어진 버그들 때문에 전달되지 못한 편지들은 모두 데이터베이스에만 저장됩니다.<br/>
    재우가 훈련소를 수료하고 나면 이 개인정보들은 모두 데이터베이스 상에서 소멸할 예정이며, 데이터들과 함께 <br/>
    데이터가 머물렀던 데이터베이스도 모두 소멸될 예정입니다. </h3>
</div>
<div class="content">
</body>
</html>"""

if __name__ == '__main__':
    app.run(threaded=True, port=5000)

