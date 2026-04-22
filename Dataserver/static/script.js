async function handleSubmit() {
    const input = document.getElementById('userInput');
    const text = input.value.trim();
    if (!text) return;
function renderMessages() {
    const container = document.getElementById('messages');
    const empty = document.getElementById('emptyState');
    const conv = conversations.find(c => c.id === activeConvId);

    if (!conv || conv.messages.length === 0) {
        empty.style.display = 'flex';
        container.innerHTML = '';
        return;
    }

    empty.style.display = 'none';
    
    // Limpamos o container para renderizar do zero (importante para o Chart.js não duplicar)
    container.innerHTML = '';

    conv.messages.forEach((m, index) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `msg ${m.role}`;
        
        // ID único para cada gráfico para o Chart.js saber onde desenhar
        const chartId = `chart-${activeConvId}-${index}`;
        
        msgDiv.innerHTML = `
            <div class="bubble">
                ${(m.content || "").replace(/\n/g, '<br>')}
                ${m.hasChart ? `<div class="chart-container"><canvas id="${chartId}"></canvas></div>` : ''}
            </div>
        `;
        container.appendChild(msgDiv);

        // Se a mensagem tem dados de gráfico, desenha ele usando a biblioteca
        if (m.hasChart && m.chartData) {
            // Pequeno delay para garantir que o canvas já existe no HTML
            setTimeout(() => {
                const ctx = document.getElementById(chartId).getContext('2d');
                new Chart(ctx, {
                    type: m.chartData.type === 'donut' ? 'doughnut' : m.chartData.type,
                    data: {
                        labels: m.chartData.labels,
                        datasets: [{
                            label: m.chartData.title,
                            data: m.chartData.values,
                            backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'],
                            borderRadius: 8,
                            borderWidth: 0,
                            hoverOffset: 15
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } }
                        },
                        animation: { duration: 2000, easing: 'easeOutQuart' }
                    }
                });
            }, 50);
        }
    });
    
    const chatArea = document.getElementById('chatArea');
    chatArea.scrollTop = chatArea.scrollHeight;
}
    // 1. Mostra a pergunta do usuário na tela
    renderUserMessage(text);
    input.value = '';
// Adicionamos (m.content || "") para garantir que nunca seja undefined
container.innerHTML = conv.messages.map(m => `
    <div class="msg ${m.role}">
        <div class="bubble">
            ${(m.content || "").replace(/\n/g, '<br>')}
            ${m.chart_html || ""}
        </div>
    </div>
`).join('');

    try {
        // 2. Envia para o Python (FastAPI)
        const response = await fetch('/api/analisar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();

        // 3. Verifica se a IA decidiu que precisa de gráfico
        let chartContainer = null;
        if (data.tipo_grafico && data.tipo_grafico !== 'null') {
            const canvasId = `chart-${Date.now()}`;
            chartContainer = `<div class="chart-box"><canvas id="${canvasId}"></canvas></div>`;
            
            // Desenha o gráfico após o HTML ser inserido
            setTimeout(() => {
                renderChart(canvasId, data);
            }, 100);
        }

        // 4. Mostra a resposta da IA
        renderAssistantMessage(data.analise, chartContainer);

    } catch (error) {
        console.error("Erro na requisição:", error);
    }
}

function renderChart(id, data) {
    const ctx = document.getElementById(id).getContext('2d');
    new Chart(ctx, {
        type: data.tipo_grafico === 'donut' ? 'doughnut' : data.tipo_grafico,
        data: {
            labels: data.eixo_x,
            datasets: [{
                label: data.titulo,
                data: data.valores,
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}