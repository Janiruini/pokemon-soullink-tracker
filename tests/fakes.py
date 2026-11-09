"""Nachbauten von Firebase (Firestore) und Streamlit für die automatischen Prüfungen.

Damit läuft die komplette App ohne Internet, ohne echtes Firebase und ohne installiertes Streamlit:
- FakeDB: eine Datenbank im Arbeitsspeicher, die Lesevorgänge so zählt, wie Firebase sie abrechnet.
- App: führt web_app.py aus, merkt sich alle gezeichneten Elemente und kann Klicks/Eingaben simulieren.
"""
import sys, types, copy, itertools, runpy

# ---------------- Firestore ----------------
class Snap:
    def __init__(self, id, data):
        self.id = id; self._d = data
    @property
    def exists(self): return self._d is not None
    def to_dict(self): return copy.deepcopy(self._d) if self._d is not None else None

def deep_merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge(a[k], v)
        else:
            a[k] = copy.deepcopy(v)

class DocRef:
    def __init__(self, store, coll, id): self.s, self.c, self.id = store, coll, id
    def get(self): LESEN[0] += 1; return Snap(self.id, self.s[self.c].get(self.id))
    def update(self, data):
        if self.id not in self.s[self.c]: raise Exception("NotFound: kein Dokument " + self.id)
        self.s[self.c][self.id].update(copy.deepcopy(data)); notify()
    def set(self, data, merge=False):
        if merge and self.id in self.s[self.c]: deep_merge(self.s[self.c][self.id], data)
        else: self.s[self.c][self.id] = copy.deepcopy(data)
    def delete(self): self.s[self.c].pop(self.id, None); notify()

class Query:
    def __init__(self, store, coll, filters=()): self.s, self.c, self.f = store, coll, list(filters)
    def where(self, field, op, val):
        assert op == "=="; return Query(self.s, self.c, self.f + [(field, val)])
    def _docs(self):
        return [Snap(id, d) for id, d in list(self.s[self.c].items()) if all(d.get(f) == v for f, v in self.f)]
    def stream(self):
        for snap in self._docs():
            LESEN[0] += 1   # Firebase berechnet jeden gelesenen Eintrag
            yield snap
    def get(self): return list(self.stream())
    def on_snapshot(self, cb):
        docs = self._docs(); LESEN[0] += len(docs)   # Anfangszustand wird einmal berechnet
        WATCHERS.append((self, cb)); cb(docs, None, None); return object()

LESEN = [0]
_ids = itertools.count(1)
WATCHERS = []
def notify():
    # Firebase berechnet bei Listenern nur geänderte Einträge: ~1 pro Änderung und Listener
    for q, cb in list(WATCHERS):
        LESEN[0] += 1; cb(q._docs(), None, None)
class Coll(Query):
    def document(self, id): return DocRef(self.s, self.c, id)
    def add(self, data):
        id = f"doc{next(_ids)}"; self.s[self.c][id] = copy.deepcopy(data); notify(); return (None, DocRef(self.s, self.c, id))

class FakeDB:
    def __init__(self): self.store = {"links": {}, "runs": {}}
    def collection(self, name):
        self.store.setdefault(name, {}); return Coll(self.store, name)

DB = FakeDB()

def install_firebase():
    fa = types.ModuleType("firebase_admin"); fa._apps = {"[DEFAULT]": object()}
    fa.initialize_app = lambda *a, **k: None
    cred = types.ModuleType("firebase_admin.credentials"); cred.Certificate = lambda x: x
    fs = types.ModuleType("firebase_admin.firestore"); fs.client = lambda: DB
    fa.credentials, fa.firestore = cred, fs
    sys.modules.update({"firebase_admin": fa, "firebase_admin.credentials": cred, "firebase_admin.firestore": fs})

# ---------------- Streamlit ----------------
class Rerun(Exception): pass

class State(dict):
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)
    def __setattr__(self, k, v): self[k] = v
    def __delattr__(self, k): del self[k]

class Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False

