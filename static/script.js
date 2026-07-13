// ===================================================================
// Navegação entre abas (categorias, perfis, gráfico, comparador,
// perfil customizado, jogadores parecidos)
// ===================================================================

// Troca qual painel (.tab-painel) fica visível e marca o botão da
// sidebar correspondente como ativo. Usado pelos onclick="mostrarPainel(...)"
// espalhados no resultado.html (cada categoria/perfil/gráfico/ferramenta
// é um painel independente, um <div class="tab-painel"> por vez visível).
function mostrarPainel(id, botaoClicado) {
    document.querySelectorAll(".tab-painel").forEach(function(painel) {
        painel.classList.remove("ativo");
    });
    document.querySelectorAll(".sidebar-item").forEach(function(botao) {
        botao.classList.remove("ativo");
    });

    document.getElementById("painel-" + id).classList.add("ativo");
    botaoClicado.classList.add("ativo");
}

// Abre/fecha uma seção da sidebar (ex: "Ver por Categoria", "Comparador").
function toggleSecao(nome) {
    document.getElementById("lista-" + nome).classList.toggle("aberta");
}

// ===================================================================
// Gráfico de dispersão (Chart.js)
// ===================================================================

let graficoDispersao = null;
let graficoRadar = null;

if (window.ChartAnnotation) {
    Chart.register(window.ChartAnnotation);
}

// Usada para posicionar as linhas tracejadas de mediana no gráfico
// (separam visualmente "acima/abaixo da média" nos eixos X e Y).
function calcularMediana(valores) {
    const ordenados = [...valores].sort(function(a, b) { return a - b; });
    const meio = Math.floor(ordenados.length / 2);
    if (ordenados.length % 2 === 0) {
        return (ordenados[meio - 1] + ordenados[meio]) / 2;
    }
    return ordenados[meio];
}

// Desenha o gráfico de dispersão (scatter) para o preset clicado (ex:
// "Construção": Passes certos x Passes em progressão). Cada preset define
// os eixos e o texto de cada quadrante (window.presetsDispersao, injetado
// pelo resultado.html a partir de PRESETS_DISPERSAO em app.py).
function desenharDispersaoPreset(nomePreset, botaoClicado) {
    window.presetAtivoAtual = nomePreset;
    const preset = window.presetsDispersao[nomePreset];
    const colunaX = preset.x;
    const colunaY = preset.y;
    const quadrantes = preset.quadrantes;

    const favoritosAtuais = obterFavoritos();
    const pontos = window.dadosDispersao.map(function(jogador) {
        return {
            x: jogador[colunaX],
            y: jogador[colunaY],
            nome: jogador["Jogador"],
            favorito: favoritosAtuais.includes(jogador["Jogador"]),
        };
    });

    document.querySelectorAll(".preset-card").forEach(function(botao) {
        botao.classList.remove("ativo");
    });
    botaoClicado.classList.add("ativo");

    document.getElementById("preset-descricao-atual").textContent = preset.descricao;

    const valoresX = pontos.map(function(p) { return p.x; });
    const valoresY = pontos.map(function(p) { return p.y; });
    const medianaX = calcularMediana(valoresX);
    const medianaY = calcularMediana(valoresY);
    const maxX = Math.max(...valoresX);
    const minX = Math.min(...valoresX);
    const maxY = Math.max(...valoresY);
    const minY = Math.min(...valoresY);

    if (graficoDispersao) {
        graficoDispersao.destroy();
    }

    graficoDispersao = new Chart(document.getElementById("grafico-dispersao"), {
        type: "scatter",
        data: {
            datasets: [{
                label: "Jogadores",
                data: pontos,
                backgroundColor: function(contexto) {
                    return contexto.raw && contexto.raw.favorito ? "#C8A24A" : "#2F6F4E";
                },
                borderColor: function(contexto) {
                    return contexto.raw && contexto.raw.favorito ? "#0B1D17" : "transparent";
                },
                borderWidth: 2,
                pointRadius: function(contexto) {
                    return contexto.raw && contexto.raw.favorito ? 9 : 6;
                },
                pointHoverRadius: function(contexto) {
                    return contexto.raw && contexto.raw.favorito ? 11 : 8;
                },
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(contexto) {
                            const ponto = contexto.raw;
                            return ponto.nome + ": " + colunaX + " " + ponto.x + " · " + colunaY + " " + ponto.y;
                        }
                    }
                },
                annotation: {
                    annotations: {
                        linhaMedianaX: {
                            type: "line",
                            xMin: medianaX,
                            xMax: medianaX,
                            borderColor: "#4A6FA5",
                            borderWidth: 1,
                            borderDash: [4, 4],
                        },
                        linhaMedianaY: {
                            type: "line",
                            yMin: medianaY,
                            yMax: medianaY,
                            borderColor: "#4A6FA5",
                            borderWidth: 1,
                            borderDash: [4, 4],
                        },
                        labelSupDir: {
                            type: "label",
                            xValue: maxX,
                            yValue: maxY,
                            content: [quadrantes.sup_dir],
                            color: "#4A6FA5",
                            font: { size: 13, weight: "600", style: "italic" },
                            position: { x: "end", y: "start" },
                        },
                        labelSupEsq: {
                            type: "label",
                            xValue: minX,
                            yValue: maxY,
                            content: [quadrantes.sup_esq],
                            color: "#4A6FA5",
                            font: { size: 13, weight: "600", style: "italic" },
                            position: { x: "start", y: "start" },
                        },
                        labelInfDir: {
                            type: "label",
                            xValue: maxX,
                            yValue: minY,
                            content: [quadrantes.inf_dir],
                            color: "#4A6FA5",
                            font: { size: 13, weight: "600", style: "italic" },
                            position: { x: "end", y: "end" },
                        },
                        labelInfEsq: {
                            type: "label",
                            xValue: minX,
                            yValue: minY,
                            content: [quadrantes.inf_esq],
                            color: "#4A6FA5",
                            font: { size: 13, weight: "600", style: "italic" },
                            position: { x: "start", y: "end" },
                        },
                    },
                },
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: colunaX,
                        font: { size: 14, weight: "600" },
                        color: "#1A1A1A",
                    },
                    ticks: { font: { size: 12 } },
                },
                y: {
                    title: {
                        display: true,
                        text: colunaY,
                        font: { size: 14, weight: "600" },
                        color: "#1A1A1A",
                    },
                    ticks: { font: { size: 12 } },
                },
            }
        }
    });
}

