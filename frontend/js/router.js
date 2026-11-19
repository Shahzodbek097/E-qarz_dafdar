/**
 * Hash router.
 *
 * Nega hash? Frontend statik fayllardan iborat va serverda SPA fallback
 * yo'q. `#/debts/12` ko'rinishi sahifa yangilanganda ham ishlaydi.
 */

const routes = [];
let changeHandler = null;

function splitPath(path) {
  return String(path || "/")
    .split("/")
    .filter(Boolean);
}

export function defineRoute(pattern, handler, { public: isPublic = false } = {}) {
  routes.push({
    pattern,
    parts: splitPath(pattern),
    handler,
    public: isPublic,
  });
}

export function matchRoute(path) {
  const parts = splitPath(path);
  for (const route of routes) {
    if (route.parts.length !== parts.length) continue;

    const params = {};
    let matched = true;

    for (let index = 0; index < route.parts.length; index += 1) {
      const expected = route.parts[index];
      const actual = parts[index];

      if (expected.startsWith(":")) {
        params[expected.slice(1)] = decodeURIComponent(actual);
      } else if (expected !== actual) {
        matched = false;
        break;
      }
    }

    if (matched) return { route, params };
  }
  return null;
}

export function currentRoute() {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const [path, queryString = ""] = raw.split("?");
  return {
    path: path || "/",
    query: new URLSearchParams(queryString),
  };
}

function emit() {
  if (changeHandler) changeHandler(currentRoute());
}

export function navigate(path, { replace = false } = {}) {
  const target = `#${path}`;
  if (window.location.hash === target) {
    emit();
    return;
  }

  if (replace) {
    window.history.replaceState(null, "", target);
    emit();
  } else {
    window.location.hash = target;
  }
}

export function startRouter(handler) {
  changeHandler = handler;
  window.addEventListener("hashchange", () => emit());
  emit();
}
