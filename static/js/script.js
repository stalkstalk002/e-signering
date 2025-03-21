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

// Store the BankID data
let bankIdData = {
    qrStartToken: '',
    sessionId: '',
    rawQrData: ''
};

// Debug logging function
function logDebug(message, data) {
    console.log(`[BankID Debug] ${message}`, data || '');
}

socket.on('update_qr_code_image', function (data) {
    qrImage.src = 'data:image/png;base64,' + data.qr_image;
    hidee.style.display = 'none';
    
    // Store all relevant QR data
    if (data.qr_code_data) {
        bankIdData.rawQrData = data.qr_code_data;
        logDebug("Received raw QR data:", bankIdData.rawQrData);
        
        // Parse the QR data for BankID format (bankid.token.time.authcode)
        const parts = data.qr_code_data.split('.');
        if (parts.length >= 4 && parts[0] === 'bankid') {
            bankIdData.qrStartToken = parts[1];
            logDebug("Extracted qrStartToken:", bankIdData.qrStartToken);
        }
    }
    
    // Store autostart token if available directly
    if (data.autostarttoken) {
        bankIdData.qrStartToken = data.autostarttoken;
        logDebug("Received autostarttoken:", bankIdData.qrStartToken);
    }
    
    // Store session ID if available
    if (data.session_id) {
        bankIdData.sessionId = data.session_id;
        logDebug("Received session ID:", bankIdData.sessionId);
    }
    
    // Create container for QR and button
    const qrContainer = document.createElement('div');
    qrContainer.className = 'qr-container';
    qrContainer.style.display = 'flex';
    qrContainer.style.flexDirection = 'column';
    qrContainer.style.alignItems = 'center';
    qrContainer.style.gap = '15px';
    
    // Make QR code a button for accessibility
    const qrButton = document.createElement('button');
    qrButton.className = 'qr-button';
    qrButton.style.background = 'none';
    qrButton.style.border = 'none';
    qrButton.style.padding = '0';
    qrButton.style.cursor = 'pointer';
    qrButton.style.display = 'block';
    qrButton.setAttribute('aria-label', 'BankID QR-kod. Klicka för att öppna i helskärm');
    
    // Add QR image to the button
    qrImage.style.display = 'block';
    qrImage.style.maxWidth = '200px';
    qrImage.style.margin = '0 auto';
    qrImage.alt = 'BankID QR-kod';
    
    qrButton.appendChild(qrImage);
    
    // Add QR button click handler for fullscreen
    qrButton.addEventListener('click', createFullscreenQrView);
    
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
    qrContainer.appendChild(qrButton);
    qrContainer.appendChild(continueButton);
    modalContent.appendChild(qrContainer);
    
    // Add countdown timer (accessibility improvement)
    const timerContainer = document.createElement('div');
    timerContainer.style.marginTop = '10px';
    timerContainer.style.textAlign = 'center';
    
    const timerText = document.createElement('p');
    timerText.textContent = 'QR-koden är giltig i: 30 sekunder';
    timerText.style.margin = '5px 0';
    timerText.setAttribute('role', 'timer');
    timerText.setAttribute('aria-live', 'polite');
    
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
        timerText.style.color = '';
        
        // Create a notification for screen readers
        const notification = document.createElement('div');
        notification.setAttribute('aria-live', 'assertive');
        notification.style.position = 'absolute';
        notification.style.clip = 'rect(0 0 0 0)';
        notification.textContent = 'Sessionen har förlängts med 30 sekunder';
        document.body.appendChild(notification);
        
        // Remove the notification after it's been read
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
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
    
    // Start QR animation (update every second)
    if (bankIdData.sessionId) {
        // Start the animation immediately
        socket.emit('start_qr_animation', { session_id: bankIdData.sessionId });
        
        // Then update every second
        const animationInterval = setInterval(function() {
            if (timeLeft <= 0) {
                clearInterval(animationInterval);
                return;
            }
            socket.emit('start_qr_animation', { session_id: bankIdData.sessionId });
        }, 1000);
    }
});

