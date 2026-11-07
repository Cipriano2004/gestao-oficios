/* Formulário de ofício: assistente em passos, secretários e modelos por secretaria, chips de placeholder. */
(function () {
  "use strict";
  const form = document.getElementById("form-oficio");
  if (!form) return;

  const selDep = form.querySelector("#departamento_id");
  const selSec = form.querySelector("#secretario_id");
  const listaModelos = document.getElementById("lista-modelos");
  const assunto = form.querySelector("#assunto");
  const corpo = form.querySelector("#corpo_oficio");
  const secInicial = selSec?.dataset.inicial || "";

  // ---------- Passos ----------
  const passos = [...form.querySelectorAll(".passo")];
  const indicadores = [...document.querySelectorAll(".stepper li")];
  let atual = 0;

  function irPara(i) {
    atual = Math.max(0, Math.min(i, passos.length - 1));
    passos.forEach((p, j) => { p.hidden = j !== atual; });
    indicadores.forEach((li, j) => {
      li.classList.toggle("ativo", j === atual);
      li.classList.toggle("feito", j < atual);
      li.setAttribute("aria-current", j === atual ? "step" : "false");
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function validarPasso(i) {
    const campos = [...passos[i].querySelectorAll("input, select, textarea")];
    for (const c of campos) {
      if (!c.checkValidity()) { c.reportValidity(); return false; }
    }
    return true;
  }

  form.querySelectorAll("[data-proximo]").forEach((b) => b.addEventListener("click", () => { if (validarPasso(atual)) irPara(atual + 1); }));
  form.querySelectorAll("[data-anterior]").forEach((b) => b.addEventListener("click", () => irPara(atual - 1)));
  if (passos.length > 1) {
    // se o servidor devolveu o formulário com erro, abre no último passo preenchido
    irPara(form.dataset.passoInicial ? Number(form.dataset.passoInicial) : 0);
  }

  // ---------- Secretários e modelos ----------
  async function carregarSecretarios(depId) {
    if (!selSec) return;
    selSec.innerHTML = '<option value="">Carregando…</option>';
    if (!depId) { selSec.innerHTML = '<option value="">Selecione a secretaria primeiro</option>'; return; }
    try {
      const dados = await window.goFetch(`/oficios/api/secretarios/${depId}`);
      selSec.replaceChildren(new Option("Selecione o destinatário", ""));
      dados.secretarios.forEach((s) => {
        const op = new Option(`${s.nome} — ${s.cargo}`, s.id);
        if (String(s.id) === String(secInicial)) op.selected = true;
        selSec.appendChild(op);
      });
      if (dados.secretarios.length === 1 && !selSec.value) selSec.selectedIndex = 1;
    } catch (e) {
      window.goToast(e.message, "danger");
    }
  }

  async function carregarModelos(depId) {
    if (!listaModelos) return;
    listaModelos.replaceChildren();
    if (!depId) {
      listaModelos.innerHTML = '<p class="text-muted small mb-0">Escolha a secretaria para ver os modelos disponíveis.</p>';
      return;
    }
    const dados = await window.goFetch(`/oficios/api/modelos/${depId}`);
    if (!dados.modelos.length) {
      listaModelos.innerHTML = '<p class="text-muted small mb-0">Nenhum modelo para esta secretaria. Você pode escrever o texto livremente.</p>';
      return;
    }
    dados.modelos.forEach((m) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "modelo-opcao";
      b.innerHTML = "<strong></strong><span></span>";
      b.querySelector("strong").textContent = m.titulo;
      b.querySelector("span").textContent = m.assunto;
      b.addEventListener("click", () => {
        if ((assunto.value || corpo.value) && !confirm("Substituir o assunto e o texto atuais pelo modelo?")) return;
        assunto.value = m.assunto;
        corpo.value = m.corpo_texto;
        listaModelos.querySelectorAll(".modelo-opcao").forEach((x) => x.classList.remove("selecionado"));
        b.classList.add("selecionado");
        window.goToast(`Modelo "${m.titulo}" aplicado.`, "info");
      });
      const col = document.createElement("div");
      col.className = "col-md-6";
      col.appendChild(b);
      listaModelos.appendChild(col);
    });
  }

  selDep?.addEventListener("change", () => {
    carregarSecretarios(selDep.value);
    carregarModelos(selDep.value).catch((e) => window.goToast(e.message, "danger"));
  });
  if (selDep?.value) {
    carregarSecretarios(selDep.value);
    carregarModelos(selDep.value).catch(() => {});
  }

  // ---------- Inserir placeholder no campo focado ----------
  let ultimoCampo = corpo;
  [assunto, corpo].forEach((c) => c?.addEventListener("focus", () => { ultimoCampo = c; }));
  document.querySelectorAll("button.chip-ph").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (!ultimoCampo) return;
      const ini = ultimoCampo.selectionStart ?? ultimoCampo.value.length;
      const fim = ultimoCampo.selectionEnd ?? ini;
      ultimoCampo.setRangeText(chip.dataset.ph, ini, fim, "end");
      ultimoCampo.focus();
    });
  });
})();
