// Aplica o tema salvo antes de a página desenhar (evita "piscar" no modo escuro).
(function () {
  var tema = null;
  try { tema = localStorage.getItem("go-tema"); } catch (e) { /* armazenamento indisponível */ }
  if (!tema) {
    tema = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.documentElement.setAttribute("data-bs-theme", tema);
})();