function createFullscreenQrView() {
    // Create fullscreen modal for QR code (accessibility enhancement)
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
    fullscreenModal.setAttribute('role', 'dialog');
    fullscreenModal.setAttribute('aria-label', 'Förstora QR-kod');
    
    // Create larger QR image for fullscreen view
    const fullscreenQR = document.createElement('img');
    fullscreenQR.src = qrImage.src;
    fullscreenQR.style.maxWidth = '80%';
    fullscreenQR.style.maxHeight = '80%';
    fullscreenQR.alt = 'Förstorad BankID QR-kod';
    
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
    
    // Allow closing with ESC key for better accessibility
    fullscreenModal.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.body.removeChild(fullscreenModal);
        }
    });
    
    // Focus on the close button for keyboard users
    closeButton.focus();
}

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
    confirmDialog.setAttribute('role', 'dialog');
    confirmDialog.setAttribute('aria-labelledby', 'dialogTitle');
    
    confirmDialog.innerHTML = `
        <h3 id="dialogTitle" style="margin-top: 0; color: #007aff;">Öppna BankID-appen</h3>
        <p>Vill du öppna BankID-appen för att fortsätta?</p>
        <div style="display: flex; justify-content: center; gap: 10px; margin-top: 20px;">
            <button id="cancelOpenBankID" style="padding: 8px 16px; background-color: #f1f1f1; border: none; border-radius: 4px; cursor: pointer;">Avbryt</button>
            <button id="confirmOpenBankID" style="padding: 8px 16px; background-color: #007aff; color: white; border: none; border-radius: 4px; cursor: pointer;">Öppna</button>
        </div>
    `;
    
    document.body.appendChild(confirmDialog);
    
    // Focus the confirm button for keyboard users
    setTimeout(() => {
        document.getElementById('confirmOpenBankID').focus();
    }, 100);
    
    // Allow closing with ESC key for better accessibility
    confirmDialog.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.body.removeChild(confirmDialog);
        }
    });
    
    // Handle cancel button
    document.getElementById('cancelOpenBankID').addEventListener('click', function() {
        document.body.removeChild(confirmDialog);
    });
    
    // Handle confirm button
    document.getElementById('confirmOpenBankID').addEventListener('click', function() {
        document.body.removeChild(confirmDialog);
        
        // Get the most recent QR code data
        socket.emit('request_fresh_qr_data');
        
        if (bankIdData.qrStartToken) {
            logDebug("Opening BankID app with token:", bankIdData.qrStartToken);
            
            // Create current URL to use as return URL
            const currentUrl = window.location.href;
            // Add a nonce to handle session matching
            const nonce = Date.now().toString(36) + Math.random().toString(36).substring(2);
            // Store nonce in sessionStorage for validation when returning
            sessionStorage.setItem('bankid_nonce', nonce);
            
            // Create return URL with nonce in fragment
            const baseReturnUrl = currentUrl.split('#')[0];
            const returnUrl = `${baseReturnUrl}#nonce=${nonce}`;
            
            let bankidUrl = '';
            
            // Handle different URL formats based on platform
            if (isMobile) {
                // For mobile devices (iOS and Android), use universal/app links
                // Use 'null' as redirect to ensure the app behind it comes into focus after completion
                bankidUrl = `https://app.bankid.com/?autostarttoken=${bankIdData.qrStartToken}&redirect=null`;
                logDebug("Using mobile universal/app link:", bankidUrl);
            } else {
                // For desktop, use bankid:// protocol
                bankidUrl = `bankid:///?autostarttoken=${bankIdData.qrStartToken}`;
                logDebug("Using desktop protocol:", bankidUrl);
            }
            
            // Open the BankID app
            window.location.href = bankidUrl;
            
            // As a fallback, after a delay, show a message and offer to install the app
            setTimeout(function() {
                // Check if we're still on the same page (user hasn't been redirected)
                const dialogElement = document.createElement('div');
                dialogElement.className = 'bankid-fallback-dialog';
                dialogElement.style.position = 'fixed';
                dialogElement.style.top = '50%';
                dialogElement.style.left = '50%';
                dialogElement.style.transform = 'translate(-50%, -50%)';
                dialogElement.style.backgroundColor = 'white';
                dialogElement.style.padding = '20px';
                dialogElement.style.borderRadius = '8px';
                dialogElement.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                dialogElement.style.zIndex = '1000';
                dialogElement.style.maxWidth = '80%';
                dialogElement.style.textAlign = 'center';
                dialogElement.setAttribute('role', 'dialog');
                dialogElement.setAttribute('aria-labelledby', 'fallbackTitle');
                
                dialogElement.innerHTML = `
                    <h3 id="fallbackTitle" style="margin-top: 0; color: #007aff;">BankID-appen kunde inte öppnas</h3>
                    <p>BankID-appen verkar inte vara installerad eller kunde inte öppnas korrekt.</p>
                    <div style="display: flex; justify-content: center; gap: 10px; margin-top: 20px;">
                        <button id="dismissFallback" style="padding: 8px 16px; background-color: #f1f1f1; border: none; border-radius: 4px; cursor: pointer;">Avbryt</button>
                        <button id="installBankID" style="padding: 8px 16px; background-color: #007aff; color: white; border: none; border-radius: 4px; cursor: pointer;">Installera BankID</button>
                    </div>
                `;
                
                document.body.appendChild(dialogElement);
                
                // Focus the install button for keyboard users
                setTimeout(() => {
                    document.getElementById('installBankID').focus();
                }, 100);
                
                // Dismiss button handler
                document.getElementById('dismissFallback').addEventListener('click', function() {
                    document.body.removeChild(dialogElement);
                });
                
                // Install button handler
                document.getElementById('installBankID').addEventListener('click', function() {
                    if (isIOS) {
                        window.location.href = 'https://apps.apple.com/se/app/bankid-s%C3%A4kerhetsapp/id433151512';
                    } else if (isAndroid) {
                        window.location.href = 'https://play.google.com/store/apps/details?id=com.bankid.bus';
                    } else {
                        window.location.href = 'https://install.bankid.com/';
                    }
                    document.body.removeChild(dialogElement);
                });
                
                // Allow closing with ESC key
                dialogElement.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        document.body.removeChild(dialogElement);
                    }
                });
            }, 3000);
        } else {
            // If we don't have a token, show an error message
            const errorDialog = document.createElement('div');
            errorDialog.style.position = 'fixed';
            errorDialog.style.top = '50%';
            errorDialog.style.left = '50%';
            errorDialog.style.transform = 'translate(-50%, -50%)';
            errorDialog.style.backgroundColor = 'white';
            errorDialog.style.padding = '20px';
            errorDialog.style.borderRadius = '8px';
            errorDialog.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            errorDialog.style.zIndex = '1000';
            errorDialog.style.maxWidth = '80%';
            errorDialog.style.textAlign = 'center';
            
            errorDialog.innerHTML = `
                <h3 style="margin-top: 0; color: #ff3b30;">Fel</h3>
                <p>Ingen BankID-data tillgänglig. Var god skanna QR-koden igen.</p>
                <button id="closeErrorDialog" style="padding: 8px 16px; background-color: #007aff; color: white; border: none; border-radius: 4px; cursor: pointer; margin-top: 15px;">Stäng</button>
            `;
            
            document.body.appendChild(errorDialog);
            
            document.getElementById('closeErrorDialog').addEventListener('click', function() {
                document.body.removeChild(errorDialog);
            });
        }
    });
}

