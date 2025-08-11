(function () {
  const startBtn = document.getElementById('startBtn');
  const stopBtn = document.getElementById('stopBtn');
  const statusEl = document.getElementById('status');
  const transcriptEl = document.getElementById('transcript');
  const replyEl = document.getElementById('replyText');
  const historyList = document.getElementById('historyList');

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const speechSynthesisApi = window.speechSynthesis;

  let recognition = null;
  let isListening = false;

  function initRecognition() {
    if (!SpeechRecognition) {
      statusEl.textContent = 'Web Speech API not supported in this browser.';
      startBtn.disabled = true;
      stopBtn.disabled = true;
      return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = true;
    recognition.continuous = false; // Stop after a phrase

    recognition.onstart = () => {
      isListening = true;
      statusEl.textContent = 'Listening...';
      startBtn.disabled = true;
      stopBtn.disabled = false;
      transcriptEl.textContent = '(listening)';
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }
      if (interimTranscript) transcriptEl.textContent = interimTranscript;
      if (finalTranscript) {
        transcriptEl.textContent = finalTranscript;
        sendToServer(finalTranscript.trim());
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      statusEl.textContent = 'Error: ' + event.error;
      isListening = false;
      startBtn.disabled = false;
      stopBtn.disabled = true;
    };

    recognition.onend = () => {
      isListening = false;
      statusEl.textContent = 'Microphone idle';
      startBtn.disabled = false;
      stopBtn.disabled = true;
    };
  }

  function startListening() {
    if (!recognition) return;
    try {
      recognition.start();
    } catch (e) {
      // Some browsers throw if called twice
    }
  }

  function stopListening() {
    if (recognition && isListening) {
      recognition.stop();
    }
  }

  async function sendToServer(text) {
    replyEl.textContent = 'Thinking...';
    try {
      const res = await fetch('/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Request failed');
      }
      const reply = data.reply || '';
      replyEl.textContent = reply;
      speak(reply);
      // Refresh history after sending a message
      await loadHistory();
    } catch (err) {
      console.error(err);
      replyEl.textContent = 'Error: ' + err.message;
    }
  }

  function speak(text) {
    if (!speechSynthesisApi) return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'en-US';
    utter.rate = 1.0;
    utter.pitch = 1.0;
    speechSynthesisApi.cancel();
    speechSynthesisApi.speak(utter);
  }

  async function loadHistory() {
    try {
      const res = await fetch('/history');
      const data = await res.json();
      const items = (data && data.messages) || [];
      renderHistory(items);
    } catch (e) {
      console.error('Failed to load history', e);
    }
  }

  function renderHistory(items) {
    historyList.innerHTML = '';
    items.forEach((row) => {
      const li = document.createElement('li');
      li.className = 'history-item';

      const user = document.createElement('div');
      user.className = 'user';
      user.textContent = 'You: ' + (row.user_input || '');

      const bot = document.createElement('div');
      bot.className = 'bot';
      bot.textContent = 'Assistant: ' + (row.assistant_reply || '');

      const ts = document.createElement('div');
      ts.className = 'timestamp';
      ts.textContent = row.timestamp || '';

      li.appendChild(ts);
      li.appendChild(user);
      li.appendChild(bot);

      historyList.appendChild(li);
    });
  }

  // Wire up UI
  document.addEventListener('DOMContentLoaded', async () => {
    initRecognition();
    await loadHistory();
  });

  startBtn.addEventListener('click', () => startListening());
  stopBtn.addEventListener('click', () => stopListening());
})();