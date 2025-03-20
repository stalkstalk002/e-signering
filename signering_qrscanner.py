import tkinter as tk
from tkinter import ttk
import numpy as np
import cv2
from threading import Thread
import time
import socketio
import mss


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


def scan_for_qr_codes(detector, frame):
    data, points, _ = detector.detectAndDecode(frame)
    if data:
        print("Detected QR Code Data:", data)
        return [{'data': data, 'points': points}]
    else:
        print("No Qr code detected")
        return []
    

def start_scanning(root, qr_status_label, server_status_label):
    global stop_scanning, scanned_data
    detector = cv2.QRCodeDetector()  
    with mss.mss() as sct:
        while not stop_scanning:
            try:
                x = root.winfo_x()
                y = root.winfo_y()
                width = root.winfo_width()
                height = root.winfo_height()
                
                monitor = {
                    'top': y,
                    'left': x,
                    'width': width,
                    'height': height
                    }
                screen_capture = np.array(sct.grab(monitor))
                screen_capture_rgb = cv2.cvtColor(
                    screen_capture,
                    cv2.COLOR_BGRA2RGB
                    )
                
                frame = cv2.resize(screen_capture_rgb, (320, 240))
                
                qr_codes = scan_for_qr_codes(detector, frame)
                
                if qr_codes:
                    scanned_data = {'data': qr_codes[0]['data']}
                    sio.emit('qr_code_scanned', scanned_data)
                    root.after(0, qr_status_label.config, {
                        'text': "QR Status: Detected",
                        'foreground': 'green',
                        'font': ('Segoe UI', 10, 'bold')
                        })
                else:
                    root.after(0, qr_status_label.config, {
                        'text': "QR Status: Not Detected",
                        'foreground': 'red'
                        })

                time.sleep(0.7) 

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

    root = tk.Tk()
    root.geometry("400x300")
    root.title("QR Scanner")
    root.configure(bg="#0080FE")
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    set_icon(root, r"D:\GH\qr_overlay\static\img\logo-bank-id_32x32.ico")

    control_panel = tk.Toplevel(root)
    control_panel.geometry("400x200")
    control_panel.title("Scanner Controls")
    control_panel.configure(bg="#F3F4F6")
    control_panel.attributes("-topmost", True)

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

    main_frame = ttk.Frame(control_panel, style="Modern.TFrame", padding="20")
    main_frame.pack(expand=True, fill="both")

    title = ttk.Label(main_frame, text="QR Code Scanner", style="Title.TLabel")
    title.pack(pady=(0, 5))

    subtitle = ttk.Label(main_frame, text="Move the blue overlay over a QR code", style="Subtitle.TLabel")
    subtitle.pack(pady=(0, 20))

    server_status_var = tk.StringVar(value="Server Status: Disconnected")
    server_status_label = ttk.Label(main_frame, textvariable=server_status_var, style="Subtitle.TLabel")
    server_status_label.pack(pady=(0, 10))

    qr_status_label = ttk.Label(main_frame, text="QR Status: Not Detected", style="Subtitle.TLabel", foreground="red")
    qr_status_label.pack(pady=(0, 10))

    button_frame = ttk.Frame(main_frame, style="Modern.TFrame")
    button_frame.pack(expand=True, fill="both")

    def align_windows(event=None):
        x = root.winfo_x()
        y = root.winfo_y() + root.winfo_height()
        control_panel.geometry(f"+{x}+{y}")
    
    root.bind("<Configure>", align_windows)

    def check_server_connection():
        if sio.connected:
            server_status_var.set("Server Status: Connected")
            server_status_label.config(foreground="green")
        else:
            server_status_var.set("Server Status: Disconnected, reopen app after 1 min")
            server_status_label.config(foreground="red")
        root.after(1000, check_server_connection)

    try:
        # sio.connect('https://signering.onrender.com/')
        # sio.connect('https://signer-y8ih.onrender.com/')
        sio.connect('http://127.0.0.1:5000/')
        server_status_var.set("Server Status: Connected")
        server_status_label.config(foreground="green")
    except Exception:
        server_status_var.set("Server is not connected, reopen app")
        server_status_label.config(foreground="red")

    scan_thread = Thread(
        target=start_scanning,
        args=(
            root,
            qr_status_label,
            server_status_label
            )
        )
    
    scan_thread.daemon = True
    scan_thread.start()

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