// Handle window hash change (for returning from BankID app)
window.addEventListener('hashchange', function() {
    // Check if we have a nonce in the URL fragment
    const urlHash = window.location.hash;
    if (urlHash.includes('nonce=')) {
        const returnedNonce = urlHash.split('nonce=')[1];
        const storedNonce = sessionStorage.getItem('bankid_nonce');
        
        if (returnedNonce === storedNonce) {
            // Valid return from BankID
            logDebug("Valid return from BankID detected with matching nonce");
            sessionStorage.removeItem('bankid_nonce'); // Clean up
            
            // Show success message or continue with verification
            const successNotification = document.createElement('div');
            successNotification.style.position = 'fixed';
            successNotification.style.top = '20px';
            successNotification.style.left = '50%';
            successNotification.style.transform = 'translateX(-50%)';
            successNotification.style.backgroundColor = '#4cd964';
            successNotification.style.color = 'white';
            successNotification.style.padding = '10px 20px';
            successNotification.style.borderRadius = '4px';
            successNotification.style.zIndex = '1000';
            successNotification.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
            successNotification.textContent = 'Återvänt från BankID-appen. Verifierar identifiering...';
            successNotification.setAttribute('role', 'status');
            successNotification.setAttribute('aria-live', 'polite');
            
            document.body.appendChild(successNotification);
            
            // Remove the hash from the URL without reloading the page
            history.replaceState(null, document.title, window.location.pathname + window.location.search);
            
            // Remove notification after a few seconds
            setTimeout(function() {
                document.body.removeChild(successNotification);
            }, 3000);
        }
    }
});

// Request QR data from server on page load
socket.emit('request_qr_data');

// Handle QR token data from server
socket.on('qr_data', function(data) {
    if (data && data.qrData) {
        bankIdData.qrStartToken = data.qrData;
        logDebug("Received QR token:", bankIdData.qrStartToken);
    }
    
    if (data && data.session_id) {
        bankIdData.sessionId = data.session_id;
        logDebug("Received session ID from qr_data:", bankIdData.sessionId);
    }
});

// Handle BankID token from server if it uses the new format
socket.on('bankid_token', function(data) {
    if (data && data.token) {
        bankIdData.qrStartToken = data.token;
        logDebug("Received bankid_token:", bankIdData.qrStartToken);
    }
});