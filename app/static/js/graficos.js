/* Gráficos (Chart.js) do dashboard, da página de relatórios e do fechamento mensal.
   Os dados chegam em <script type="application/json"> para respeitar a CSP (sem script inline). */
(function () {
  "use strict";
  if (typeof Chart === "undefined") return;

  const lerJSON = (id) => {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  };
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const PALETA = ["#2563eb", "#0ea5e9", "#14b8a6", "#22c55e", "#eab308", "#f97316", "#ef4444", "#a855f7", "#64748b"];

  function aplicarTema() {
    Chart.defaults.font.family = "Inter, system-ui, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = css("--go-texto-suave");
    Chart.defaults.borderColor = css("--go-borda");
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
    Object.assign(Chart.defaults.plugins.tooltip, {
      backgroundColor: css("--go-sidebar"), padding: 10, cornerRadius: 8, titleFont: { weight: "600" },
      displayColors: true, boxPadding: 4,
    });
  }
  aplicarTema();

  const graficos = [];
  const eixoY = () => ({ beginAtZero: true, ticks: { precision: 0 }, grid: { color: css("--go-borda") }, border: { display: false } });
  const eixoX = () => ({ grid: { display: false }, border: { display: false } });

  function barras(canvas, rotulos, valores, { horizontal = false, aoClicar = null, rotulo = "Ofícios" } = {}) {
    const g = new Chart(canvas, {
      type: "bar",
      data: { labels: rotulos, datasets: [{ label: rotulo, data: valores, backgroundColor: css("--go-primaria"), borderRadius: 6, maxBarThickness: 34 }] },
      options: {
        indexAxis: horizontal ? "y" : "x", maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: horizontal ? { x: eixoY(), y: eixoX() } : { x: eixoX(), y: eixoY() },
        onClick: (_e, itens) => { if (aoClicar && itens.length) aoClicar(itens[0].index); },
        onHover: (e, itens) => { if (aoClicar) e.native.target.style.cursor = itens.length ? "pointer" : "default"; },
      },
    });
    graficos.push(g);
    return g;
  }

  // ---------- Dashboard ----------
  const serie = lerJSON("dados-serie");
  if (serie) {
    const ctx = document.getElementById("grafico-serie");
    graficos.push(new Chart(ctx, {
      type: "line",
      data: {
        labels: serie.labels,
        datasets: [
          { label: "Criados", data: serie.total, borderColor: css("--go-primaria"), backgroundColor: css("--go-primaria") + "22", fill: true, tension: .35, pointRadius: 3, borderWidth: 2 },
          { label: "Executados", data: serie.executados, borderColor: css("--go-sucesso"), backgroundColor: "transparent", tension: .35, pointRadius: 3, borderWidth: 2, borderDash: [5, 4] },
        ],
      },
      options: { maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, scales: { x: eixoX(), y: eixoY() }, plugins: { legend: { position: "top", align: "end" } } },
    }));
  }

  const status = lerJSON("dados-status");
  if (status) {
    graficos.push(new Chart(document.getElementById("grafico-status"), {
      type: "doughnut",
      data: { labels: ["Executados", "Pendentes"], datasets: [{ data: [status.executados, status.pendentes], backgroundColor: [css("--go-sucesso"), css("--go-alerta")], borderWidth: 0 }] },
      options: { maintainAspectRatio: false, cutout: "72%", plugins: { legend: { position: "bottom" } } },
    }));
  }

  const secretariasDash = lerJSON("dados-secretarias");
  if (secretariasDash) {
    barras(document.getElementById("grafico-secretarias"), secretariasDash.map((s) => s.sigla), secretariasDash.map((s) => s.count));
  }

  // ---------- Fechamento mensal ----------
  const fech = lerJSON("dados-fechamento");
  if (fech) {
    if (fech.secretarias.length) {
      barras(document.getElementById("grafico-fech-secretarias"), fech.secretarias.map((s) => s.sigla), fech.secretarias.map((s) => s.count), { horizontal: true });
    }
    graficos.push(new Chart(document.getElementById("grafico-fech-status"), {
      type: "doughnut",
      data: { labels: ["Executados", "Pendentes"], datasets: [{ data: [fech.executados, fech.pendentes], backgroundColor: [css("--go-sucesso"), css("--go-alerta")], borderWidth: 0 }] },
      options: { maintainAspectRatio: false, cutout: "70%", plugins: { legend: { position: "bottom" } } },
    }));
  }

  // ---------- Relatórios (com detalhamento ao clicar) ----------
  const pagRel = document.getElementById("pagina-relatorios");
  if (pagRel) {
    const filtroMes = document.getElementById("filtro-mes");
    const painel = document.getElementById("painel-detalhe");
    const titulo = document.getElementById("detalhe-titulo");
    const lista = document.getElementById("detalhe-lista");
    let gSec = null;
    let gAss = null;

    const mesSelecionado = () => (filtroMes.value ? `mes=${encodeURIComponent(filtroMes.value)}&` : "");

    function mostrarDetalhe(rotulo, oficios) {
      titulo.textContent = `${rotulo} · ${oficios.length} ofício(s)`;
      lista.replaceChildren();
      if (!oficios.length) {
        lista.innerHTML = '<li class="list-group-item text-muted">Nenhum ofício no período.</li>';
      }
      oficios.forEach((o) => {
        const li = document.createElement("li");
        li.className = "list-group-item d-flex gap-3 align-items-center";
        const a = document.createElement("a");
        a.href = o.url; a.className = "text-decoration-none flex-grow-1";
        a.innerHTML = `<span class="mono fw-semibold me-2"></span><span class="text-body"></span>`;
        a.children[0].textContent = o.numero;
        a.children[1].textContent = o.assunto;
        const badge = document.createElement("span");
        badge.className = `badge-status ${o.status === "Executado" ? "executado" : "pendente"}`;
        badge.textContent = o.status;
        li.append(a, badge);
        lista.appendChild(li);
      });
      painel.hidden = false;
      painel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    async function carregar() {
      const dados = await window.goFetch(`/api/graficos?${mesSelecionado()}`);
      const sec = dados.secretarias.filter((s) => s.count > 0);
      const ass = dados.assessores;
      document.getElementById("total-periodo").textContent = sec.reduce((t, s) => t + s.count, 0);

      gSec?.destroy(); gAss?.destroy();
      gSec = barras(document.getElementById("grafico-rel-secretarias"), sec.map((s) => s.sigla), sec.map((s) => s.count), {
        aoClicar: async (i) => {
          const r = await window.goFetch(`/api/oficios-por-secretaria?${mesSelecionado()}sigla=${encodeURIComponent(sec[i].sigla)}`);
          mostrarDetalhe(r.secretaria.nome, r.oficios);
        },
      });
      gAss = barras(document.getElementById("grafico-rel-assessores"), ass.map((a) => a.nome), ass.map((a) => a.count), {
        horizontal: true,
        aoClicar: async (i) => {
          const r = await window.goFetch(`/api/oficios-por-assessor?${mesSelecionado()}nome=${encodeURIComponent(ass[i].nome)}`);
          mostrarDetalhe(ass[i].nome, r.oficios);
        },
      });
    }

    filtroMes.addEventListener("change", () => { painel.hidden = true; carregar(); });
    carregar().catch((e) => window.goToast(e.message, "danger"));
  }

  // Redesenha ao trocar o tema
  document.addEventListener("go:tema", () => {
    aplicarTema();
    graficos.forEach((g) => {
      g.data.datasets.forEach((ds) => {
        if (g.config.type === "bar") ds.backgroundColor = css("--go-primaria");
      });
      ["x", "y"].forEach((eixo) => { if (g.options.scales?.[eixo]?.grid?.color) g.options.scales[eixo].grid.color = css("--go-borda"); });
      g.update();
    });
  });

  window.GO_PALETA = PALETA;
})();
