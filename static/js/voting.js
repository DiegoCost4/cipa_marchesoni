let currentVote = "";
let isWhiteVote = false; // Nova flag para controlar estado
let capturedPhoto = null;
let cpfValue = "";

// --- Câmera e Validação de CPF ---
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const cpfInput = document.getElementById('cpfInput');
const feedback = document.getElementById('cpf-feedback');
const btnEnable = document.getElementById('btn-enable-vote');

async function initCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
    } catch (err) {
        alert("Erro ao acessar câmera: " + err);
    }
}
initCamera();

// Escuta a digitação do CPF
cpfInput.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\D/g, '');
    e.target.value = value;

    if (value.length < 11) {
        btnEnable.disabled = true;
        btnEnable.classList.add('opacity-50', 'cursor-not-allowed');
        btnEnable.classList.remove('hover:bg-blue-700');
        feedback.innerText = "";
        cpfInput.classList.remove('ring-2', 'ring-green-500', 'ring-red-500');
        return;
    }
    if (value.length === 11) validateCpfServer(value);
});

async function validateCpfServer(cpf) {
    feedback.innerText = "Verificando...";
    feedback.className = "text-sm font-bold min-h-[20px] mb-4 text-yellow-400";

    try {
        const res = await fetch(`/api/check-cpf/${cpf}`);
        const data = await res.json();

        if (data.allowed) {
            feedback.innerText = "✓ CPF Liberado";
            feedback.className = "text-sm font-bold min-h-[20px] mb-4 text-green-400";
            btnEnable.disabled = false;
            btnEnable.classList.remove('opacity-50', 'cursor-not-allowed');
            btnEnable.classList.add('hover:bg-blue-700');
            cpfInput.classList.add('ring-2', 'ring-green-500');
            cpfInput.classList.remove('ring-red-500');
            cpfValue = cpf; // Guarda o CPF
        } else {
            feedback.innerText = "⚠ " + data.message;
            feedback.className = "text-sm font-bold min-h-[20px] mb-4 text-red-500 bg-white px-2 py-1 rounded";
            btnEnable.disabled = true;
            cpfInput.classList.add('ring-2', 'ring-red-500');
        }
    } catch (error) {
        console.error(error);
    }
}

function startVoting() {
    // Capturar Foto
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    capturedPhoto = canvas.toDataURL('image/jpeg');

    // Troca de tela
    document.getElementById('step-1-controls').classList.add('hidden');
    document.getElementById('auth-status').classList.remove('hidden');
    const urna = document.getElementById('urna-panel');
    urna.classList.remove('opacity-50', 'pointer-events-none');
    
    playAudio('start');
}

// --- Lógica da Urna ---

function press(num) {
    if (isWhiteVote) return; // Se apertou Branco, bloqueia números
    if (currentVote.length < 2) {
        currentVote += num;
        updateScreen();
        if (currentVote.length === 2) fetchCandidate();
    }
}

function updateScreen() {
    document.getElementById('digit-1').innerText = currentVote[0] || "";
    document.getElementById('digit-2').innerText = currentVote[1] || "";
}

function whiteVote() {
    // Lógica do botão Branco
    currentVote = "";
    isWhiteVote = true;
    
    // Limpa números e mostra mensagem
    updateScreen(); 
    document.getElementById('candidate-data').classList.remove('hidden');
    document.getElementById('cand-name').innerText = "VOTO EM BRANCO";
    document.getElementById('cand-name').className = "text-2xl font-bold text-center mt-4"; // Aumenta fonte
    document.getElementById('cand-dept').innerText = "";
}

function correct() {
    currentVote = "";
    isWhiteVote = false;
    
    document.getElementById('candidate-data').classList.add('hidden');
    document.getElementById('cand-name').innerText = "...";
    document.getElementById('cand-name').className = "text-lg font-bold truncate"; // Volta fonte normal
    updateScreen();
}

async function fetchCandidate() {
    try {
        const res = await fetch(`/candidate-info/${currentVote}`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('cand-name').innerText = data.name;
            document.getElementById('cand-dept').innerText = data.department;
            document.getElementById('candidate-data').classList.remove('hidden');
        } else {
            document.getElementById('cand-name').innerText = "CANDIDATO INEXISTENTE";
            document.getElementById('cand-dept').innerText = "Verifique o número";
            document.getElementById('candidate-data').classList.remove('hidden');
        }
    } catch (e) { console.error(e); }
}

async function confirmVote() {
    let voteNumber = null;

    if (isWhiteVote) {
        voteNumber = "0"; // Código do voto em branco
    } else {
        if (!currentVote || currentVote.length !== 2) return;
        voteNumber = currentVote;
    }

    // Enviar para o Backend
    const payload = {
        cpf: cpfValue,
        number: voteNumber,
        photo: capturedPhoto
    };

    try {
        const res = await fetch('/vote', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        const json = await res.json();

        if (res.ok) {
            playAudio('end');
            document.getElementById('screen-default').classList.add('hidden');
            document.getElementById('candidate-data').classList.add('hidden');
            document.getElementById('screen-msg').classList.remove('hidden');
            
            setTimeout(() => {
                location.reload();
            }, 4000);
        } else {
            alert("Erro: " + json.error);
            // location.reload(); // Opcional: recarregar se der erro
            correct(); // Apenas limpa a tela se der erro (ex: cpf duplicado na ultima hora)
        }

    } catch (e) {
        alert("Erro de conexão");
    }
}

function playAudio(type) {
    if (type === 'end') {
        // O caminho deve ser relativo à raiz do servidor
        const audio = new Audio('/static/sounds/urna.mp3');
        
        // Tenta tocar o som
        audio.play().catch(error => {
            console.warn("O navegador bloqueou o áudio automático ou arquivo não encontrado.", error);
        });
    }
}