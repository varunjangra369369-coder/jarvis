import os
import re
import shutil
import base64
import datetime
from flask import Flask, render_template_string, request, jsonify, send_file

app = Flask(__name__)

# --- SYSTEM CONFIGURATION ---
if os.path.exists('/storage/emulated/0/'):
    BASE_DIR = '/storage/emulated/0/'  # Android Storage
else:
    BASE_DIR = os.path.expanduser('~') # PC/Mac

CURRENT_DIR = BASE_DIR
PENDING_DELETE = None 

# --- ANDROID RUNTIME PERMISSIONS (Using safe PyJnius) ---
def request_android_permissions():
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        
        # Regular storage & media permissions (Android 13+ compatibility)
        permissions = [
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_IMAGES",
            "android.permission.READ_MEDIA_VIDEO",
            "android.permission.READ_MEDIA_AUDIO"
        ]
        
        # Request standard runtime permissions
        activity.requestPermissions(permissions, 101)
        
        # Request All Files Access (MANAGE_EXTERNAL_STORAGE) if on Android 11+ (API 30+)
        Build = autoclass("android.os.Build")
        if Build.VERSION.SDK_INT >= 30:
            Environment = autoclass("android.os.Environment")
            if not Environment.isExternalStorageManager():
                Intent = autoclass("android.content.Intent")
                Settings = autoclass("android.provider.Settings")
                Uri = autoclass("android.net.Uri")
                
                try:
                    # Direct user to toggle "Allow access to manage all files" for this specific app
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    intent.setData(Uri.parse(f"package:{activity.getPackageName()}"))
                    activity.startActivity(intent)
                except Exception:
                    # Fallback to the general settings manager page
                    intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    activity.startActivity(intent)
    except Exception as e:
        print("Android native permission request skipped/failed:", e)

# --- SAFE PATH ENCODING ---
def safe_encode(path):
    return base64.b64encode(path.encode('utf-8')).decode('utf-8')

def safe_decode(b64_str):
    return base64.b64decode(b64_str.encode('utf-8')).decode('utf-8')

# --- FILE SYSTEM ENGINES WITH SECURITY SHIELDS ---
def get_dir_contents(path):
    try:
        items = os.listdir(path)
        folders = [f for f in items if os.path.isdir(os.path.join(path, f))]
        files = [f for f in items if os.path.isfile(os.path.join(path, f))]
        return sorted(folders), sorted(files)
    except Exception:
        return [], []

def global_search(target, filter_exts=None, limit=40):
    results = []
    target = target.lower()
    try:
        for root, dirs, files in os.walk(BASE_DIR):
            if '/Android/data' in root or '/.' in root: continue 
            
            if not filter_exts:
                for d in dirs:
                    if target in d.lower(): results.append(os.path.join(root, d))
                    
            for f in files:
                if target in f.lower() or (filter_exts and any(f.lower().endswith(ext) for ext in filter_exts)):
                    if filter_exts and target == "" and not any(f.lower().endswith(ext) for ext in filter_exts): continue
                    if target in f.lower() or target == "": results.append(os.path.join(root, f))
                    
            if len(results) >= limit: break 
    except Exception:
        pass  
    return results

def smart_jump_search(target):
    target = target.lower().replace('s', '') 
    try:
        for d in os.listdir(CURRENT_DIR):
            if os.path.isdir(os.path.join(CURRENT_DIR, d)) and target in d.lower().replace('s', ''):
                return os.path.join(CURRENT_DIR, d)
        for root, dirs, files in os.walk(BASE_DIR):
            if '/Android/data' in root or '/.' in root: continue
            for d in dirs:
                if target == d.lower().replace('s', ''):
                    return os.path.join(root, d)
    except Exception:
        pass
    return None