// ===================================================================
// Radar de Jogador (Chart.js "radar") — compara até 2 jogadores nas
// métricas de um perfil escolhido, normalizadas de 0 a 100
// ===================================================================

// Liga os 3 seletores da aba "Radar de Jogador": qualquer mudança
// redesenha o gráfico automaticamente.
function configurarRadar() {
    ["radar-jogador-1", "radar-jogador-2", "radar-perfil"].forEach(function(id) {
        const elemento = document.getElementById(id);
        if (elemento) {
            elemento.addEventListener("change", desenharRadar);
        }
    });
}

// Normaliza (0 a 100, min-max sobre toda a base importada) as métricas do
// perfil escolhido para um jogador específico. Devolve null se o jogador
// não existir em window.dadosDispersao (não deveria acontecer, mas evita
// quebrar o gráfico).
function normalizarMetricasJogador(nomeJogador, metricas, minMaxPorMetrica) {
    const dadosJogador = window.dadosDispersao.find(function(jogador) {
        return jogador["Jogador"] === nomeJogador;
    });
    if (!dadosJogador) {
        return null;
    }

    return metricas.map(function(metrica) {
        const faixa = minMaxPorMetrica[metrica];
        const valor = dadosJogador[metrica];
        if (!faixa || typeof valor !== "number" || isNaN(valor) || faixa.max === faixa.min) {
            return 50;
        }
        return ((valor - faixa.min) / (faixa.max - faixa.min)) * 100;
    });
}

// Desenha (ou redesenha) o radar com os jogadores/perfil selecionados no
// momento. Perfil "Radar de Jogador" reaproveita o Chart.js já carregado
// (type: "radar"), como descrito no roadmap.
function desenharRadar() {
    const jogador1 = document.getElementById("radar-jogador-1").value;
    const jogador2 = document.getElementById("radar-jogador-2").value;
    const nomePerfil = document.getElementById("radar-perfil").value;

    if (graficoRadar) {
        graficoRadar.destroy();
        graficoRadar = null;
    }

    if (!jogador1 || !nomePerfil || !window.perfisMetricas[nomePerfil]) {
        return;
    }

    const metricas = Object.keys(window.perfisMetricas[nomePerfil]);

    // Min/máx de cada métrica do perfil, calculados sobre TODOS os
    // jogadores importados — é isso que dá a escala 0-100 de cada eixo.
    const minMaxPorMetrica = {};
    metricas.forEach(function(metrica) {
        const valores = window.dadosDispersao
            .map(function(jogador) { return jogador[metrica]; })
            .filter(function(valor) { return typeof valor === "number" && !isNaN(valor); });
        minMaxPorMetrica[metrica] = {
            min: valores.length ? Math.min(...valores) : 0,
            max: valores.length ? Math.max(...valores) : 0,
        };
    });

    const datasets = [];

    const valores1 = normalizarMetricasJogador(jogador1, metricas, minMaxPorMetrica);
    if (valores1) {
        datasets.push({
            label: jogador1,
            data: valores1,
            backgroundColor: "rgba(47, 111, 78, 0.25)",
            borderColor: "#2F6F4E",
            borderWidth: 2,
            pointBackgroundColor: "#2F6F4E",
        });
    }

    if (jogador2) {
        const valores2 = normalizarMetricasJogador(jogador2, metricas, minMaxPorMetrica);
        if (valores2) {
            datasets.push({
                label: jogador2,
                data: valores2,
                backgroundColor: "rgba(200, 162, 74, 0.25)",
                borderColor: "#C8A24A",
                borderWidth: 2,
                pointBackgroundColor: "#C8A24A",
            });
        }
    }

    if (datasets.length === 0) {
        return;
    }

    graficoRadar = new Chart(document.getElementById("grafico-radar"), {
        type: "radar",
        data: {
            labels: metricas,
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "bottom" },
            },
            scales: {
                r: {
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        showLabelBackdrop: false,
                        color: "#8D969C",
                    },
                    pointLabels: {
                        font: { size: 11 },
                        color: "#E8ECEF",
                    },
                    // O padrão do Chart.js pra essas duas cores é
                    // "rgba(0, 0, 0, 0.1)" — quase invisível no tema escuro
                    // deste site (fundo #0D1013), por isso as linhas de
                    // fundo do radar (teia + raios) pareciam ter sumido.
                    // Definindo explicitamente uma cor clara e translúcida.
                    grid: { color: "rgba(232, 236, 239, 0.15)" },
                    angleLines: { color: "rgba(232, 236, 239, 0.15)" },
                },
            },
        },
    });
}

// ===================================================================
// Comparador de jogadores (até 3 lado a lado)
// ===================================================================

