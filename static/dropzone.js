// static/dropzone.js
//
// Lógica de drag & drop compartilhada pelas páginas de upload
// (templates/upload.html e templates/elenco.html). As duas seguem a mesma
// estrutura no HTML: um <label class="upload-dropzone"> envolvendo um
// <input type="file"> e um <span> que mostra o nome do arquivo escolhido.
//
// configurarDropzone liga tanto o clique (via <label for="...">, que já
// funciona nativamente) quanto o arrastar-e-soltar, sem duplicar a função
// "atualizar nome do arquivo" entre as duas páginas.
function configurarDropzone(dropzoneEl, inputEl, labelSpanEl, textoPadrao) {
    if (!dropzoneEl || !inputEl || !labelSpanEl) return;

    function atualizarNomeArquivo() {
        labelSpanEl.textContent = inputEl.files.length
            ? inputEl.files[0].name
            : textoPadrao;
    }

    // Clique/seleção normal via o <input type="file">.
    inputEl.addEventListener("change", atualizarNomeArquivo);

    // Realce visual da dropzone enquanto um arquivo é arrastado por cima.
    ["dragover", "dragenter"].forEach(function(evento) {
        dropzoneEl.addEventListener(evento, function(e) {
            e.preventDefault();
            e.stopPropagation();
            dropzoneEl.classList.add("upload-dropzone-ativo");
        });
    });

    ["dragleave", "dragend"].forEach(function(evento) {
        dropzoneEl.addEventListener(evento, function(e) {
            e.preventDefault();
            e.stopPropagation();
            dropzoneEl.classList.remove("upload-dropzone-ativo");
        });
    });

    // Soltar o arquivo: joga ele dentro do <input type="file"> via
    // DataTransfer, pra reaproveitar o mesmo fluxo do <form> normal
    // (inclusive o "change" acima, que atualiza o nome mostrado).
    dropzoneEl.addEventListener("drop", function(e) {
        e.preventDefault();
        e.stopPropagation();
        dropzoneEl.classList.remove("upload-dropzone-ativo");

        const arquivos = e.dataTransfer.files;
        if (arquivos.length) {
            inputEl.files = arquivos;
            atualizarNomeArquivo();
        }
    });
}
