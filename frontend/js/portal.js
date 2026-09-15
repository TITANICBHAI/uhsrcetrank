(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".nav-toggle").forEach(function (toggle) {
      var nav = toggle.closest(".main-nav");
      toggle.addEventListener("click", function () {
        var expanded = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", String(!expanded));
        nav.classList.toggle("nav-open", !expanded);
      });
    });
  });
})();