/* Comportamentos globais: tema, sidebar, toasts, confirmações e requisições com CSRF. */
(function () {
  "use strict";

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";

  // Requisição JSON com token CSRF
  window.goFetch = async function (url, opcoes = {}) {
    const resp = await fetch(url, {
      credentials: "same-origin",
      ...opcoes,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
        Accept: "application/json",
        ...(opcoes.headers || {}),
      },
    });
    const dados = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(dados.erro || `Erro ${resp.status}`);
    return dados;
  };

  // Toast simples
  window.goToast = function (mensagem, tipo = "success") {
    const cores = { success: "var(--go-sucesso)", danger: "var(--go-perigo)", warning: "var(--go-alerta)", info: "var(--go-primaria)" };
    const icones = { success: "check-circle-fill", danger: "x-circle-fill", warning: "exclamation-triangle-fill", info: "info-circle-fill" };
    const area = document.getElementById("toasts");
    if (!area) return;
    const el = document.createElement("div");
    el.className = "toast align-items-stretch";
    el.setAttribute("role", tipo === "danger" ? "alert" : "status");
    el.setAttribute("aria-live", "polite");
    el.innerHTML = `<div class="d-flex"><div class="barra"></div><div class="toast-body d-flex gap-2 align-items-start">
        <i class="bi bi-${icones[tipo] || icones.info} mt-1"></i><span></span></div>
        <button type="button" class="btn-close m-2 ms-auto" data-bs-dismiss="toast" aria-label="Fechar"></button></div>`;
    el.querySelector(".barra").style.background = cores[tipo] || cores.info;
    el.querySelector("i").style.color = cores[tipo] || cores.info;
    el.querySelector("span").textContent = mensagem;
    area.appendChild(el);
    const t = new bootstrap.Toast(el, { delay: 5000 });
    el.addEventListener("hidden.bs.toast", () => el.remove());
    t.show();
  };

  document.addEventListener("DOMContentLoaded", () => {
    // Mensagens flash do servidor viram toasts
    document.querySelectorAll("[data-flash]").forEach((el) => {
      window.goToast(el.dataset.flash, el.dataset.tipo || "info");
      el.remove();
    });

    // Alternar tema claro/escuro
    document.querySelectorAll("[data-alternar-tema]").forEach((botao) => {
      botao.addEventListener("click", () => {
        const atual = document.documentElement.getAttribute("data-bs-theme");
        const novo = atual === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-bs-theme", novo);
        try { localStorage.setItem("go-tema", novo); } catch (e) { /* ignora */ }
        document.dispatchEvent(new CustomEvent("go:tema", { detail: novo }));
      });
    });

    // Sidebar no celular
    const sidebar = document.querySelector(".sidebar");
    const fundo = document.querySelector(".sidebar-fundo");
    const alternarSidebar = (abrir) => {
      sidebar?.classList.toggle("aberta", abrir);
      fundo?.classList.toggle("visivel", abrir);
    };
    document.querySelectorAll("[data-abrir-menu]").forEach((b) => b.addEventListener("click", () => alternarSidebar(true)));
    fundo?.addEventListener("click", () => alternarSidebar(false));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") alternarSidebar(false); });

    // Confirmação antes de enviar formulários destrutivos: <form data-confirmar="Mensagem">
    const modalEl = document.getElementById("modalConfirmar");
    const modal = modalEl ? new bootstrap.Modal(modalEl) : null;
    let formPendente = null;
    document.querySelectorAll("form[data-confirmar]").forEach((form) => {
      form.addEventListener("submit", (e) => {
        if (form.dataset.confirmado === "1" || !modal) return;
        e.preventDefault();
        formPendente = form;
        modalEl.querySelector("[data-msg]").textContent = form.dataset.confirmar;
        modalEl.querySelector("[data-titulo]").textContent = form.dataset.titulo || "Confirmar ação";
        modal.show();
      });
    });
    modalEl?.querySelector("[data-ok]").addEventListener("click", () => {
      if (!formPendente) return;
      formPendente.dataset.confirmado = "1";
      modal.hide();
      formPendente.requestSubmit();
    });

    // Linhas de tabela clicáveis
    document.querySelectorAll("tr[data-href]").forEach((tr) => {
      tr.addEventListener("click", (e) => {
        if (e.target.closest("a, button, input, label, form, .dropdown")) return;
        window.location = tr.dataset.href;
      });
    });

    // Switch "executado" (AJAX)
    document.querySelectorAll("input[data-executado-url]").forEach((input) => {
      input.addEventListener("change", async () => {
        const marcado = input.checked;
        input.disabled = true;
        try {
          await window.goFetch(input.dataset.executadoUrl, { method: "POST", body: JSON.stringify({ executado: marcado }) });
          const badge = document.querySelector(`[data-badge-oficio="${input.dataset.oficioId}"]`);
          if (badge) {
            badge.className = `badge-status ${marcado ? "executado" : "pendente"}`;
            badge.textContent = marcado ? "Executado" : "Pendente";
          }
          window.goToast(marcado ? "Ofício marcado como executado." : "Ofício voltou para pendente.", "success");
        } catch (erro) {
          input.checked = !marcado;
          window.goToast(erro.message, "danger");
        } finally {
          input.disabled = false;
        }
      });
    });

    // Selects que enviam o formulário ao mudar
    document.querySelectorAll("[data-auto-submit]").forEach((el) => el.addEventListener("change", () => el.form.requestSubmit()));

    // Botão imprimir
    document.querySelectorAll("[data-imprimir]").forEach((b) => b.addEventListener("click", () => window.print()));
  });
})();