// Monta a tabela do comparador sempre que um dos 3 <select> de jogador
// muda. window.dadosComparador e window.estruturaCategorias vêm prontos
// do backend (app.py: dados_comparador e estrutura_categorias), já
// formatados — aqui só organizamos em linhas (uma por métrica, agrupadas
// por categoria) e colunas (uma por jogador selecionado).
function montarComparador() {
    const nomes = [
        document.getElementById("comparar-jogador-1").value,
        document.getElementById("comparar-jogador-2").value,
        document.getElementById("comparar-jogador-3").value,
    ].filter(function(n) { return n; });

    const tabela = document.getElementById("tabela-comparador");
    tabela.innerHTML = "";

    if (nomes.length < 2) {
        return;
    }

    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");
    const thMetrica = document.createElement("th");
    thMetrica.textContent = "Métrica";
    thMetrica.className = "identidade identidade-fixa";
    trHead.appendChild(thMetrica);
    nomes.forEach(function(nome) {
        const th = document.createElement("th");
        th.textContent = nome;
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");

    Object.keys(window.estruturaCategorias).forEach(function(categoria) {
        const trCategoria = document.createElement("tr");
        const tdCategoria = document.createElement("td");
        tdCategoria.textContent = categoria;
        tdCategoria.colSpan = nomes.length + 1;
        tdCategoria.className = "comparador-categoria";
        trCategoria.appendChild(tdCategoria);
        tbody.appendChild(trCategoria);

        window.estruturaCategorias[categoria].forEach(function(coluna) {
            const tr = document.createElement("tr");
            const tdMetrica = document.createElement("td");
            tdMetrica.textContent = coluna;
            tdMetrica.className = "identidade identidade-fixa";
            tr.appendChild(tdMetrica);

            nomes.forEach(function(nome) {
                const td = document.createElement("td");
                const dadosJogador = window.dadosComparador[nome];
                td.textContent = dadosJogador ? dadosJogador[coluna] : "-";
                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });
    });

    tabela.appendChild(tbody);
}

// ===================================================================
// Perfil Customizado (usuário escolhe métricas + pesos e gera um ranking
// sob medida, via POST /perfil-customizado)
// ===================================================================

// Liga os listeners da aba "Perfil Customizado": marcar uma checkbox
// habilita o campo de peso correspondente; o botão "Calcular Ranking"
// dispara a requisição ao backend.
function configurarPerfilCustomizado() {
    document.querySelectorAll(".metrica-checkbox").forEach(function(checkbox) {
        checkbox.addEventListener("change", function() {
            const linha = checkbox.closest(".perfil-custom-linha");
            const inputPeso = linha.querySelector(".metrica-peso");
            inputPeso.disabled = !checkbox.checked;
        });
    });

    const botao = document.getElementById("calcular-perfil-custom");
    if (botao) {
        botao.addEventListener("click", calcularPerfilCustomizado);
    }
}

// Monta {métrica: peso} a partir das checkboxes marcadas e envia para
// POST /perfil-customizado (app.py: perfil_customizado), que recalcula
// o ranking com esses pesos em vez dos pesos fixos de PERFIS_VOLANTES.
function calcularPerfilCustomizado() {
    const pesos = {};

    document.querySelectorAll(".metrica-checkbox:checked").forEach(function(checkbox) {
        const coluna = checkbox.value;
        const inputPeso = document.querySelector(".metrica-peso[data-coluna='" + coluna + "']");
        const valor = parseFloat(inputPeso.value);
        if (!isNaN(valor) && valor !== 0) {
            pesos[coluna] = valor;
        }
    });

    if (Object.keys(pesos).length === 0) {
        alert("Selecione ao menos uma métrica com peso diferente de zero.");
        return;
    }

    fetch("/perfil-customizado", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pesos: pesos })
    })
        .then(function(resposta) { return resposta.json(); })
        .then(function(dados) {
            if (dados.erro) {
                alert(dados.erro);
                return;
            }
            renderizarTabelaPerfilCustom(dados);
        })
        .catch(function(erro) {
            alert("Erro ao calcular o perfil.");
            console.error(erro);
        });
}

// Constrói a tabela de resultado do perfil customizado a partir do JSON
// devolvido por /perfil-customizado (colunas_identidade, colunas_metricas,
// registros e intensidades — mesmo esquema de cores 0 a 1 usado nas
// tabelas renderizadas pelo Jinja em resultado.html).
function renderizarTabelaPerfilCustom(dados) {
    const tabela = document.getElementById("tabela-perfil-custom");
    tabela.innerHTML = "";

    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");

    dados.colunas_identidade.forEach(function(coluna, indice) {
        const th = document.createElement("th");
        th.textContent = coluna;
        if (indice === 0) th.className = "identidade identidade-fixa";
        trHead.appendChild(th);
    });
    dados.colunas_metricas.forEach(function(coluna) {
        const th = document.createElement("th");
        th.textContent = coluna;
        trHead.appendChild(th);
    });
    const thNota = document.createElement("th");
    thNota.textContent = "Nota do Perfil";
    trHead.appendChild(thNota);

    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");

    dados.registros.forEach(function(registro, indice) {
        const tr = document.createElement("tr");

        dados.colunas_identidade.forEach(function(coluna, i) {
            const td = document.createElement("td");

            if (i === 0) {
                td.className = "identidade identidade-fixa";
                const nome = registro[coluna];

                const botaoFavorito = document.createElement("button");
                botaoFavorito.className = "favorito-estrela";
                botaoFavorito.textContent = "★";
                botaoFavorito.dataset.jogadorEstrela = nome;
                botaoFavorito.addEventListener("click", function() { toggleFavorito(nome); });
                td.appendChild(botaoFavorito);

                const botaoNota = document.createElement("button");
                botaoNota.className = "nota-botao";
                botaoNota.textContent = "📝";
                botaoNota.title = "Adicionar nota";
                botaoNota.dataset.jogadorNota = nome;
                botaoNota.addEventListener("click", function() { abrirNota(nome); });
                td.appendChild(botaoNota);

                td.appendChild(document.createTextNode(" " + nome));
            } else {
                td.textContent = registro[coluna];
            }

            tr.appendChild(td);
        });

        dados.colunas_metricas.forEach(function(coluna) {
            const td = document.createElement("td");
            td.textContent = registro[coluna];
            const intensidade = dados.intensidades[indice][coluna];
            if (intensidade !== null && intensidade !== undefined) {
                td.style.backgroundColor = "rgba(47, 111, 78, " + (intensidade * 0.45).toFixed(2) + ")";
            }
            tr.appendChild(td);
        });

        const tdNota = document.createElement("td");
        tdNota.textContent = registro["Nota do Perfil"];
        const intensidadeNota = dados.intensidades[indice]["Nota do Perfil"];
        if (intensidadeNota !== null && intensidadeNota !== undefined) {
            tdNota.style.backgroundColor = "rgba(200, 162, 74, " + (intensidadeNota * 0.45).toFixed(2) + ")";
        }
        tr.appendChild(tdNota);

        tbody.appendChild(tr);
    });

    tabela.appendChild(tbody);

    // A tabela acabou de ser recriada do zero — os botões de estrela/nota
    // são novos elementos, então precisam ser sincronizados com o que já
    // está salvo no localStorage (favoritos e notas).
    aplicarFavoritos();
    atualizarBotoesNota();
}

// ===================================================================
// Inicialização (roda uma vez, quando a página termina de carregar)
// ===================================================================

document.addEventListener("DOMContentLoaded", function() {
    // Abre a primeira categoria e o primeiro preset de dispersão por
    // padrão, para a tela não começar em branco.
    mostrarPainel(
        "cat-" + window.primeiraCategoria,
        document.getElementById("botao-cat-" + window.primeiraCategoria)
    );

    const primeiroPreset = document.querySelector(".preset-card");
    if (primeiroPreset) {
        primeiroPreset.click();
    }

    // Recalcula a tabela do comparador sempre que um dos 3 selects muda.
    ["comparar-jogador-1", "comparar-jogador-2", "comparar-jogador-3"].forEach(function(id) {
        const elemento = document.getElementById(id);
        if (elemento) {
            elemento.addEventListener("change", montarComparador);
        }
    });

    configurarPerfilCustomizado();

    tornarTabelasOrdenaveis();
    configurarPaginacao();
    aplicarFavoritos();
    configurarFiltros();
    aplicarFiltros();
    atualizarSelectsSomenteFavoritos();
    configurarJogadoresParecidos();
    configurarMelhorPerfil();
    configurarRadar();
    configurarModalNota();
    atualizarBotoesNota();
    renderizarFavoritosNotas();
    configurarExportarCSV();
});

// ===================================================================
// Ordenação de tabelas (clique no cabeçalho da coluna)
// ===================================================================

// Extrai um número de um texto de célula (removendo "%"), para permitir
// ordenar numericamente em vez de alfabeticamente (ex: "83.3%" -> 83.3).
// Se não for um número, a ordenação cai para comparação de texto (pt-BR).
function parseValor(texto) {
    const limpo = texto.replace("%", "").trim();

    // Valores monetários abreviados (ex: "R$ 120.5M", "R$ 96K") viram o
    // número cheio, pra ordenar numericamente como qualquer outra coluna.
    const matchMoeda = limpo.match(/^R\$\s*([\d.,]+)\s*([KM])?$/i);
    if (matchMoeda) {
        let numeroMoeda = parseFloat(matchMoeda[1].replace(",", "."));
        const sufixo = (matchMoeda[2] || "").toUpperCase();
        if (sufixo === "K") numeroMoeda *= 1000;
        if (sufixo === "M") numeroMoeda *= 1000000;
        return isNaN(numeroMoeda) ? null : numeroMoeda;
    }

    const numero = parseFloat(limpo);
    return isNaN(numero) ? null : numero;
}

// Ordena as linhas de uma tabela pela coluna clicada, alternando entre
// crescente/decrescente a cada clique no mesmo cabeçalho.
function ordenarTabela(tabela, indice, thClicado) {
    const tbody = tabela.querySelector("tbody");
    const linhas = Array.from(tbody.querySelectorAll("tr"));

    const novaDirecao = thClicado.dataset.direcao === "asc" ? "desc" : "asc";

    tabela.querySelectorAll("thead th").forEach(function(th) {
        th.dataset.direcao = "";
        th.classList.remove("ordenado-asc", "ordenado-desc");
    });
    thClicado.dataset.direcao = novaDirecao;
    thClicado.classList.add(novaDirecao === "asc" ? "ordenado-asc" : "ordenado-desc");

    linhas.sort(function(a, b) {
        const textoA = a.children[indice].textContent.trim();
        const textoB = b.children[indice].textContent.trim();

        const numA = parseValor(textoA);
        const numB = parseValor(textoB);

        let comparacao;
        if (numA !== null && numB !== null) {
            comparacao = numA - numB;
        } else {
            comparacao = textoA.localeCompare(textoB, "pt-BR");
        }

        return novaDirecao === "asc" ? comparacao : -comparacao;
    });

    linhas.forEach(function(linha) {
        tbody.appendChild(linha);
    });

    // A ordem mudou: se essa tabela tiver paginação, a janela de linhas
    // visíveis (linha-pagina-oculta) precisa ser recalculada sobre a nova
    // ordem, senão a página atual mostraria linhas "erradas".
    const wrapperOrdenado = tabela.closest(".tabela-wrapper");
    if (wrapperOrdenado && wrapperOrdenado.querySelector(".paginacao-controles")) {
        atualizarPaginacao(wrapperOrdenado);
    }
}

// Adiciona o listener de clique a cada cabeçalho (th) de cada tabela da
// página, tornando todas elas ordenáveis sem precisar repetir isso no HTML.
function tornarTabelasOrdenaveis() {
    document.querySelectorAll(".tabela-wrapper table").forEach(function(tabela) {
        tabela.querySelectorAll("thead th").forEach(function(th, indice) {
            th.dataset.direcao = "";
            th.addEventListener("click", function() {
                ordenarTabela(tabela, indice, th);
            });
        });
    });
}

// ===================================================================
// Paginação das tabelas (categoria e ranking por perfil)
// ===================================================================
// Só se aplica às tabelas que recebem a base inteira de uma vez (as
// tabelas de categoria e de ranking por perfil, renderizadas pelo Jinja
// com tr[data-jogador] no tbody). As tabelas montadas via AJAX
// (comparador, jogadores parecidos, melhor perfil) não têm essas linhas
// no momento do DOMContentLoaded e por isso não recebem paginação — elas
// já são naturalmente pequenas.
//
// A paginação não interfere na classe de filtro (linha-oculta, ver
// aplicarFiltros): ela aplica uma segunda classe (linha-pagina-oculta)
// só nas linhas que já passaram no filtro, mas ficam fora da página
// atual.

const PAGINACAO_TAMANHO_PAGINA = 50;

function configurarPaginacao() {
    document.querySelectorAll(".tabela-wrapper table").forEach(function(tabela) {
        const tbody = tabela.querySelector("tbody");
        if (!tbody || !tbody.querySelector("tr[data-jogador]")) return;

        const wrapper = tabela.closest(".tabela-wrapper");
        wrapper.dataset.paginaAtual = "1";

        const controles = document.createElement("div");
        controles.className = "paginacao-controles";
        controles.innerHTML =
            '<button type="button" class="paginacao-botao" data-acao="anterior">‹ Anterior</button>' +
            '<span class="paginacao-info"></span>' +
            '<button type="button" class="paginacao-botao" data-acao="proxima">Próxima ›</button>';
        wrapper.appendChild(controles);

        controles.querySelector('[data-acao="anterior"]').addEventListener("click", function() {
            const atual = parseInt(wrapper.dataset.paginaAtual, 10) || 1;
            wrapper.dataset.paginaAtual = String(atual - 1);
            atualizarPaginacao(wrapper);
        });
        controles.querySelector('[data-acao="proxima"]').addEventListener("click", function() {
            const atual = parseInt(wrapper.dataset.paginaAtual, 10) || 1;
            wrapper.dataset.paginaAtual = String(atual + 1);
            atualizarPaginacao(wrapper);
        });

        atualizarPaginacao(wrapper);
    });
}

// Recalcula quais linhas (das que já passaram no filtro) ficam visíveis
// na página atual do wrapper, e atualiza o texto/estado dos controles.
// Chamada sempre que o conjunto de linhas visíveis pode ter mudado:
// no carregamento (configurarPaginacao), depois de filtrar
// (aplicarFiltros) e depois de ordenar (ordenarTabela).
function atualizarPaginacao(wrapper) {
    const controles = wrapper.querySelector(".paginacao-controles");
    if (!controles) return;

    const tbody = wrapper.querySelector("table tbody");
    const linhasVisiveis = Array.from(tbody.querySelectorAll("tr[data-jogador]")).filter(
        function(linha) { return !linha.classList.contains("linha-oculta"); }
    );

    const total = linhasVisiveis.length;
    const totalPaginas = Math.max(1, Math.ceil(total / PAGINACAO_TAMANHO_PAGINA));

    let paginaAtual = parseInt(wrapper.dataset.paginaAtual, 10) || 1;
    if (paginaAtual > totalPaginas) paginaAtual = totalPaginas;
    if (paginaAtual < 1) paginaAtual = 1;
    wrapper.dataset.paginaAtual = String(paginaAtual);

    const inicio = (paginaAtual - 1) * PAGINACAO_TAMANHO_PAGINA;
    const fim = inicio + PAGINACAO_TAMANHO_PAGINA;

    linhasVisiveis.forEach(function(linha, indice) {
        linha.classList.toggle("linha-pagina-oculta", indice < inicio || indice >= fim);
    });

    controles.querySelector(".paginacao-info").textContent =
        "Página " + paginaAtual + " de " + totalPaginas + " (" + total + " jogadores)";
    controles.querySelector('[data-acao="anterior"]').disabled = paginaAtual <= 1;
    controles.querySelector('[data-acao="proxima"]').disabled = paginaAtual >= totalPaginas;
}

// ===================================================================
// Favoritos (estrela ★, salvos no navegador do usuário via localStorage)
// ===================================================================
// Observação: o localStorage é por navegador/computador, não por arquivo
// importado — se você analisar times diferentes na mesma máquina, os
// favoritos são compartilhados entre eles (mesmo nome de jogador = mesmo
// favorito). Beneficia uso pessoal contínuo, mas vale ter em mente.

const CHAVE_FAVORITOS = "fmScoutingFavoritos";

function obterFavoritos() {
    const salvos = localStorage.getItem(CHAVE_FAVORITOS);
    return salvos ? JSON.parse(salvos) : [];
}

function salvarFavoritos(lista) {
    localStorage.setItem(CHAVE_FAVORITOS, JSON.stringify(lista));
}

// Adiciona/remove um jogador da lista de favoritos e atualiza tudo que
// depende disso na tela: destaque nas linhas, filtro "somente favoritos"
// e o gráfico de dispersão (favoritos aparecem maiores/destacados nele).
function toggleFavorito(nomeJogador) {
    let favoritos = obterFavoritos();

    if (favoritos.includes(nomeJogador)) {
        favoritos = favoritos.filter(function(nome) { return nome !== nomeJogador; });
    } else {
        favoritos.push(nomeJogador);
    }

    salvarFavoritos(favoritos);
    aplicarFavoritos();
    aplicarFiltros();
    renderizarFavoritosNotas();
    atualizarSelectsSomenteFavoritos();

    if (graficoDispersao && window.presetAtivoAtual) {
        const botaoAtivo = document.querySelector(".preset-card.ativo");
        if (botaoAtivo) {
            desenharDispersaoPreset(window.presetAtivoAtual, botaoAtivo);
        }
    }
}

// Aplica visualmente o estado de favorito atual: destaca a linha (CSS
// .linha-favorita) e preenche a estrela (.favorito-estrela.ativa).
// Chamada sempre que a lista de favoritos muda ou a página carrega.
function aplicarFavoritos() {
    const favoritos = obterFavoritos();

    document.querySelectorAll("tr[data-jogador]").forEach(function(linha) {
        const nome = linha.dataset.jogador;
        linha.classList.toggle("linha-favorita", favoritos.includes(nome));
    });

    document.querySelectorAll(".favorito-estrela").forEach(function(botao) {
        const nome = botao.dataset.jogadorEstrela;
        botao.classList.toggle("ativa", favoritos.includes(nome));
    });
}

// "Jogador de referência" (Jogadores Parecidos) e os 3 jogadores do
// Comparador só devem oferecer jogadores já favoritados (★) — a ideia é
// comparar/buscar a partir da sua shortlist, não da base inteira. As
// <option> continuam no DOM (só escondidas via `hidden`/`disabled`), pra
// não perder a lista se o usuário favoritar mais gente depois.
const SELECTS_SOMENTE_FAVORITOS = [
    "parecidos-jogador",
    "comparar-jogador-1", "comparar-jogador-2", "comparar-jogador-3",
];

// Chamada no carregamento da página e sempre que a lista de favoritos
// muda (toggleFavorito). Se o jogador selecionado num desses selects
// deixou de ser favorito (ex: desfavoritado em outra aba), o select volta
// pro "Selecione" e dispara "change" (recalcula o comparador).
function atualizarSelectsSomenteFavoritos() {
    const favoritos = obterFavoritos();
    const temFavoritos = favoritos.length > 0;

    SELECTS_SOMENTE_FAVORITOS.forEach(function(id) {
        const select = document.getElementById(id);
        if (!select) return;

        let valorAindaValido = false;

        Array.from(select.options).forEach(function(opcao) {
            if (opcao.value === "") return; // "Selecione" / "Nenhum" sempre visível
            const visivel = favoritos.includes(opcao.value);
            opcao.hidden = !visivel;
            opcao.disabled = !visivel;
            if (visivel && opcao.value === select.value) {
                valorAindaValido = true;
            }
        });

        if (select.value && !valorAindaValido) {
            select.value = "";
            select.dispatchEvent(new Event("change"));
        }
    });

    ["dica-favoritos-parecidos", "dica-favoritos-comparador"].forEach(function(id) {
        const dica = document.getElementById(id);
        if (dica) dica.classList.toggle("visivel", !temFavoritos);
    });
}

// ===================================================================
// Notas/tags nos favoritos (anotação curta por jogador, salva no
// localStorage do navegador — mesmo local dos favoritos)
// ===================================================================

const CHAVE_NOTAS = "fmScoutingNotas";

// Nome do jogador cuja nota está aberta no modal no momento (null quando o
// modal está fechado). Usado por salvarNotaAtual() para saber em quem
// salvar.
let jogadorNotaAtual = null;

function obterNotas() {
    const salvas = localStorage.getItem(CHAVE_NOTAS);
    return salvas ? JSON.parse(salvas) : {};
}

function salvarNotas(notas) {
    localStorage.setItem(CHAVE_NOTAS, JSON.stringify(notas));
}

// Abre o modal de nota para um jogador, pré-preenchendo com a nota
// existente (se houver). Chamada pelo botão "📝" em qualquer tabela.
function abrirNota(nomeJogador) {
    jogadorNotaAtual = nomeJogador;
    const notas = obterNotas();

    document.getElementById("modal-nota-titulo").textContent = "Nota — " + nomeJogador;
    document.getElementById("modal-nota-texto").value = notas[nomeJogador] || "";
    document.getElementById("modal-nota").classList.add("aberto");
    document.getElementById("modal-nota-texto").focus();
}

function fecharModalNota() {
    document.getElementById("modal-nota").classList.remove("aberto");
    jogadorNotaAtual = null;
}

// Salva (ou remove, se o texto ficou vazio) a nota do jogador atualmente
// aberto no modal, e atualiza tudo que depende disso na tela.
function salvarNotaAtual() {
    if (!jogadorNotaAtual) {
        return;
    }

    const texto = document.getElementById("modal-nota-texto").value.trim();
    const notas = obterNotas();

    if (texto) {
        notas[jogadorNotaAtual] = texto;
    } else {
        delete notas[jogadorNotaAtual];
    }

    salvarNotas(notas);
    atualizarBotoesNota();
    renderizarFavoritosNotas();
    fecharModalNota();
}

// Destaca (classe .tem-nota) os botões "📝" dos jogadores que já têm
// alguma nota salva, para diferenciar visualmente de quem ainda não tem.
function atualizarBotoesNota() {
    const notas = obterNotas();
    document.querySelectorAll(".nota-botao").forEach(function(botao) {
        const nome = botao.dataset.jogadorNota;
        botao.classList.toggle("tem-nota", Boolean(notas[nome]));
    });
}

function configurarModalNota() {
    const salvar = document.getElementById("modal-nota-salvar");
    const cancelar = document.getElementById("modal-nota-cancelar");
    const overlay = document.getElementById("modal-nota");

    if (salvar) salvar.addEventListener("click", salvarNotaAtual);
    if (cancelar) cancelar.addEventListener("click", fecharModalNota);
    if (overlay) {
        // Clicar fora da caixa (no fundo escurecido) também fecha o modal.
        overlay.addEventListener("click", function(evento) {
            if (evento.target === overlay) {
                fecharModalNota();
            }
        });
    }
}

// ===================================================================
// Painel "Favoritos & Notas" — lista todos os jogadores favoritados com
// suas notas, funcionando como uma shortlist de verdade.
// ===================================================================

// (Re)constrói a tabela do painel "Favoritos & Notas" a partir dos
// favoritos e notas salvos no navegador + window.dadosIdentidade (injetado
// pelo backend com clube/idade/etc de cada jogador).
function renderizarFavoritosNotas() {
    const tabela = document.getElementById("tabela-favoritos-notas");
    if (!tabela) {
        return;
    }

    const favoritos = obterFavoritos();
    const notas = obterNotas();

    tabela.innerHTML = "";

    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");
    ["Jogador", "Equipe", "Idade", "Valor", "Nota"].forEach(function(texto, indice) {
        const th = document.createElement("th");
        th.textContent = texto;
        if (indice === 0) th.className = "identidade identidade-fixa";
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");

    if (favoritos.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 5;
        td.textContent = "Nenhum jogador favoritado ainda. Clique na estrela ★ em qualquer tabela para adicionar.";
        td.style.textAlign = "center";
        td.style.color = "#7C8B85";
        tr.appendChild(td);
        tbody.appendChild(tr);
    } else {
        favoritos.forEach(function(nome) {
            const identidade = window.dadosIdentidade[nome] || {};
            const tr = document.createElement("tr");

            const tdNome = document.createElement("td");
            tdNome.textContent = nome;
            tdNome.className = "identidade identidade-fixa";
            tr.appendChild(tdNome);

            const tdEquipe = document.createElement("td");
            tdEquipe.textContent = identidade["Equipe"] || "-";
            tr.appendChild(tdEquipe);

            const tdIdade = document.createElement("td");
            tdIdade.textContent = identidade["Idade"] || "-";
            tr.appendChild(tdIdade);

            const tdValor = document.createElement("td");
            tdValor.textContent = identidade["Valor"] || "-";
            tr.appendChild(tdValor);

            const tdNota = document.createElement("td");
            tdNota.textContent = notas[nome] || "— clique para adicionar —";
            tdNota.style.textAlign = "left";
            tdNota.style.cursor = "pointer";
            tdNota.title = "Clique para editar a nota";
            tdNota.addEventListener("click", function() { abrirNota(nome); });
            tr.appendChild(tdNota);

            tbody.appendChild(tr);
        });
    }

    tabela.appendChild(tbody);
}

// ===================================================================
// Filtros da barra superior (idade, pé, nacionalidade, contrato, favoritos)
// ===================================================================

// Esconde (via CSS .linha-oculta) as linhas de TODAS as tabelas que não
// atendem aos filtros ativos no momento. Roda sempre que qualquer campo
// de filtro muda (ver configurarFiltros) e também quando um favorito é
// alternado (para respeitar o filtro "somente favoritos" em tempo real).
function aplicarFiltros() {
    const idadeMin = parseFloat(document.getElementById("filtro-idade-min").value);
    const idadeMax = parseFloat(document.getElementById("filtro-idade-max").value);
    const somenteFavoritos = document.getElementById("filtro-somente-favoritos").checked;
    const pe = document.getElementById("filtro-pe").value;
    const nac = document.getElementById("filtro-nac").value;
    const anoContrato = parseFloat(document.getElementById("filtro-ano-contrato").value);
    const buscaNome = document.getElementById("filtro-busca-nome").value.trim().toLowerCase();
    const favoritos = obterFavoritos();

    document.querySelectorAll("tr[data-jogador]").forEach(function(linha) {
        const idade = parseFloat(linha.dataset.idade);
        const nome = linha.dataset.jogador;
        const pePreferido = linha.dataset.pe;
        const nacionalidade = linha.dataset.nac;
        const ano = parseFloat(linha.dataset.anoContrato);

        let visivel = true;

        if (!isNaN(idadeMin) && idade < idadeMin) visivel = false;
        if (!isNaN(idadeMax) && idade > idadeMax) visivel = false;
        if (somenteFavoritos && !favoritos.includes(nome)) visivel = false;
        if (pe && pePreferido !== pe) visivel = false;
        if (nac && nacionalidade !== nac) visivel = false;
        if (!isNaN(anoContrato) && ano > anoContrato) visivel = false;
        if (buscaNome && !nome.toLowerCase().includes(buscaNome)) visivel = false;

        linha.classList.toggle("linha-oculta", !visivel);
    });

    // O total de linhas que passam no filtro mudou: volta cada tabela
    // paginada pra página 1 e recalcula os controles sobre o novo total.
    document.querySelectorAll(".tabela-wrapper").forEach(function(wrapper) {
        if (wrapper.querySelector(".paginacao-controles")) {
            wrapper.dataset.paginaAtual = "1";
            atualizarPaginacao(wrapper);
        }
    });
}

// Liga os event listeners de cada campo de filtro (chamado uma vez, no
// carregamento da página) e o botão de "Limpar filtros".
function configurarFiltros() {
    const camposNumero = ["filtro-idade-min", "filtro-idade-max"];
    const camposSelect = ["filtro-pe", "filtro-nac", "filtro-ano-contrato"];
    const camposTexto = ["filtro-busca-nome"];

    camposNumero.forEach(function(id) {
        document.getElementById(id).addEventListener("input", aplicarFiltros);
    });
    camposSelect.forEach(function(id) {
        document.getElementById(id).addEventListener("change", aplicarFiltros);
    });
    camposTexto.forEach(function(id) {
        document.getElementById(id).addEventListener("input", aplicarFiltros);
    });
    document.getElementById("filtro-somente-favoritos").addEventListener("change", aplicarFiltros);

    document.getElementById("filtro-limpar").addEventListener("click", function() {
        camposNumero.forEach(function(id) { document.getElementById(id).value = ""; });
        camposSelect.forEach(function(id) { document.getElementById(id).value = ""; });
        camposTexto.forEach(function(id) { document.getElementById(id).value = ""; });
        document.getElementById("filtro-somente-favoritos").checked = false;
        aplicarFiltros();
    });
}

// ===================================================================
// Jogadores Parecidos (busca por similaridade estatística, via
// POST /jogadores-parecidos)
// ===================================================================

// Liga o botão "Buscar" da aba "Jogadores Parecidos" à função que
// consulta o backend.
function configurarJogadoresParecidos() {
    const botao = document.getElementById("calcular-parecidos");
    if (botao) {
        botao.addEventListener("click", buscarJogadoresParecidos);
    }
}

// ===================================================================
// "Qual perfil combina comigo?" (ranking reverso, via POST /melhor-perfil)
// Reaproveita o mesmo seletor de jogador da aba "Jogadores Parecidos".
// ===================================================================

function configurarMelhorPerfil() {
    const botao = document.getElementById("calcular-melhor-perfil");
    if (botao) {
        botao.addEventListener("click", buscarMelhorPerfil);
    }
}

// Envia o jogador escolhido para POST /melhor-perfil (app.py:
// melhor_perfil), que calcula a "Nota do Perfil" dele em TODOS os perfis
// fixos e devolve ordenado do que mais combina para o que menos combina.
function buscarMelhorPerfil() {
    const jogador = document.getElementById("parecidos-jogador").value;
    if (!jogador) {
        alert("Selecione um jogador de referência.");
        return;
    }

    fetch("/melhor-perfil", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jogador: jogador })
    })
        .then(function(resposta) { return resposta.json(); })
        .then(function(dados) {
            if (dados.erro) {
                alert(dados.erro);
                return;
            }
            renderizarTabelaMelhorPerfil(dados);
        })
        .catch(function(erro) {
            alert("Erro ao calcular o melhor perfil.");
            console.error(erro);
        });
}

