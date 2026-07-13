/*
 * JavaScript da tela "Meu Time" (templates/elenco.html).
 *
 * Envia a comparação escolhida (jogador escoutado x jogador específico
 * do elenco, ou x média do elenco) para POST /elenco/comparar e
 * renderiza o resultado: a "Nota do Perfil" do candidato recalculada
 * tendo o elenco como grupo de referência, e uma tabela métrica a
 * métrica logo abaixo.
 */

// Mostra o <select> de "jogador específico do elenco" só quando esse
// modo de comparação está selecionado; no modo "média" ele fica
// escondido (e não é enviado na requisição).
function configurarModoComparacaoElenco() {
    const selectModo = document.getElementById("elenco-modo");
    const campoJogadorEspecifico = document.getElementById("elenco-campo-jogador-especifico");
    if (!selectModo || !campoJogadorEspecifico) {
        return;
    }

    function atualizarVisibilidade() {
        campoJogadorEspecifico.style.display = selectModo.value === "jogador" ? "block" : "none";
    }

    selectModo.addEventListener("change", atualizarVisibilidade);
    atualizarVisibilidade();
}

function compararComElenco() {
    const jogadorScout = document.getElementById("elenco-jogador-scout").value;
    const modo = document.getElementById("elenco-modo").value;
    const selectJogadorElenco = document.getElementById("elenco-jogador-elenco");
    const jogadorElenco = selectJogadorElenco ? selectJogadorElenco.value : "";

    if (!jogadorScout) {
        alert("Selecione um jogador escoutado.");
        return;
    }
    if (modo === "jogador" && !jogadorElenco) {
        alert("Selecione um jogador do elenco para comparar.");
        return;
    }

    const corpo = { jogador_scout: jogadorScout, modo: modo };
    if (modo === "jogador") {
        corpo.jogador_elenco = jogadorElenco;
    }

    fetch("/elenco/comparar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo),
    })
        .then(function(resposta) { return resposta.json(); })
        .then(function(dados) {
            if (dados.erro) {
                alert(dados.erro);
                return;
            }
            renderizarComparacaoElenco(dados);
        })
        .catch(function(erro) {
            alert("Erro ao comparar com o elenco.");
            console.error(erro);
        });
}

// Nome da coluna de comparação: o nome do jogador do elenco (modo
// "jogador") ou "Média do Elenco" (modo "media").
function tituloColunaComparacao(dados) {
    return dados.modo === "jogador" ? dados.jogador_elenco : "Média do Elenco";
}

function renderizarNotasPorPerfil(dados, container) {
    if (!dados.notas_por_perfil.length) {
        return;
    }

    const titulo = document.createElement("h3");
    titulo.className = "painel-titulo";
    titulo.textContent = "Nota do Perfil (comparada ao elenco)";
    container.appendChild(titulo);

    const grade = document.createElement("div");
    grade.className = "elenco-notas-grade";

    dados.notas_por_perfil.forEach(function(item) {
        const cartao = document.createElement("div");
        cartao.className = "elenco-nota-cartao";

        const nomePerfil = document.createElement("div");
        nomePerfil.className = "elenco-nota-perfil";
        nomePerfil.textContent = item.perfil;
        cartao.appendChild(nomePerfil);

        const nota = document.createElement("div");
        nota.className = "elenco-nota-valor";
        nota.textContent = item.nota_jogador;
        cartao.appendChild(nota);

        const referencia = document.createElement("div");
        referencia.className = "elenco-nota-referencia";
        const partes = [];
        if (item.nota_media_elenco !== null && item.nota_media_elenco !== undefined) {
            partes.push("média do elenco: " + item.nota_media_elenco);
        }
        if (item.nota_melhor_elenco !== null && item.nota_melhor_elenco !== undefined) {
            partes.push("melhor do elenco: " + item.nota_melhor_elenco);
        }
        referencia.textContent = partes.join(" · ");
        cartao.appendChild(referencia);

        if (item.nota_media_elenco !== null && item.nota_media_elenco !== undefined) {
            cartao.classList.add(item.nota_jogador >= item.nota_media_elenco ? "delta-positivo" : "delta-negativo");
        }

        grade.appendChild(cartao);
    });

    container.appendChild(grade);
}

function renderizarMetricas(dados, container) {
    const categorias = Object.keys(dados.metricas);
    if (!categorias.length) {
        return;
    }

    const titulo = document.createElement("h3");
    titulo.className = "painel-titulo";
    titulo.textContent = "Métrica a métrica";
    container.appendChild(titulo);

    const wrapper = document.createElement("div");
    wrapper.className = "tabela-wrapper";

    const tabela = document.createElement("table");
    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");

    ["Métrica", dados.jogador_scout, tituloColunaComparacao(dados)].forEach(function(texto, indice) {
        const th = document.createElement("th");
        th.textContent = texto;
        if (indice === 0) th.className = "identidade identidade-fixa";
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");

    categorias.forEach(function(categoria) {
        const trCategoria = document.createElement("tr");
        const tdCategoria = document.createElement("td");
        tdCategoria.textContent = categoria;
        tdCategoria.colSpan = 3;
        tdCategoria.className = "comparador-categoria";
        trCategoria.appendChild(tdCategoria);
        tbody.appendChild(trCategoria);

        dados.metricas[categoria].forEach(function(linha) {
            const tr = document.createElement("tr");

            const tdMetrica = document.createElement("td");
            tdMetrica.textContent = linha.coluna;
            tdMetrica.className = "identidade identidade-fixa";
            tr.appendChild(tdMetrica);

            const tdScout = document.createElement("td");
            tdScout.textContent = linha.scout;
            if (linha.melhor === "scout") tdScout.classList.add("delta-positivo");
            tr.appendChild(tdScout);

            const tdComparacao = document.createElement("td");
            tdComparacao.textContent = linha.comparacao;
            if (linha.melhor === "comparacao") tdComparacao.classList.add("delta-positivo");
            tr.appendChild(tdComparacao);

            tbody.appendChild(tr);
        });
    });

    tabela.appendChild(tbody);
    wrapper.appendChild(tabela);
    container.appendChild(wrapper);
}

function renderizarComparacaoElenco(dados) {
    const container = document.getElementById("resultado-comparacao-elenco");
    container.innerHTML = "";

    renderizarNotasPorPerfil(dados, container);
    renderizarMetricas(dados, container);
}

document.addEventListener("DOMContentLoaded", function() {
    configurarModoComparacaoElenco();

    const botaoComparar = document.getElementById("elenco-comparar-botao");
    if (botaoComparar) {
        botaoComparar.addEventListener("click", compararComElenco);
    }
});
