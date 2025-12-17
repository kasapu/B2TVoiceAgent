document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    initSidebar();
    initTestingStudio();
    loadStats();
});

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            navigateTo(page);
        });
    });
    
    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();
}

function handleHashChange() {
    const hash = window.location.hash.slice(1) || 'dashboard';
    navigateTo(hash);
}

function navigateTo(page) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-page') === page) {
            item.classList.add('active');
        }
    });
    
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
    });
    
    const targetPage = document.getElementById('page-' + page);
    if (targetPage) {
        targetPage.classList.add('active');
    }
    
    window.location.hash = page;
    
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.remove('open');
}

function initSidebar() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    
    menuToggle.addEventListener('click', function() {
        sidebar.classList.toggle('open');
    });
    
    document.addEventListener('click', function(e) {
        if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });
}

function openChatWidget() {
    document.getElementById('chatModal').classList.add('active');
}

function closeChatWidget() {
    document.getElementById('chatModal').classList.remove('active');
}

function initTestingStudio() {
    const testInput = document.getElementById('testInput');
    if (testInput) {
        testInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendTestMessage();
            }
        });
    }
}

let ws = null;
let sessionId = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleTestMessage(data);
    };
    
    ws.onclose = function() {
        console.log('WebSocket disconnected');
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

function handleTestMessage(data) {
    const messagesContainer = document.getElementById('testMessages');
    
    switch (data.type) {
        case 'session_created':
            sessionId = data.session_id;
            break;
            
        case 'message':
            const botMsg = document.createElement('div');
            botMsg.className = 'message bot';
            botMsg.textContent = data.text;
            messagesContainer.appendChild(botMsg);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            document.getElementById('detectedIntent').textContent = data.intent || '-';
            document.getElementById('confidence').textContent = data.confidence ? 
                (data.confidence * 100).toFixed(1) + '%' : '-';
            document.getElementById('entities').textContent = '-';
            break;
    }
}

function sendTestMessage() {
    const input = document.getElementById('testInput');
    const text = input.value.trim();
    
    if (!text) return;
    
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        connectWebSocket();
        setTimeout(() => sendTestMessage(), 500);
        return;
    }
    
    const messagesContainer = document.getElementById('testMessages');
    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.textContent = text;
    messagesContainer.appendChild(userMsg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    ws.send(JSON.stringify({
        type: 'message',
        text: text
    }));
    
    input.value = '';
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        if (response.ok) {
            const stats = await response.json();
            updateStats(stats);
        }
    } catch (error) {
        console.log('Stats not available');
    }
}

function updateStats(stats) {
    const statValues = document.querySelectorAll('.stat-value');
    if (stats.conversations_today !== undefined && statValues[0]) {
        statValues[0].textContent = stats.conversations_today.toLocaleString();
    }
    if (stats.success_rate !== undefined && statValues[1]) {
        statValues[1].textContent = stats.success_rate + '%';
    }
    if (stats.avg_response_time !== undefined && statValues[2]) {
        statValues[2].textContent = stats.avg_response_time + 's';
    }
    if (stats.active_users !== undefined && statValues[3]) {
        statValues[3].textContent = stats.active_users.toLocaleString();
    }
}

function initDragAndDrop() {
    const components = document.querySelectorAll('.component-item');
    const canvas = document.querySelector('.flow-canvas');
    
    components.forEach(comp => {
        comp.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('text/plain', this.textContent.trim());
        });
    });
    
    if (canvas) {
        canvas.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.style.background = 'rgba(67, 97, 238, 0.1)';
        });
        
        canvas.addEventListener('dragleave', function() {
            this.style.background = '';
        });
        
        canvas.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.background = '';
            const componentType = e.dataTransfer.getData('text/plain');
            addFlowComponent(componentType, e.offsetX, e.offsetY);
        });
    }
}

function addFlowComponent(type, x, y) {
    const canvas = document.querySelector('.flow-canvas');
    const placeholder = canvas.querySelector('.canvas-placeholder');
    
    if (placeholder) {
        placeholder.style.display = 'none';
    }
    
    const node = document.createElement('div');
    node.className = 'flow-node';
    node.style.position = 'absolute';
    node.style.left = x + 'px';
    node.style.top = y + 'px';
    node.style.padding = '12px 20px';
    node.style.background = 'white';
    node.style.border = '2px solid var(--primary-color)';
    node.style.borderRadius = '8px';
    node.style.cursor = 'move';
    node.textContent = type;
    
    canvas.style.position = 'relative';
    canvas.appendChild(node);
    
    makeDraggable(node);
}

function makeDraggable(element) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    
    element.onmousedown = dragMouseDown;
    
    function dragMouseDown(e) {
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }
    
    function elementDrag(e) {
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        element.style.top = (element.offsetTop - pos2) + 'px';
        element.style.left = (element.offsetLeft - pos1) + 'px';
    }
    
    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initDragAndDrop();
});