// Constrói a tabela "Perfil ideal" a partir do JSON devolvido por
// /melhor-perfil: uma linha por perfil, ordenada da maior para a menor
// nota, com a mesma cor de fundo dourada usada na "Nota do Perfil" das
// tabelas de ranking.
function renderizarTabelaMelhorPerfil(dados) {
    const tabela = document.getElementById("tabela-melhor-perfil");
    tabela.innerHTML = "";

    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");
    ["Perfil", "Nota"].forEach(function(texto, indice) {
        const th = document.createElement("th");
        th.textContent = texto;
        if (indice === 0) th.className = "identidade identidade-fixa";
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");

    dados.resultados.forEach(function(item) {
        const tr = document.createElement("tr");

        const tdPerfil = document.createElement("td");
        tdPerfil.textContent = item.perfil;
        tdPerfil.className = "identidade identidade-fixa";
        tr.appendChild(tdPerfil);

        const tdNota = document.createElement("td");
        tdNota.textContent = item.nota;
        tdNota.style.backgroundColor = "rgba(200, 162, 74, " + (Math.max(item.nota, 0) / 100 * 0.45).toFixed(2) + ")";
        tr.appendChild(tdNota);

        tbody.appendChild(tr);
    });

    tabela.appendChild(tbody);
}

// Envia o jogador de referência escolhido para POST /jogadores-parecidos
// (app.py: jogadores_parecidos), que devolve os jogadores com o perfil
// estatístico mais próximo (ver calcular_similares em scouting/ranking.py).
function buscarJogadoresParecidos() {
    const jogador = document.getElementById("parecidos-jogador").value;
    if (!jogador) {
        alert("Selecione um jogador de referência.");
        return;
    }

    fetch("/jogadores-parecidos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jogador: jogador })
    })
        .then(function(resposta) { return resposta.json(); })
        .then(function(dados) {
            if (dados.erro) {
                alert(dados.erro);
                return;
            }
            renderizarTabelaParecidos(dados);
        })
        .catch(function(erro) {
            alert("Erro ao buscar jogadores parecidos.");
            console.error(erro);
        });
}

// Constrói a tabela de resultado a partir do JSON devolvido pelo backend:
// colunas de identidade do jogador (nome, idade, clube...) + uma coluna
// extra de "Similaridade" (0-100%), com a cor de fundo proporcional ao
// percentual — quanto mais dourado, mais parecido com o jogador de
// referência.
function renderizarTabelaParecidos(dados) {
    const tabela = document.getElementById("tabela-parecidos");
    tabela.innerHTML = "";

    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");

    dados.colunas_identidade.forEach(function(coluna, indice) {
        const th = document.createElement("th");
        th.textContent = coluna;
        if (indice === 0) th.className = "identidade identidade-fixa";
        trHead.appendChild(th);
    });
    const thSim = document.createElement("th");
    thSim.textContent = "Similaridade";
    trHead.appendChild(thSim);

    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");

    dados.registros.forEach(function(registro) {
        const tr = document.createElement("tr");

        dados.colunas_identidade.forEach(function(coluna, i) {
            const td = document.createElement("td");
            td.textContent = registro[coluna];
            if (i === 0) td.className = "identidade identidade-fixa";
            tr.appendChild(td);
        });

        const tdSim = document.createElement("td");
        tdSim.textContent = registro["Similaridade"] + "%";
        tdSim.style.backgroundColor = "rgba(200, 162, 74, " + (registro["Similaridade"] / 100 * 0.45).toFixed(2) + ")";
        tr.appendChild(tdSim);

        tbody.appendChild(tr);
    });

    tabela.appendChild(tbody);
}

// ===================================================================
// Exportar CSV (linhas VISÍVEIS no momento — ou seja, já respeitando os
// filtros aplicados — da tabela ativa)
// ===================================================================

// Escapa um valor de célula para CSV (aspas duplas ao redor quando o
// texto contém vírgula, aspas ou quebra de linha).
function escaparCSV(valor) {
    if (valor.indexOf(",") !== -1 || valor.indexOf('"') !== -1 || valor.indexOf("\n") !== -1) {
        return '"' + valor.replace(/"/g, '""') + '"';
    }
    return valor;
}

// Gera e baixa um CSV a partir da tabela do painel (.tab-painel.ativo) que
// estiver visível no momento, ignorando linhas escondidas pelos filtros
// (.linha-oculta). Funciona tanto nas tabelas renderizadas pelo Jinja
// (categorias/perfis) quanto nas montadas via JavaScript (comparador,
// perfil customizado, parecidos, favoritos & notas).
function exportarTabelaAtivaCSV() {
    const painelAtivo = document.querySelector(".tab-painel.ativo");
    if (!painelAtivo) {
        alert("Nenhuma aba ativa para exportar.");
        return;
    }

    const tabela = painelAtivo.querySelector("table");
    if (!tabela || !tabela.querySelector("thead") || !tabela.querySelector("tbody")) {
        alert("Esta aba não tem uma tabela para exportar.");
        return;
    }

    const cabecalhos = Array.from(tabela.querySelectorAll("thead th")).map(function(th) {
        return th.textContent.trim();
    });

    const linhasVisiveis = Array.from(tabela.querySelectorAll("tbody tr")).filter(function(tr) {
        return !tr.classList.contains("linha-oculta");
    });

    if (linhasVisiveis.length === 0) {
        alert("Não há linhas visíveis para exportar (confira os filtros aplicados).");
        return;
    }

    const linhasCSV = [cabecalhos.map(escaparCSV).join(",")];

    linhasVisiveis.forEach(function(tr) {
        const celulas = Array.from(tr.children).map(function(td, indice) {
            // A primeira célula das tabelas de categoria/perfil tem os
            // botões ★/📝 junto do nome — usa o nome puro (data-jogador)
            // em vez do texto bruto da célula nesse caso.
            if (indice === 0 && tr.dataset.jogador) {
                return escaparCSV(tr.dataset.jogador);
            }
            const texto = td.textContent.replace(/⚠/g, "").trim();
            return escaparCSV(texto);
        });
        linhasCSV.push(celulas.join(","));
    });

    // BOM no início do arquivo garante que o Excel abra acentos/caracteres
    // especiais corretamente (sem isso, "ç", "ã" etc. viram lixo).
    const conteudo = "\uFEFF" + linhasCSV.join("\r\n");
    const blob = new Blob([conteudo], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const tituloPainel = painelAtivo.querySelector(".painel-titulo");
    const nomeArquivo = "fm_scouting_" + (tituloPainel ? tituloPainel.textContent.trim() : "tabela")
        .toLowerCase()
        .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "") + ".csv";

    const link = document.createElement("a");
    link.href = url;
    link.download = nomeArquivo;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function configurarExportarCSV() {
    const botao = document.getElementById("exportar-csv");
    if (botao) {
        botao.addEventListener("click", exportarTabelaAtivaCSV);
    }
}
