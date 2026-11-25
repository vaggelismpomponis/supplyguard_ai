/*
 * SupplyGuard AI - login page enhancements for Chainlit 2.12.
 *
 * Chainlit's login page has no stable ids, so on the /login route this script tags its elements
 * with .sg-login* classes (styled in public/custom.css) and fills the image column with a brand
 * panel: a schematic route map and a sample case manifest (a disrupted lane and its recovery
 * route). It never touches auth: the form, inputs and submit handler stay Chainlit's own. All
 * injected markup is static; no page or user data is inserted.
 */
(function () {
  "use strict";

  var STRINGS = {
    en: {
      eyebrow: "Control tower access",
      title: "Sign in to SupplyGuard AI",
      subtitle: "Use your operator account to continue.",
      userLabel: "Username or email",
      userPlaceholder: "name.surname",
      tag: "Control tower",
      lede: "Disruption to recovery, with human sign-off.",
      headline: "When a supplier slips, <em>find the way around it.</em>",
      mapLabel:
        "Example route map: the Kaohsiung to plant F2 lane is blocked at Singapore and rerouted by air via Busan and Frankfurt.",
      manifest: [
        ["CASE", "MC-17 · Atlas Components", ""],
        ["EVENT", "KHH → RTM lane blocked · +12 days", "is-delay"],
        ["PLAN", "Reroute via PUS → FRA (air) · €48,200", "is-plan"],
        ["STATUS", "Awaiting human approval", "is-status"],
      ],
      delay: "DELAY +12D",
      foot: "Human sign-off on every purchase order · €75,000 cap",
      note: "Authorized personnel only · role-based access",
    },
    el: {
      eyebrow: "Πρόσβαση στο κέντρο ελέγχου",
      title: "Σύνδεση στο SupplyGuard AI",
      subtitle: "Συνδεθείτε με τον λογαριασμό χειριστή σας.",
      userLabel: "Όνομα χρήστη ή email",
      userPlaceholder: "onoma.eponymo",
      tag: "Κέντρο ελέγχου",
      lede: "Από τη διαταραχή στην ανάκαμψη, με ανθρώπινη έγκριση.",
      headline: "Όταν ένας προμηθευτής καθυστερεί, <em>βρείτε την παράκαμψη.</em>",
      mapLabel:
        "Παράδειγμα χάρτη: η διαδρομή Kaohsiung προς εργοστάσιο F2 μπλοκάρεται στη Σιγκαπούρη και αναδρομολογείται αεροπορικώς μέσω Busan και Φρανκφούρτης.",
      manifest: [
        ["ΥΠΟΘΕΣΗ", "MC-17 · Atlas Components", ""],
        ["ΣΥΜΒΑΝ", "Διαδρομή KHH → RTM μπλοκαρισμένη · +12 ημέρες", "is-delay"],
        ["ΣΧΕΔΙΟ", "Αναδρομολόγηση μέσω PUS → FRA (αεροπορικώς) · €48.200", "is-plan"],
        ["ΚΑΤΑΣΤΑΣΗ", "Αναμένει ανθρώπινη έγκριση", "is-status"],
      ],
      delay: "ΚΑΘΥΣΤΕΡΗΣΗ +12Η",
      foot: "Ανθρώπινη έγκριση σε κάθε παραγγελία · όριο €75.000",
      note: "Μόνο για εξουσιοδοτημένους χρήστες · πρόσβαση βάσει ρόλου",
    },
  };

  // Chainlit follows the browser language when [UI].language is unset.
  var lang = (navigator.language || "en").toLowerCase().indexOf("el") === 0 ? "el" : "en";
  var T = STRINGS[lang];

  var ROUTE = "M20 140 C50 140 70 60 110 60 L410 60 C450 60 470 140 500 140";

  function stop(x, y, code, city, route) {
    var labelY = route ? y - 16 : y + 26;
    var cityY = route ? y - 30 : y + 40;
    return (
      '<circle class="sg-map__stop' + (route ? " sg-map__stop--route" : "") + '" cx="' + x + '" cy="' + y + '" r="5"/>' +
      '<text class="sg-map__label' + (route ? " sg-map__label--route" : "") + '" x="' + x + '" y="' + labelY +
      '" text-anchor="middle">' + code + "</text>" +
      '<text class="sg-map__label sg-map__label--dim" x="' + x + '" y="' + cityY + '" text-anchor="middle">' + city + "</text>"
    );
  }

  // Schematic lane: Kaohsiung -> Singapore -> Rotterdam -> plant F2, blocked after Singapore,
  // with the recovery route flown via Busan and Frankfurt.
  function mapSvg() {
    return (
      '<svg class="sg-brand__map" xmlns="http://www.w3.org/2000/svg" viewBox="0 -10 520 200" role="img" aria-label="' +
      T.mapLabel + '">' +
      '<path class="sg-map__lane" d="M20 140 H150"/>' +
      '<path class="sg-map__lane sg-map__lane--blocked" d="M150 140 H494"/>' +
      '<path class="sg-map__lane sg-map__lane--route" d="' + ROUTE + '"/>' +
      stop(20, 140, "KHH", "Kaohsiung") +
      stop(150, 140, "SIN", "Singapore") +
      stop(370, 140, "RTM", "Rotterdam") +
      stop(160, 60, "PUS", "Busan · air", true) +
      stop(380, 60, "FRA", "Frankfurt", true) +
      '<rect class="sg-map__factory" x="494" y="134" width="12" height="12" rx="1"/>' +
      '<text class="sg-map__label" x="500" y="166" text-anchor="middle">F2</text>' +
      '<text class="sg-map__label sg-map__label--dim" x="500" y="180" text-anchor="middle">Plant</text>' +
      '<circle class="sg-map__x-ring" cx="260" cy="140" r="10"/>' +
      '<path class="sg-map__x" d="M255.5 135.5 l9 9 M264.5 135.5 l-9 9"/>' +
      '<text class="sg-map__label sg-map__label--delay" x="260" y="118" text-anchor="middle">' + T.delay + "</text>" +
      '<circle class="sg-map__pulse" r="3.5"><animateMotion dur="7s" repeatCount="indefinite" path="' + ROUTE +
      '"/></circle>' +
      "</svg>"
    );
  }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  }

  function buildBrand() {
    var root = el("div", "sg-brand");

    var top = el("div", "sg-brand__top");
    var lockup = el("div", "sg-brand__lockup");
    var logo = el("img", "sg-brand__logo");
    logo.src = "/public/logo_dark.png"; // white badge variant reads well on the navy panel
    logo.alt = "";
    lockup.appendChild(logo);
    lockup.appendChild(el("span", "sg-brand__name", "SupplyGuard AI"));
    top.appendChild(lockup);
    top.appendChild(el("span", "sg-brand__tag", T.tag));
    root.appendChild(top);
    root.appendChild(el("p", "sg-brand__lede", T.lede));

    var main = el("div", "sg-brand__main");
    var headline = el("h2", "sg-brand__headline");
    headline.innerHTML = T.headline; // static string from STRINGS above
    main.appendChild(headline);
    main.insertAdjacentHTML("beforeend", mapSvg());

    var manifest = el("dl", "sg-brand__manifest");
    T.manifest.forEach(function (row) {
      manifest.appendChild(el("dt", "", row[0]));
      manifest.appendChild(el("dd", row[2], row[1]));
    });
    main.appendChild(manifest);
    root.appendChild(main);

    root.appendChild(el("p", "sg-brand__foot", T.foot));
    return root;
  }

  function setText(node, text) {
    if (node && node.textContent !== text) node.textContent = text;
  }

  function isLoginRoute() {
    return /\/login\/?$/.test(window.location.pathname);
  }

  function enhance() {
    if (!isLoginRoute()) return;
    var email = document.getElementById("email");
    var form = email && email.closest("form");
    var grid = form && form.closest(".min-h-svh");
    if (!grid) return;

    grid.classList.add("sg-login");
    // Scoped so Greek all-caps labels drop their accents (CSS text-transform is language-aware).
    if (grid.getAttribute("lang") !== lang) grid.setAttribute("lang", lang);
    var main = grid.children[0];
    var brand = grid.children[1]; // absent when header auth is used
    if (main) {
      main.classList.add("sg-login__main");
      if (main.children[0]) main.children[0].classList.add("sg-login__toprow");
      if (main.children[1]) main.children[1].classList.add("sg-login__center");
    }
    if (brand && brand !== main && !brand.querySelector(".sg-brand")) {
      brand.classList.add("sg-login__brand");
      brand.appendChild(buildBrand());
    }

    var card = form.parentElement;
    card.classList.add("sg-login__card");
    if (!card.querySelector(".sg-login__note")) {
      card.appendChild(el("p", "sg-login__note", T.note));
    }

    var h1 = form.querySelector("h1");
    if (h1) {
      setText(h1, T.title);
      var heading = h1.parentElement;
      heading.classList.add("sg-login__heading");
      if (!heading.querySelector(".sg-login__eyebrow")) {
        heading.insertBefore(el("p", "sg-login__eyebrow", T.eyebrow), h1);
      }
      if (!heading.querySelector(".sg-login__subtitle")) {
        heading.appendChild(el("p", "sg-login__subtitle", T.subtitle));
      }
    }

    setText(form.querySelector('label[for="email"]'), T.userLabel);
    if (email.placeholder !== T.userPlaceholder) email.placeholder = T.userPlaceholder;
    email.setAttribute("autocomplete", "username");
    var password = document.getElementById("password");
    if (password) password.setAttribute("autocomplete", "current-password");
  }

  var scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(function () {
      scheduled = false;
      enhance();
    });
  }

  function start() {
    enhance();
    // React renders and re-renders the login page asynchronously (and on logout navigation).
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