class FakeST(Ctx):
    def __init__(self, app, where="main"): self.app, self.where = app, where
    # Ausgabe
    def _log(self, kind, text): self.app.log.append((self.where, kind, str(text)))
    def markdown(self, t, **k): self._log("md", t)
    def title(self, t): self._log("title", t)
    def caption(self, t): self._log("caption", t)
    def success(self, t): self._log("success", t)
    def warning(self, t): self._log("warning", t)
    def error(self, t): self._log("error", t)
    def info(self, t): self._log("info", t)
    def write(self, t): self._log("md", t)
    def image(self, p, **k): self._log("image", p)
    def metric(self, label, value): self._log("metric", f"{label}={value}")
    def divider(self): pass
    def set_page_config(self, **k): pass
    def spinner(self, t): return Ctx()
    def rerun(self): raise Rerun()
    # Layout
    def columns(self, spec, **k): self._log("columns", str(spec)); n = spec if isinstance(spec, int) else len(spec); return [FakeST(self.app, self.where) for _ in range(n)]
    def container(self, **k):
        if k.get("key"): self._log("container", k["key"])
        return FakeST(self.app, self.where)
    def expander(self, label, **k): self._log("expander", label); return FakeST(self.app, self.where)
    def popover(self, label, **k): self._log("popover", label); return FakeST(self.app, self.where)
    def form(self, key, **k):
        assert key not in self.app.forms_this_run, f"Formular-Key doppelt: {key}"
        self.app.forms_this_run.add(key); return FormCtx(self.app, key)
    def tabs(self, labels): self._log("tabs", " | ".join(labels)); return [FakeST(self.app, self.where) for _ in labels]
    # Widgets
    def _widget(self, key, label, default, on_change=None, args=()):
        k = key or f"auto_{label}"
        assert k not in self.app.keys_this_run, f"Widget-Key doppelt: {k}"
        self.app.keys_this_run.add(k)
        if on_change: self.app.callbacks[k] = (on_change, args)
        st = self.app.state
        if k not in st: st[k] = default
        return st[k]
    def text_input(self, label, value="", key=None, on_change=None, args=(), **k):
        return self._widget(key, label, value, on_change, args)
    def radio(self, label, options, key=None, **k): return self._widget(key, label, options[0])
    def selectbox(self, label, options, index=0, key=None, on_change=None, args=(), format_func=str, **k):
        if key: self.app.formats[key] = format_func
        v = self._widget(key, label, None if index is None else options[index], on_change, args)
        assert v is None or v in options, f"Auswahl {v!r} nicht in Optionen ({label})"
        return v
    def number_input(self, label, min_value=None, max_value=None, value=None, key=None, **k):
        return self._widget(key, label, value)
    def slider(self, label, min_value=None, max_value=None, value=None, key=None, **k):
        return self._widget(key, label, value)
    def checkbox(self, label, value=False, key=None, on_change=None, args=(), **k):
        return self._widget(key, label, value, on_change, args)
    def button(self, label, key=None, disabled=False, **k):
        k2 = key or f"btn_{label}"
        if disabled:
            self.app.disabled.add(k2)
        assert k2 not in self.app.keys_this_run, f"Button-Key doppelt: {k2}"
        self.app.keys_this_run.add(k2)
        if k2 in self.app.clicks and not disabled: self.app.clicks.discard(k2); return True
        return False
    def form_submit_button(self, label, **k):
        assert self.app.current_form, "form_submit_button außerhalb eines Formulars"
        return self.button(label, key=f"submit_{self.app.current_form}", disabled=k.get("disabled", False))

class FormCtx(Ctx):
    def __init__(self, app, key): self.app, self.key = app, key
    def __enter__(self): self.app.current_form = self.key; return self
    def __exit__(self, *a): self.app.current_form = None; return False

RESOURCE_CACHE = {}

CACHE_FNS = []
CACHE_SPEICHER = {}
CACHE_BEI_JEDEM_LAUF_LEEREN = [True]   # Tests legen Daten direkt in die DB -> Standard: Cache pro Lauf leeren
class CacheFn:
    """Wie st.cache_data: Ergebnis wird über alle Sitzungen UND Neuläufe geteilt (Schlüssel = Funktionsname), bis clear()."""
    def __init__(self, fn):
        self.fn = fn; self.werte = CACHE_SPEICHER.setdefault(fn.__qualname__, {}); CACHE_FNS.append(self)
    def __call__(self, *a, **k):
        if a not in self.werte: self.werte[a] = self.fn(*a, **k)
        return self.werte[a]
    def clear(self): self.werte.clear()
