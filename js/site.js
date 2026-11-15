(function () {
  var els = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    els.forEach(function (e) { e.classList.add("in"); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var el = entry.target;
      var group = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
      el.style.transitionDelay = Math.min(group, 6) * 70 + "ms";
      el.classList.add("in");
      io.unobserve(el);
    });
  }, { threshold: 0.14, rootMargin: "0px 0px -8% 0px" });
  els.forEach(function (e) { io.observe(e); });
})();

(function () {
  var bar = document.querySelector(".topbar");
  var btn = document.querySelector(".nav-toggle");
  if (!bar || !btn) return;
  btn.addEventListener("click", function () {
    var open = bar.classList.toggle("is-open");
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
})();