def extract_pdf_text(filepath):
    try:
        import PyPDF2
        with open(filepath, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            return " ".join([page.extract_text() for page in pdf.pages if page.extract_text()]).lower()
    except ImportError: return "MISSING_MODULE"
    except Exception: return ""

def deep_content_search(word, pdf_only=False):
    results = []
    word = word.lower()
    valid_text_exts = ['.txt', '.py', '.js', '.html', '.css', '.json', '.md', '.csv']
    missing_module = False

    try:
        for root, dirs, files in os.walk(BASE_DIR):
            if '/Android/data' in root or '/.' in root: continue
            for f in files:
                filepath = os.path.join(root, f)
                try:
                    if pdf_only and f.lower().endswith('.pdf'):
                        content = extract_pdf_text(filepath)
                        if content == "MISSING_MODULE": missing_module = True
                        elif word in content: results.append(filepath)
                    elif not pdf_only and any(f.endswith(ext) for ext in valid_text_exts):
                        if os.path.getsize(filepath) < 2 * 1024 * 1024: 
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as doc:
                                if word in doc.read().lower(): results.append(filepath)
                except Exception:
                    pass
                if len(results) >= 20: return results, missing_module
    except Exception:
        pass
    return results, missing_module

# --- HTML & JAVASCRIPT ---
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
    <title>J.A.R.V.I.S. Core OS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #030712; }
        ::-webkit-scrollbar-thumb { background: rgba(0, 212, 255, 0.5); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #00d4ff; }

        body { background: radial-gradient(circle at top, #0a1128 0%, #030712 100%); color: #00d4ff; font-family: 'Consolas', 'Courier New', monospace; text-align: center; padding: 15px; margin: 0; min-height: 100vh; overflow-x: hidden; }
        h1 { letter-spacing: 8px; text-shadow: 0 0 15px #00d4ff, 0 0 30px #00d4ff; margin-top: 5px; font-size: 2em; font-weight: 900; }
        
        .circle { width: 85px; height: 85px; border: 2px solid #00d4ff; border-radius: 50%; margin: 15px auto; box-shadow: 0 0 20px rgba(0,212,255,0.4), inset 0 0 20px rgba(0,212,255,0.2); animation: pulse 2.5s infinite; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.3s ease; background: rgba(0, 212, 255, 0.05); backdrop-filter: blur(5px); }
        .circle:hover { transform: scale(1.1); box-shadow: 0 0 40px #00d4ff, inset 0 0 30px #00d4ff; background: rgba(0, 212, 255, 0.15); }
        .circle span { font-weight: bold; font-size: 0.85em; letter-spacing: 2px; text-shadow: 0 0 5px #00d4ff; }
        @keyframes pulse { 0% { box-shadow: 0 0 10px rgba(0,212,255,0.4); } 50% { box-shadow: 0 0 35px rgba(0,212,255,0.8); } 100% { box-shadow: 0 0 10px rgba(0,212,255,0.4); } }
        
        #chat-box { height: 45vh; overflow-y: auto; padding: 15px; margin-bottom: 20px; text-align: left; background: rgba(3, 7, 18, 0.7); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 12px; font-size: 0.95em; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); backdrop-filter: blur(8px); display: flex; flex-direction: column; gap: 10px; }
        .msg-container { width: 100%; display: flex; flex-direction: column; }
        .msg-container.user { align-items: flex-end; }
        .msg-container.jarvis { align-items: flex-start; }
        .msg-container.system { align-items: center; }
        
        .bubble { max-width: 85%; padding: 10px 15px; border-radius: 8px; line-height: 1.4; word-wrap: break-word; }
        .bubble-user { background: rgba(255, 255, 255, 0.1); color: #fff; border-bottom-right-radius: 0; border: 1px solid rgba(255,255,255,0.2); }
        .bubble-jarvis { background: rgba(0, 212, 255, 0.1); color: #00d4ff; border-bottom-left-radius: 0; border: 1px solid rgba(0,212,255,0.3); box-shadow: 0 0 10px rgba(0,212,255,0.1); }
        .bubble-warning { background: rgba(255, 51, 51, 0.1); color: #ff3333; border: 1px solid #ff3333; box-shadow: 0 0 10px rgba(255,51,51,0.2); animation: pulse-warn 1.5s infinite; }
        @keyframes pulse-warn { 50% { box-shadow: 0 0 20px rgba(255,51,51,0.5); } }

        .sys-box { width: 100%; background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(0, 212, 255, 0.4); padding: 15px; border-radius: 8px; margin-top: 5px; box-sizing: border-box; box-shadow: inset 0 0 20px rgba(0,212,255,0.05); }
        .path-header { color: #888; font-size: 0.85em; margin-bottom: 12px; word-wrap: break-word; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px;}
        
        .item-row { display: flex; align-items: center; padding: 8px; border-radius: 6px; transition: all 0.2s ease; margin-bottom: 2px; }
        .item-row:hover { background: rgba(0, 212, 255, 0.1); transform: translateX(5px); border-left: 3px solid #00d4ff; }
        .item-name { cursor: pointer; text-decoration: none; display: flex; align-items: center; gap: 12px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.95em; }
        .rich-thumb { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; border: 1px solid rgba(0,212,255,0.5); transition: 0.3s;}
        
        .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 10px; padding: 5px; }
        .gallery-item { position: relative; cursor: pointer; aspect-ratio: 1; border-radius: 8px; overflow: hidden; border: 1px solid rgba(0,212,255,0.3); transition: 0.3s; box-shadow: 0 0 10px rgba(0,0,0,0.5); }
        .gallery-item:hover { transform: scale(1.08); border-color: #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.8); z-index: 10; }
        .gallery-img { width: 100%; height: 100%; object-fit: cover; }

        .color-folder { color: #f4c20d; font-weight: bold; }
        .color-img { color: #00ffaa; }
        .color-txt { color: #aaaaaa; }
        .color-pdf { color: #ff4444; font-weight: bold; }
        .color-def { color: #00d4ff; }
        
        .back-link { color: #ff00ff; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; margin-bottom: 15px; font-weight: bold; transition: 0.2s; padding: 5px 10px; background: rgba(255,0,255,0.1); border-radius: 5px; border: 1px solid rgba(255,0,255,0.3); }
        .back-link:hover { background: rgba(255,0,255,0.2); box-shadow: 0 0 10px rgba(255,0,255,0.4); }
        
        .input-area { display: flex; gap: 8px; justify-content: center; width: 100%; max-width: 700px; margin: auto; }
        input[type="text"] { flex: 1; background: rgba(0,0,0,0.5); border: 1px solid #00d4ff; color: white; padding: 12px 15px; border-radius: 8px; outline: none; transition: 0.3s; font-family: inherit; font-size: 1em; }
        input[type="text"]:focus { box-shadow: 0 0 15px rgba(0,212,255,0.3); background: rgba(0, 0, 0, 0.8); }
        .btn { background: linear-gradient(135deg, #00d4ff 0%, #0077ff 100%); color: #000; border: none; padding: 12px 20px; cursor: pointer; font-weight: 900; border-radius: 8px; transition: 0.3s; text-transform: uppercase; letter-spacing: 1px; }
        .btn:hover { box-shadow: 0 0 20px rgba(0,212,255,0.6); transform: translateY(-2px); }
        
        #status { font-size: 0.8em; color: #555; margin-top: 15px; letter-spacing: 2px; text-transform: uppercase; }

        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(3, 7, 18, 0.95); z-index: 1000; flex-direction: column; align-items: center; justify-content: center; padding: 20px; box-sizing: border-box; backdrop-filter: blur(10px); }
        .modal-content { width: 100%; max-width: 900px; background: rgba(10, 10, 10, 0.9); border: 1px solid #00d4ff; padding: 20px; border-radius: 12px; display: flex; flex-direction: column; box-shadow: 0 0 50px rgba(0,212,255,0.1); }
        .close-x { color: #ff3333; position: absolute; right: 20px; top: 15px; font-size: 35px; cursor: pointer; font-weight: bold; transition: 0.2s; z-index: 1001; text-shadow: 0 0 10px rgba(255,51,51,0.5);}
        .close-x:hover { text-shadow: 0 0 20px #ff3333; transform: scale(1.1); }
        
        textarea { width: 100%; height: 60vh; background: #050505; color: #00ff00; border: 1px solid rgba(0,212,255,0.3); padding: 15px; font-family: monospace; resize: none; box-sizing: border-box; border-radius: 8px; font-size: 14px;}
        textarea:focus { outline: none; border-color: #00d4ff; box-shadow: inset 0 0 10px rgba(0,212,255,0.1); }
        
        canvas { max-width: 100%; max-height: 60vh; border: 1px solid rgba(0,212,255,0.5); background: #000; touch-action: none; align-self: center; border-radius: 8px; box-shadow: 0 0 20px rgba(0,212,255,0.2);}
        
        #lightboxModal .modal-content { background: transparent; border: none; box-shadow: none; align-items: center; max-width: 100vw; justify-content: center; padding: 0;}
        #lightbox-img { max-width: 95vw; max-height: 80vh; object-fit: contain; border-radius: 8px; box-shadow: 0 0 40px rgba(0,212,255,0.5); border: 1px solid #00d4ff; }
        
        .toolbar { display: flex; gap: 10px; margin-top: 15px; justify-content: center; flex-wrap: wrap;}
    </style>
</head>
<body>
    <h1>J.A.R.V.I.S.</h1>
    <div class="circle" id="mic-btn"><span>LISTEN</span></div>
    <div id="chat-box"></div>
    
    <div class="input-area">
        <input type="text" id="user-input" placeholder="Awaiting command..." autocomplete="off" onkeypress="if(event.key==='Enter') sendText()">
        <button class="btn" onclick="sendText()">SEND</button>
    </div>
    <div id="status">System: Online & Secure</div>

    <div id="lightboxModal" class="modal">
        <span class="close-x" onclick="closeModal('lightboxModal')">&times;</span>
        <div class="modal-content">
            <img id="lightbox-img" src="">
            <div class="toolbar" style="margin-top: 25px;">
                <button class="btn" style="background: linear-gradient(135deg, #f4c20d, #ff9900);" onclick="openEditorFromLightbox()">🎨 Open Editor</button>
            </div>
        </div>
    </div>

    <div id="textModal" class="modal">
        <div class="modal-content" style="position: relative;">
            <span class="close-x" onclick="closeModal('textModal')">&times;</span>
            <h3 style="margin:0 0 15px 0; color:#00d4ff; text-align:left; letter-spacing:1px;">📝 Code / Text Editor</h3>
            <input type="hidden" id="edit-path">
            <textarea id="edit-content"></textarea>
            <div class="toolbar">
                <button class="btn" onclick="saveTextFile()">Save Document</button>
                <span id="txt-status" style="color:yellow; align-self:center; font-weight:bold;"></span>
            </div>
        </div>
    </div>

    <div id="imageModal" class="modal">
        <div class="modal-content" style="position: relative;">
            <span class="close-x" onclick="closeModal('imageModal')">&times;</span>
            <h3 style="margin:0 0 15px 0; color:#00d4ff; text-align:left; letter-spacing:1px;">🎨 Visual Processing Bay</h3>
            <input type="hidden" id="img-path">
            <canvas id="imgCanvas"></canvas>
            <div class="toolbar">
                <button class="btn" style="background: #444; color: #fff;" onclick="applyFilter('gray')">Grayscale</button>
                <button class="btn" style="background: #444; color: #fff;" onclick="resetCanvas()">Reset Image</button>
                <button class="btn" onclick="saveImage()">Save Image</button>
            </div>
            <p style="font-size:0.8em; color:#888; margin-top:10px;">* Draw with pointer/touch</p>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chat-box');
        const status = document.getElementById('status');
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'en-US';
        recognition.interimResults = false;

        document.getElementById('mic-btn').onclick = () => { recognition.start(); status.innerText = "Acoustic Sensors Active..."; };
        recognition.onresult = (e) => processInput(e.results[0][0].transcript);

        async function processInput(text) {
            if(!text.trim()) return;
            appendChat("You", text, "user");
            status.innerText = "Processing Directive...";

            try {
                const response = await fetch('/chat', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text })
                });
                const data = await response.json();
                
                if(data.action === 'open_url') window.open(data.url, '_blank');
                if(data.action === 'battery') checkBattery();
                
                let msgClass = data.is_warning ? "warning" : "jarvis";
                appendChat("J.A.R.V.I.S.", data.reply, msgClass);
                speak(data.reply);

                if(data.action === 'show_ui') renderUI(data);
                
            } catch (err) {
                appendChat("System", "Error communicating with the backend core.", "warning");
            }
            status.innerText = "System: Online & Secure";
        }

        function renderUI(data) {
            let html = `<div class="sys-box">`;
            if (data.context === 'dir') {
                html += `<div class="back-link" onclick="cmd('go back')">⬅ Go Up One Level</div>`;
                html += `<div class="path-header">Path: ${data.path_display}</div>`;
            } else if (data.context === 'gallery') {
                html += `<div class="path-header">Visual Media Gallery:</div>`;
            } else {
                html += `<div class="path-header">Database Search Results:</div>`;
            }

            if (data.context === 'gallery') {
                html += `<div class="gallery-grid">`;
                data.items.forEach(item => {
                    let viewUrl = `/view?path=${item.b64}`;
                    html += `<div class="gallery-item" onclick="viewFullscreen('${item.b64}')">
                                <img src="${viewUrl}" class="gallery-img" loading="lazy">
                             </div>`;
                });
                html += `</div>`;
            } 
            else {
                data.items.forEach(item => {
                    let viewUrl = `/view?path=${item.b64}`;
                    let icon = '📦', colorClass = 'color-def', action = `window.open('${viewUrl}', '_blank')`;

                    if(item.type === 'folder') {
                        icon = '📁'; colorClass = 'color-folder';
                        action = `cmd(\`open folder ${item.name}\`)`;
                    } else if(item.type === 'pdf') {
                        icon = '📕'; colorClass = 'color-pdf';
                        action = `window.open('${viewUrl}', '_blank')`;
                    } else if(item.type === 'img') {
                        icon = `<img src="${viewUrl}" class="rich-thumb" loading="lazy">`; 
                        colorClass = 'color-img';
                        action = `viewFullscreen('${item.b64}')`;
                    } else if(item.type === 'txt') {
                        icon = '📄'; colorClass = 'color-txt';
                        action = `openTxt('${item.b64}')`;
                    }

                    html += `
                    <div class="item-row" onclick="${action}">
                        <div class="item-name ${colorClass}">${icon} <span style="margin-left:8px;">${item.name}</span></div>
                    </div>`;
                });
            }
            
            html += `</div>`;
            appendChat("System", html, "system");
        }

        function cmd(text) { processInput(text); }
        function sendText() {
            const inp = document.getElementById('user-input');
            processInput(inp.value); inp.value = '';
        }

        function appendChat(user, msg, type) {
            let bubbleClass = type === 'user' ? 'bubble-user' : type === 'warning' ? 'bubble-warning' : 'bubble-jarvis';
            let html = `<div class="msg-container ${type === 'system' ? 'system' : type}">`;
            if(type !== 'system') {
                html += `<div style="font-size:0.75em; color:#888; margin-bottom:4px; margin-top:8px;">${user}</div>`;
            }
            html += `<div class="bubble ${type === 'system' ? '' : bubbleClass}">${msg}</div></div>`;
            chatBox.innerHTML += html;
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function speak(text) {
            window.speechSynthesis.cancel();
            let clean = text.replace(/J\.A\.R\.V\.I\.S\./g, 'Jarvis').replace(/[^a-zA-Z0-9\s,.]/g, '');
            const u = new SpeechSynthesisUtterance(clean);
            u.rate = 1.0; u.pitch = 0.8;
            window.speechSynthesis.speak(u);
        }

        function checkBattery() {
            if(navigator.getBattery) {
                navigator.getBattery().then(b => {
                    let msg = `Sir, your battery is currently at ${Math.round(b.level * 100)} percent.`;
                    appendChat("J.A.R.V.I.S.", msg, "jarvis"); speak(msg);
                });
            }
        }

        let currentImgB64 = '';
        
        function closeModal(id) { document.getElementById(id).style.display = 'none'; }
        
        function viewFullscreen(b64path) {
            currentImgB64 = b64path;
            document.getElementById('lightbox-img').src = `/view?path=${b64path}`;
            document.getElementById('lightboxModal').style.display = 'flex';
        }

        function openEditorFromLightbox() {
            closeModal('lightboxModal');
            openImg(currentImgB64);
        }

        async function openTxt(b64path) {
            document.getElementById('edit-path').value = b64path;
            document.getElementById('txt-status').innerText = "Decrypting file...";
            document.getElementById('textModal').style.display = 'flex';
            const res = await fetch(`/view?path=${b64path}&raw=true`);
            const text = await res.text();
            document.getElementById('edit-content').value = text;
            document.getElementById('txt-status').innerText = "";
        }

        async function saveTextFile(force=false) {
            const b64 = document.getElementById('edit-path').value;
            const content = document.getElementById('edit-content').value;
            document.getElementById('txt-status').innerText = "Uploading to drive...";
            
            const res = await fetch('/save_file', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({path: b64, content: content, force: force})
            });
            const data = await res.json();
            if(data.status === 'warn') {
                if(confirm("File already exists. Confirm Overwrite?")) saveTextFile(true);
                else document.getElementById('txt-status').innerText = "Upload Aborted.";
            } else {
                document.getElementById('txt-status').innerText = "✅ Saved Successfully!";
                setTimeout(()=>document.getElementById('txt-status').innerText="", 2000);
            }
        }

        let cvs = document.getElementById('imgCanvas'), ctx = cvs.getContext('2d');
        let imgObj = new Image(), isDrawing = false;

        function openImg(b64path) {
            document.getElementById('img-path').value = b64path;
            document.getElementById('imageModal').style.display = 'flex';
            imgObj.src = `/view?path=${b64path}`;
            imgObj.onload = () => resetCanvas();
        }

        function resetCanvas() {
            let maxW = window.innerWidth * 0.9;
            let ratio = imgObj.width / imgObj.height;
            cvs.width = Math.min(imgObj.width, maxW); cvs.height = cvs.width / ratio;
            ctx.filter = 'none'; ctx.drawImage(imgObj, 0, 0, cvs.width, cvs.height);
        }

        function applyFilter(t) {
            if(t==='gray') { ctx.filter = 'grayscale(100%)'; ctx.drawImage(imgObj, 0, 0, cvs.width, cvs.height); }
        }

        cvs.onmousedown = (e) => { isDrawing=true; ctx.beginPath(); ctx.moveTo(e.offsetX, e.offsetY); };
        cvs.onmousemove = (e) => { if(isDrawing){ ctx.strokeStyle="#00ff00"; ctx.lineWidth=4; ctx.lineTo(e.offsetX, e.offsetY); ctx.stroke(); }};
        cvs.onmouseup = () => isDrawing=false; cvs.onmouseout = () => isDrawing=false;
        
        cvs.ontouchstart = (e) => { isDrawing=true; let r=cvs.getBoundingClientRect(); ctx.beginPath(); ctx.moveTo(e.touches[0].clientX-r.left, e.touches[0].clientY-r.top); };
        cvs.ontouchmove = (e) => { if(isDrawing){ e.preventDefault(); let r=cvs.getBoundingClientRect(); ctx.strokeStyle="#00ff00"; ctx.lineWidth=4; ctx.lineTo(e.touches[0].clientX-r.left, e.touches[0].clientY-r.top); ctx.stroke(); }};
        cvs.ontouchend = () => isDrawing=false;

        async function saveImage() {
            const res = await fetch('/save_image', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ path: document.getElementById('img-path').value, img: cvs.toDataURL("image/png") })
            });
            if((await res.json()).success) alert("Image Saved to System!");
        }
    </script>
</body>
</html>
"""

# --- BACKEND ROUTES ---
@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

@app.route('/view')
def view_file():
    try:
        path = safe_decode(request.args.get('path'))
        raw = request.args.get('raw')
        if os.path.exists(path):
            if raw:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f: return f.read()
            return send_file(path, as_attachment=False)
        return "Not found", 404
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/save_file', methods=['POST'])
def save_file():
    d = request.json
    path = safe_decode(d['path'])
    if os.path.exists(path) and not d.get('force'): return jsonify({"status": "warn"})
    with open(path, 'w', encoding='utf-8') as f: f.write(d['content'])
    return jsonify({"status": "success"})

@app.route('/save_image', methods=['POST'])
def save_image():
    d = request.json
    path = safe_decode(d['path'])
    b64_data = d['img'].split(',')[1]
    with open(path, "wb") as fh: fh.write(base64.b64decode(b64_data))
    return jsonify({"success": True})

def build_ui_payload(items_list, is_search=False):
    payload = []
    img_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    txt_exts = ['.txt', '.py', '.js', '.html', '.css', '.json', '.csv', '.md', '.log']
    
    for item in items_list:
        try:
            name = os.path.basename(item)
            full_path = os.path.join(CURRENT_DIR, item) if not is_search else item
            
            type_str = 'file'
            if os.path.isdir(full_path): type_str = 'folder'
            elif name.lower().endswith('.pdf'): type_str = 'pdf'
            elif any(name.lower().endswith(e) for e in img_exts): type_str = 'img'
            elif any(name.lower().endswith(e) for e in txt_exts): type_str = 'txt'

            payload.append({"name": name, "type": type_str, "b64": safe_encode(full_path)})
        except Exception:
            pass
    return payload

@app.route('/chat', methods=['POST'])
def chat():
    global CURRENT_DIR, PENDING_DELETE
    raw = request.json.get('message', '').strip()
    msg_clean = re.sub(r'[^\w\s:./\-]', '', raw.lower()).strip()
    words = msg_clean.split()
    
    res = {"reply": "", "action": None, "is_warning": False, "show_ui": False}

    # 0. Awaiting Deletion Confirmation
    if PENDING_DELETE:
        if any(w in words for w in ["yes", "y", "confirm", "proceed"]):
            try:
                if os.path.isdir(PENDING_DELETE): shutil.rmtree(PENDING_DELETE)
                else: os.remove(PENDING_DELETE)
                res["reply"] = "Item permanently deleted from the system, sir."
            except Exception as e: res["reply"] = f"Error: {e}"
            PENDING_DELETE = None
            return jsonify(res)
        elif any(w in words for w in ["no", "n", "cancel", "stop", "abort"]):
            PENDING_DELETE = None
            res["reply"] = "Deletion aborted. Your files are secure."
            return jsonify(res)

    # 1. Identity & Core Basics
    if any(phrase in msg_clean for phrase in ["who are you", "your name", "what are you"]):
        res["reply"] = "I am J.A.R.V.I.S., your localized Artificial Intelligence operating system, designed to manage and optimize your device."
        return jsonify(res)
        
    if any(w in words for w in ["hi", "hello", "hey", "wake", "greetings"]):
        res["reply"] = "Greetings, sir. J.A.R.V.I.S. is online and awaiting your command."
        return jsonify(res)
        
    if any(phrase in msg_clean for phrase in ["what can you do", "what you can do", "help", "features"]):
        res["reply"] = "I can manage your device hierarchy, search files, load PDFs and images, edit code, open websites, and execute localized commands. Just ask."
        return jsonify(res)
        
    if "time" in words:
        res["reply"] = f"It is currently {datetime.datetime.now().strftime('%I:%M %p')}."
        return jsonify(res)
        
    if "battery" in words or "power" in words:
        res["reply"] = "Checking power diagnostic matrices."
        res["action"] = "battery"
        return jsonify(res)

    # 2. Dynamic Web URLs
    if msg_clean.startswith("open ") and "folder" not in msg_clean:
        target = msg_clean.replace("open ", "").strip()
        web_keywords = ["google", "youtube", "chatgpt", "facebook", "twitter", "github", "instagram", "netflix", ".com", ".org", ".in"]
        
        if any(w in target for w in web_keywords) or not smart_jump_search(target):
            if "." not in target: target += ".com"
            res["action"] = "open_url"
            res["url"] = f"https://www.{target}"
            res["reply"] = f"Establishing connection to {target}."
            return jsonify(res)

    # 3. File / Folder Creation
    if any(w in words for w in ["create", "make", "add"]):
        is_folder = "folder" in words and "file" not in words and not any("." in w for w in words)
        parent_dir = CURRENT_DIR
        
        for keyword in ["inside", "in"]:
            if keyword in words:
                idx = words.index(keyword)
                if idx + 1 < len(words):
                    p_name = words[idx+1]
                    if p_name == "folder" and idx + 2 < len(words): p_name = words[idx+2]
                    try:
                        for d in os.listdir(CURRENT_DIR):
                            if d.lower() == p_name.lower() and os.path.isdir(os.path.join(CURRENT_DIR, d)):
                                parent_dir = os.path.join(CURRENT_DIR, d)
                                break
                    except Exception:
                        pass
                break
                
        target_name = words[-1]
        for w in words:
            if "." in w: target_name = w
            
        try:
            if is_folder:
                os.makedirs(os.path.join(parent_dir, target_name), exist_ok=True)
                res["reply"] = f"Folder '{target_name}' successfully created."
            else:
                open(os.path.join(parent_dir, target_name), 'a').close()
                res["reply"] = f"File '{target_name}' successfully generated."
        except Exception as e:
            res["reply"] = f"Failed to generate item: {e}"
        return jsonify(res)

    # 4. Safe Deletion 
    m_del = re.search(r"(?:delete|remove)\s+(?:folder\s+|file\s+)?(.+)", msg_clean)
    if m_del:
        target = m_del.group(1).strip()
        matched = None
        try:
            for f in os.listdir(CURRENT_DIR):
                if f.lower() == target.lower():
                    matched = f
                    break
        except Exception:
            pass
        
        if matched:
            PENDING_DELETE = os.path.join(CURRENT_DIR, matched)
            res["reply"] = f"WARNING: Deleting '{matched}'. Reply 'yes' to confirm."
            res["is_warning"] = True
        else: 
            res["reply"] = f"Cannot delete. '{target}' not found in this sector."
        return jsonify(res)

    # 5. Fullscreen Gallery Engine
    if any(w in words for w in ["photo", "photos", "image", "images", "picture", "pictures", "gallery"]):
        res["reply"] = "Compiling your visual media gallery now, sir."
        results = global_search("", filter_exts=[".jpg", ".jpeg", ".png", ".gif", ".webp"], limit=60)
        res["action"] = "show_ui"
        res["context"] = "gallery"
        res["items"] = build_ui_payload(results, is_search=True)
        return jsonify(res)

    # 6. PDF Engine
    if any(w in words for w in ["pdf", "pdfs", "documents"]):
        m_pdf = re.search(r"(?:find|search for)\s+pdf\s+(.+)", msg_clean)
        if m_pdf:
            target = m_pdf.group(1).strip()
            res["reply"] = f"Locating PDF matching '{target}'."
            results = global_search(target, filter_exts=[".pdf"])
        else:
            res["reply"] = "Gathering all PDF documents on the device."
            results = global_search("", filter_exts=[".pdf"])
            
        res["action"] = "show_ui"
        res["context"] = "search"
        res["items"] = build_ui_payload(results, is_search=True)
        return jsonify(res)

    # 7. Navigation
    if msg_clean in ["go back", "back", "up", "previous"]:
        if CURRENT_DIR != BASE_DIR: CURRENT_DIR = os.path.dirname(CURRENT_DIR)
        folders, files = get_dir_contents(CURRENT_DIR)
        res["reply"] = "Navigating up one directory level."
        res["action"] = "show_ui"
        res["context"] = "dir"
        res["path_display"] = CURRENT_DIR
        res["items"] = build_ui_payload(folders + files)
        return jsonify(res)

    if any(phrase in msg_clean for phrase in ["show folder", "show folders", "folders", "folder", "files", "show files", "browse"]):
        CURRENT_DIR = BASE_DIR
        folders, files = get_dir_contents(CURRENT_DIR)
        res["reply"] = "Accessing directory matrix."
        res["action"] = "show_ui"
        res["context"] = "dir"
        res["path_display"] = CURRENT_DIR
        res["items"] = build_ui_payload(folders + files)
        return jsonify(res)

    # 8. Jump / Open Folder
    m_jump = re.search(r"^(?:jump to|go to|open folder|jump|open)\s+(.+)", msg_clean)
    target_jump = m_jump.group(1).strip() if m_jump else msg_clean

    if target_jump and len(words) <= 3 and not msg_clean.startswith("find"):
        found_dir = smart_jump_search(target_jump)
        if found_dir:
            CURRENT_DIR = found_dir
            folders, files = get_dir_contents(CURRENT_DIR)
            res["reply"] = f"Accessing {os.path.basename(found_dir)}."
            res["action"] = "show_ui"
            res["context"] = "dir"
            res["path_display"] = CURRENT_DIR
            res["items"] = build_ui_payload(folders + files)
            return jsonify(res)

    # 9. Find text inside a specific file
    m_inside = re.search(r"(?:find|search)\s+(.+?)\s+(?:in|inside)\s+([a-zA-Z0-9_\-\.]+)", msg_clean)
    if m_inside:
        target_word = m_inside.group(1).strip()
        filename = m_inside.group(2).strip()
        res["reply"] = f"Scanning '{filename}' for the text '{target_word}', sir."
        
        potential_files = global_search(filename)
        matched_files = []
        for filepath in potential_files:
            try:
                if os.path.isfile(filepath):
                    if filepath.lower().endswith('.pdf'):
                        content = extract_pdf_text(filepath)
                        if content != "MISSING_MODULE" and target_word in content: matched_files.append(filepath)
                    else:
                        if os.path.getsize(filepath) < 2 * 1024 * 1024:
                            try:
                                with open(filepath, 'r', encoding='utf-8', errors='ignore') as doc:
                                    if target_word in doc.read().lower(): matched_files.append(filepath)
                            except: pass
            except Exception:
                pass
                        
        if matched_files:
            res["reply"] += " Match found."
            res["action"] = "show_ui"
            res["context"] = "search"
            res["items"] = build_ui_payload(matched_files, is_search=True)
        else:
            res["reply"] = f"The text '{target_word}' was not found inside '{filename}'."
        return jsonify(res)

    # 10. Deep Content Word Search (General)
    m_word = re.search(r"(?:search|find)\s+word\s+([^\s]+)\s*(in\s+pdf)?", msg_clean)
    if m_word:
        word = m_word.group(1).strip()
        pdf_only = bool(m_word.group(2))
        res["reply"] = f"Scanning system contents for '{word}'."
        results, missing_mod = deep_content_search(word, pdf_only)
        
        if missing_mod: res["reply"] += " Note: PyPDF2 library is required to read PDFs."
        elif not results: res["reply"] = f"The target word '{word}' was not found."
        else: res["reply"] += " Deep scan complete. Matches found."
        
        res["action"] = "show_ui"
        res["context"] = "search"
        res["items"] = build_ui_payload(results, is_search=True)
        return jsonify(res)

    # 11. Global File Search
    m_file = re.search(r"(?:find|search for|search)\s+(?:file|folder)?\s*(.+)", msg_clean)
    if m_file:
        target = m_file.group(1).strip()
        res["reply"] = f"Scanning system hierarchy for '{target}'."
        results = global_search(target)
        res["action"] = "show_ui"
        res["context"] = "search"
        res["items"] = build_ui_payload(results, is_search=True)
        return jsonify(res)

    res["reply"] = "Command unverified. Please state your directive clearly, sir."
    return jsonify(res)

if __name__ == '__main__':
    # Request native runtime permissions inside Kivy's thread space on startup
    request_android_permissions()
    # Run the server
    app.run(host='127.0.0.1', port=5000, debug=False)
