import tkinter as tk
from tkinter import ttk
import numpy as np
import cv2
from threading import Thread
import time
import socketio
import mss
import importlib.util

# Check if pyzbar is available, otherwise suggest installing it
pyzbar_available = importlib.util.find_spec("pyzbar") is not None
if not pyzbar_available:
    print("Note: For better QR code detection, install pyzbar: pip install pyzbar")
else:
    from pyzbar.pyzbar import decode as pyzbar_decode

sio = socketio.Client()

stop_scanning = False
scanned_data = {}


class ModernButton(tk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self["background"] = "#7C3AED"

    def on_leave(self, e):
        self['background'] = '#8B5CF6'


def enhance_qr_image(frame):
    """Apply image enhancements to improve QR code detection"""
    # Convert to grayscale if not already
    if len(frame.shape) > 2:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    else:
        gray = frame
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Apply morphological operations to clean up the image
    kernel = np.ones((3, 3), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
    
    return morph


def scan_for_qr_codes(frame):
    results = []
    detected = False
    detected_data = None
    
    # Try multiple methods to maximize detection chances
    
    # Method 1: OpenCV QR Detector
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(frame)
    if data:
        print("Detected QR Code Data (OpenCV):", data)
        results.append({'data': data, 'points': points, 'method': 'opencv'})
        detected = True
        detected_data = data
    
    # Try with enhanced image if standard detection fails
    if not detected:
        enhanced = enhance_qr_image(frame)
        data, points, _ = detector.detectAndDecode(enhanced)
        if data:
            print("Detected QR Code Data (OpenCV Enhanced):", data)
            results.append({'data': data, 'points': points, 'method': 'opencv_enhanced'})
            detected = True
            detected_data = data
    
    # Method 2: PyZBar (if available)
    if not detected and pyzbar_available:
        try:
            decoded_objects = pyzbar_decode(frame)
            for obj in decoded_objects:
                qr_data = obj.data.decode('utf-8')
                print("Detected QR Code Data (PyZBar):", qr_data)
                results.append({
                    'data': qr_data, 
                    'points': obj.polygon, 
                    'method': 'pyzbar'
                })
                detected = True
                detected_data = qr_data
                break
        except Exception as e:
            print(f"PyZBar detection error: {e}")
    
    # Method 3: Try OpenCV's WECHAT_QR detector if available (OpenCV 4.5.1+)
    if not detected:
        try:
            wechat_detector = cv2.wechat_qrcode_WeChatQRCode()
            data_list, points_list = wechat_detector.detectAndDecode(frame)
            if data_list and len(data_list) > 0 and data_list[0]:
                print("Detected QR Code Data (WeChatQR):", data_list[0])
                results.append({
                    'data': data_list[0], 
                    'points': points_list[0] if points_list else None, 
                    'method': 'wechat_qr'
                })
                detected = True
                detected_data = data_list[0]
        except (AttributeError, cv2.error) as e:
            # WeChatQR detector might not be available in all OpenCV builds
            pass
    
    # If still not detected, try with different scales
    if not detected:
        # Try with upscaled image
        upscaled = cv2.resize(frame, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        data, points, _ = detector.detectAndDecode(upscaled)
        if data:
            print("Detected QR Code Data (Upscaled):", data)
            results.append({'data': data, 'points': points, 'method': 'upscaled'})
            detected = True
            detected_data = data
    
    if results:
        print(f"Successfully detected QR code using method: {results[0]['method']}")
    else:
        print("No QR code detected with any method")
    
    return results


def start_scanning(root, qr_status_label, server_status_label, method_label):
    global stop_scanning, scanned_data
    
    with mss.mss() as sct:
        last_detection_time = 0
        last_detected_data = None
        
        while not stop_scanning:
            try:
                # Get the overlay window position
                x = root.winfo_x()
                y = root.winfo_y()
                width = root.winfo_width()
                height = root.winfo_height()
                
                # Define the capture area
                monitor = {
                    'top': y,
                    'left': x,
                    'width': width,
                    'height': height
                }
                
                # Capture the screen area
                screen_capture = np.array(sct.grab(monitor))
                screen_capture_rgb = cv2.cvtColor(
                    screen_capture,
                    cv2.COLOR_BGRA2RGB
                )
                
                # Process at multiple scales for better detection
                detected = False
                qr_codes = []
                
                # Try with original size
                frame = screen_capture_rgb
                qr_codes = scan_for_qr_codes(frame)
                
                if not qr_codes:
                    # Try with reduced size (might be faster and work better for some QR codes)
                    frame_resized = cv2.resize(screen_capture_rgb, (320, 240))
                    qr_codes = scan_for_qr_codes(frame_resized)
                
                # Process detection results
                if qr_codes:
                    detected = True
                    current_data = qr_codes[0]['data']
                    detection_method = qr_codes[0].get('method', 'unknown')
                    
                    # Only emit if it's a new QR code or hasn't been sent in the last 3 seconds
                    current_time = time.time()
                    if current_data != last_detected_data or (current_time - last_detection_time) > 3:
                        scanned_data = {'data': current_data}
                        sio.emit('qr_code_scanned', scanned_data)
                        last_detection_time = current_time
                        last_detected_data = current_data
                    
                    root.after(0, qr_status_label.config, {
                        'text': "QR Status: Detected",
                        'foreground': 'green',
                        'font': ('Segoe UI', 10, 'bold')
                    })
                    
                    root.after(0, method_label.config, {
                        'text': f"Method: {detection_method}",
                        'foreground': 'blue',
                        'font': ('Segoe UI', 9)
                    })
                else:
                    root.after(0, qr_status_label.config, {
                        'text': "QR Status: Not Detected",
                        'foreground': 'red'
                    })
                    
                    root.after(0, method_label.config, {
                        'text': "Method: none",
                        'foreground': 'gray',
                        'font': ('Segoe UI', 9)
                    })

                # Sleep to reduce CPU usage
                time.sleep(0.5)

            except Exception as e:
                print(f"Scanning error: {e}")
                time.sleep(1)


def create_overlay():
    global stop_scanning
    stop_scanning = False
    
    def set_icon(root, icon_path):
        try:
            root.iconbitmap(icon_path)
        except tk.TclError:
            print(f"Failed to set icon: {icon_path}")

    # Create the main overlay window
    root = tk.Tk()
    root.geometry("400x300")
    root.title("QR Scanner")
    root.configure(bg="#0080FE")
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    try:
        set_icon(root, r"D:\GH\qr_overlay\static\img\logo-bank-id_32x32.ico")
    except:
        pass  # If icon not found, continue without it

    # Create the control panel window
    control_panel = tk.Toplevel(root)
    control_panel.geometry("400x250")  # Made slightly larger for the additional info
    control_panel.title("Enhanced QR Scanner Controls")
    control_panel.configure(bg="#F3F4F6")
    control_panel.attributes("-topmost", True)

    # Configure styles
    style = ttk.Style()
    style.configure("Modern.TFrame", background="#F3F4F6")
    style.configure("Title.TLabel",
                    background="#F3F4F6",
                    foreground="#1F2937",
                    font=('Segoe UI', 14, 'bold'))
    style.configure("Subtitle.TLabel",
                    background="#F3F4F6",
                    foreground="#4B5563",
                    font=('Segoe UI', 10)
                    )

    # Create main frame in control panel
    main_frame = ttk.Frame(control_panel, style="Modern.TFrame", padding="20")
    main_frame.pack(expand=True, fill="both")

    # Add title and instructions
    title = ttk.Label(main_frame, text="Enhanced QR Code Scanner", style="Title.TLabel")
    title.pack(pady=(0, 5))

    subtitle = ttk.Label(main_frame, 
                         text="Move the blue overlay over a QR code", 
                         style="Subtitle.TLabel")
    subtitle.pack(pady=(0, 10))

    # Status indicators
    server_status_var = tk.StringVar(value="Server Status: Disconnected")
    server_status_label = ttk.Label(main_frame, 
                                   textvariable=server_status_var, 
                                   style="Subtitle.TLabel")
    server_status_label.pack(pady=(0, 5))

    qr_status_label = ttk.Label(main_frame, 
                               text="QR Status: Not Detected", 
                               style="Subtitle.TLabel", 
                               foreground="red")
    qr_status_label.pack(pady=(0, 5))
    
    method_label = ttk.Label(main_frame, 
                            text="Method: none", 
                            style="Subtitle.TLabel", 
                            foreground="gray")
    method_label.pack(pady=(0, 5))
    
    # Add info about supported formats
    info_label = ttk.Label(main_frame, 
                          text="Supports standard, colored, and logo QR codes", 
                          style="Subtitle.TLabel", 
                          foreground="#4B5563")
    info_label.pack(pady=(5, 5))

    # Create frame for buttons (for future use)
    button_frame = ttk.Frame(main_frame, style="Modern.TFrame")
    button_frame.pack(expand=True, fill="both")

    # Function to align the control panel below the overlay
    def align_windows(event=None):
        x = root.winfo_x()
        y = root.winfo_y() + root.winfo_height()
        control_panel.geometry(f"+{x}+{y}")
    
    root.bind("<Configure>", align_windows)

    # Function to check server connection status
    def check_server_connection():
        if sio.connected:
            server_status_var.set("Server Status: Connected")
            server_status_label.config(foreground="green")
        else:
            server_status_var.set("Server Status: Disconnected, reopen app after 1 min")
            server_status_label.config(foreground="red")
        root.after(1000, check_server_connection)

    # Connect to the server
    try:
        # Try to connect to the server (uncomment the appropriate line)
        # sio.connect('https://signering.onrender.com/')
        # sio.connect('https://signer-y8ih.onrender.com/')
        sio.connect('http://127.0.0.1:5000/')
        server_status_var.set("Server Status: Connected")
        server_status_label.config(foreground="green")
    except Exception:
        server_status_var.set("Server is not connected, reopen app")
        server_status_label.config(foreground="red")

    # Start scanning in a separate thread
    scan_thread = Thread(
        target=start_scanning,
        args=(
            root,
            qr_status_label,
            server_status_label,
            method_label
        )
    )
    
    scan_thread.daemon = True
    scan_thread.start()

    # Handle window closing
    def on_close():
        global stop_scanning
        stop_scanning = True
        try:
            sio.disconnect()
        except Exception:
            pass
        root.destroy()
        control_panel.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    control_panel.protocol("WM_DELETE_WINDOW", on_close)
    
    align_windows()
    check_server_connection()
    root.mainloop()


if __name__ == "__main__":
    create_overlay()