def cache_ablaufen():
    """Wie 'alle Zwischenspeicher sind abgelaufen' (Streamlit-Cache und der mitgeführte Link-Speicher)."""
    for w in CACHE_SPEICHER.values(): w.clear()
    tl = sys.modules.get("tracker_logik")
    if tl is not None and hasattr(tl, "cache_verwerfen"): tl.cache_verwerfen()

class App:
    def __init__(self, script):
        self.script = script; self.state = State(); self.query = {}; self.callbacks = {}; self.clicks = set(); self.formats = {}; self.fragment_fn = None
        self.dialog = None; self.dialog_gezeichnet = False; self.im_dialog = False
        self.module = self._make_module()
    def _make_module(self):
        m = types.ModuleType("streamlit"); main = FakeST(self, "main")
        for name in dir(FakeST):
            if not name.startswith("_"): setattr(m, name, getattr(main, name))
        m.sidebar = FakeST(self, "sidebar"); m.session_state = self.state; m.query_params = self.query
        m.secrets = {}
        def cache_resource(*a, **k):
            def deko(fn):
                def wrapper(*args):
                    schl = (fn.__name__,) + args
                    if schl not in RESOURCE_CACHE: RESOURCE_CACHE[schl] = fn(*args)
                    return RESOURCE_CACHE[schl]
                return wrapper
            return deko(a[0]) if (a and callable(a[0])) else deko
        m.cache_resource = cache_resource
        app = self
        def fragment(*a, **k):
            def deko(fn):
                def wrapper():
                    app.fragment_fn = fn; return fn()
                return wrapper
            return deko(a[0]) if (a and callable(a[0])) else deko
        m.fragment = fragment
        def dialog(titel, **k):
            """Wie st.dialog: Fenster bleibt offen (nur sein Inhalt läuft neu), bis ein voller Neuaufbau (st.rerun) kommt."""
            def deko(fn):
                def oeffnen(*args):
                    assert app.im_dialog is False, "Dialoge dürfen nicht verschachtelt werden"
                    app.dialog = (titel, fn, args); app.dialog_gezeichnet = True
                    app.log.append(("main", "dialog", titel))
                    app.im_dialog = True
                    try: fn(*args)
                    finally: app.im_dialog = False
                return oeffnen
            return deko
        m.dialog = dialog
        m.cache_data = lambda *a, **k: (lambda fn: CacheFn(fn)) if not (a and callable(a[0])) else CacheFn(a[0])
        sys.modules["streamlit"] = m
        return m
    def run(self):
        sys.modules["streamlit"] = self.module
        if CACHE_BEI_JEDEM_LAUF_LEEREN[0]:
            cache_ablaufen()
        for _ in range(6):
            self.log, self.keys_this_run, self.forms_this_run, self.current_form, self.disabled = [], set(), set(), None, set()
            self.dialog_gezeichnet = False; self.im_dialog = False
            try:
                runpy.run_path(self.script, run_name="__main__")
                if self.dialog and not self.dialog_gezeichnet:
                    # offenes Fenster: sein Inhalt wird weiter gezeichnet (in echt läuft dann nur das Fenster neu)
                    titel, fn, args = self.dialog
                    self.log.append(("main", "dialog", titel)); self.im_dialog = True
                    try: fn(*args)
                    finally: self.im_dialog = False
                return self
            except Rerun:
                self.dialog = None   # voller Neuaufbau schließt das Fenster
                continue
        raise AssertionError("Endlose Rerun-Schleife")
    def tick(self):
        """Simuliert das automatische Neuzeichnen des Live-Bereichs (nur das Fragment)."""
        sys.modules["streamlit"] = self.module
        self.log, self.keys_this_run, self.forms_this_run, self.current_form, self.disabled = [], set(), set(), None, set()
        try:
            self.fragment_fn()
        except Rerun:
            self.run()
        return self
    def set(self, key, value):
        """Simuliert eine Nutzer-Eingabe inkl. on_change-Callback, dann neuer Lauf."""
        self.state[key] = value
        if key in self.callbacks:
            fn, args = self.callbacks[key]; fn(*args)
        return self.run()
    def click(self, key):
        self.clicks.add(key); r = self.run()
        if key in self.clicks and key in self.disabled: self.clicks.discard(key); return r
        assert key not in self.clicks, f"Button {key} wurde nicht gerendert"; return r
    def texts(self, kind=None, where=None):
        return [t for w, k, t in self.log if (kind is None or k == kind) and (where is None or w == where)]
