import { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  Bell,
  Building2,
  Check,
  CheckCheck,
  ChevronRight,
  ChevronsUpDown,
  CreditCard,
  Ellipsis,
  LayoutGrid,
  LifeBuoy,
  LoaderCircle,
  LogIn,
  LogOut,
  Menu,
  PanelLeft,
  Settings2,
  ShieldCheck,
  SquareCheckBig,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import "@fontsource-variable/golos-text";
import "./theme.css";
import { request } from "./api";
import {
  Brand,
  Btn,
  Ctx,
  EventList,
  methodNames,
  navTitles,
  useBuro,
} from "./ui";
import Dashboard from "./Dashboard";
import Dialogs from "./Dialogs";
import {
  Billing,
  Directory,
  Events,
  Help,
  Legal,
  Login,
  Onboarding,
  Settings,
} from "./Pages";

const entries = [
  ["overview", "Обзор", LayoutGrid],
  ["clients", "Клиенты", UsersRound],
  ["tasks", "Мои задачи", SquareCheckBig],
  ["billing", "Тариф и оплата", CreditCard],
  ["settings", "Настройки", Settings2],
];
function SideNav({ mobile, setMobile }) {
  const {
      data: { user: u, stats: s },
      route,
      go,
      show,
      logout,
    } = useBuro(),
    [profile, setProfile] = useState(false),
    ref = useRef(null);
  useEffect(() => {
    if (!profile) return;
    const close = (e) => {
      if (!ref.current?.contains(e.target)) setProfile(false);
    };
    const esc = (e) => {
      if (e.key === "Escape") setProfile(false);
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [profile]);
  function navigate(p) {
    setMobile(false);
    setProfile(false);
    go(p);
  }
  function nav([id, label, Icon]) {
    return (
      <a
        href={"#/" + id}
        className={"nav-item " + (route === id ? "active" : "")}
        key={id}
        aria-current={route === id ? "page" : undefined}
        onClick={(e) => {
          e.preventDefault();
          navigate(id);
        }}
      >
        <Icon size={19} strokeWidth={1.7} />
        {label}
        {id === "tasks" ? (
          <span className="nav-count">{s.tasks - s.done}</span>
        ) : route === id ? (
          <i className="nav-dot" />
        ) : null}
      </a>
    );
  }
  return (
    <>
      {mobile && (
        <button
          className="side-scrim"
          onClick={() => setMobile(false)}
          aria-label="Закрыть меню"
        />
      )}
      <aside className={"sidebar " + (mobile ? "opened" : "")}>
        <div className="sidebar-brand">
          <a
            href="#/overview"
            aria-label="Бюро — обзор кабинета"
            onClick={() => navigate("overview")}
          >
            <Brand />
          </a>
          <button
            className="icon-button mobile-close"
            aria-label="Закрыть меню"
            onClick={() => setMobile(false)}
          >
            <X size={18} />
          </button>
        </div>
        <button
          className="space-switch"
          onClick={() => {
            setMobile(false);
            show("profile");
          }}
        >
          <span className="space-icon">
            <Building2 size={19} strokeWidth={1.8} />
          </span>
          <span>
            <strong>{u.company || "Мой бизнес"}</strong>
            <small>Пространство</small>
          </span>
          <ChevronsUpDown size={14} />
        </button>
        <nav aria-label="Основная навигация">
          <div className="nav-label">РАБОЧАЯ ОБЛАСТЬ</div>
          {entries.slice(0, 3).map(nav)}
          <div className="nav-label second">УПРАВЛЕНИЕ</div>
          {entries.slice(3).map(nav)}
        </nav>
        <div className="side-bottom">
          <button
            className={"help-link " + (route === "help" ? "selected" : "")}
            onClick={() => navigate("help")}
          >
            <LifeBuoy size={18} />
            Центр помощи
            <ChevronRight size={15} />
          </button>
          <div className="account-wrap" ref={ref}>
            {profile && (
              <div className="profile-pop">
                <button onClick={() => navigate("settings")}>
                  <Settings2 size={15} />
                  Настройки профиля
                </button>
                {u.login_method === "guest" && (
                  <button
                    onClick={() => {
                      setProfile(false);
                      show("login");
                    }}
                  >
                    <LogIn size={15} />
                    Войти в кабинет
                  </button>
                )}
                <button
                  onClick={() => {
                    setProfile(false);
                    logout();
                  }}
                >
                  <LogOut size={15} />
                  Завершить сеанс
                </button>
              </div>
            )}
            <button
              className="sidebar-account"
              aria-expanded={profile}
              onClick={() => setProfile(!profile)}
            >
              <span className="avatar">
                {u.name ? (
                  u.name.charAt(0).toUpperCase()
                ) : (
                  <UserRound size={18} />
                )}
              </span>
              <span>
                <strong>
                  {u.name ||
                    (u.login_method === "guest"
                      ? "Демо-аккаунт"
                      : "Мой аккаунт")}
                </strong>
                <small>
                  {u.login_method === "guest"
                    ? "Личный профиль"
                    : methodNames[u.login_method]}
                </small>
              </span>
              <Ellipsis size={17} />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
function Topbar({ openMobile }) {
  const {
    route,
    data: { events, user: u },
    show,
    go,
    mutate,
    notify,
  } = useBuro();
  const [bell, setBell] = useState(false),
    ref = useRef(null);
  const unread = events.some((e) => e.id > u.notification_seen);
  useEffect(() => {
    if (!bell) return;
    function outside(e) {
      if (!ref.current?.contains(e.target)) setBell(false);
    }
    function esc(e) {
      if (e.key === "Escape") setBell(false);
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", esc);
    };
  }, [bell]);
  return (
    <header className="topbar">
      <button
        className="icon-button mobile-menu"
        aria-label="Открыть навигацию"
        onClick={openMobile}
      >
        <Menu size={21} />
      </button>
      <div className="crumb">
        <PanelLeft size={16} />
        <span className="crumb-divider" />
        <span>Личный кабинет</span>
        <ChevronRight size={13} />
        <b>{navTitles[route] || "Обзор"}</b>
      </div>
      <div className="top-actions">
        <span className="online">
          <i />
          Система онлайн
        </span>
        <div className="bell-wrap" ref={ref}>
          <button
            aria-label="Уведомления"
            aria-expanded={bell}
            className={"bell icon-button " + (bell ? "selected" : "")}
            onClick={() => setBell(!bell)}
          >
            <Bell size={19} />
            {unread && <i />}
          </button>
          {bell && (
            <section className="bell-pop">
              <div className="section-title">
                <h2>Уведомления</h2>
                <button
                  className="icon-button"
                  onClick={() => setBell(false)}
                  aria-label="Закрыть уведомления"
                >
                  <X size={15} />
                </button>
              </div>
              <EventList items={events.slice(0, 3)} compact />
              {unread ? (
                <button
                  className="text-link"
                  onClick={async () => {
                    try {
                      await mutate("/notifications/read");
                      notify("Уведомления прочитаны");
                    } catch (e) {
                      notify(e.message);
                    }
                  }}
                >
                  <CheckCheck size={15} />
                  Отметить прочитанными
                </button>
              ) : (
                <span className="field-help">Все уведомления прочитаны</span>
              )}
            </section>
          )}
        </div>
        <span className="top-divider" />
        {u.login_method === "guest" ? (
          <button className="login-link" onClick={() => show("login")}>
            <LogIn size={15} />
            Войти
          </button>
        ) : (
          <button
            className="mini-avatar"
            aria-label="Профиль"
            onClick={() => go("settings")}
          >
            {u.name ? u.name[0] : <UserRound size={16} />}
          </button>
        )}
      </div>
    </header>
  );
}
function Workspace() {
  const {
      data: { config },
      route,
    } = useBuro(),
    [mobile, setMobile] = useState(false);
  useEffect(() => {
    setMobile(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [route]);
  useEffect(() => {
    if (!mobile) return;
    const fn = (e) => {
      if (e.key === "Escape") setMobile(false);
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [mobile]);
  let page;
  switch (route) {
    case "clients":
    case "tasks":
      page = <Directory key={route} type={route} />;
      break;
    case "billing":
      page = <Billing />;
      break;
    case "settings":
      page = <Settings />;
      break;
    case "help":
      page = <Help />;
      break;
    case "events":
      page = <Events />;
      break;
    case "onboarding":
      page = <Onboarding />;
      break;
    default:
      page = <Dashboard />;
  }
  return (
    <div className="shell">
      <a
        className="skip"
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        К содержанию
      </a>
      <SideNav mobile={mobile} setMobile={setMobile} />
      <div className="main-shell">
        <Topbar openMobile={() => setMobile(true)} />
        <main id="main-content" className="main-content" tabIndex={-1}>
          {page}
        </main>
        <footer className="footer">
          <span>
            Бюро <i /> Кабинет для бизнеса
          </span>
          <a href={config.policyUrl} target="_blank" rel="noreferrer">
            <ShieldCheck size={13} />
            Персональные данные
            <ArrowUpRight size={12} />
          </a>
        </footer>
      </div>
    </div>
  );
}
const routeFromLocation = () =>
  location.hash.replace(/^#\/?/, "").split("?")[0] ||
  (location.pathname === "/login" ? "login" : "overview");
function App() {
  const [data, setData] = useState(null),
    [revision, bump] = useState(0),
    [route, setRoute] = useState(routeFromLocation),
    [modal, setModal] = useState(null),
    [toast, setToast] = useState(""),
    [error, setError] = useState(""),
    [tries, setTries] = useState(0);
  const timer = useRef(0);
  const legal = ["/privacy", "/consent"].includes(location.pathname);
  function update(r) {
    setData(r);
    bump((n) => n + 1);
  }
  function notify(message) {
    clearTimeout(timer.current);
    setToast(message);
    timer.current = setTimeout(() => setToast(""), 4000);
  }
  const go = useCallback((id) => {
    setModal(null);
    location.hash = "/" + id;
    setRoute(id);
  }, []);
  function show(type, extra = {}) {
    setModal({ type, ...extra });
  }
  async function mutate(path, payload = {}, method = "POST") {
    const r = await request(path, method, payload);
    if (r.config) update(r);
    return r;
  }
  async function preview() {
    try {
      const r = await mutate("/open", { preview: true });
      if (r.user) go("overview");
    } catch (e) {
      notify(e.message);
    }
  }
  async function logout() {
    try {
      await mutate("/logout");
      setModal(null);
      go("login");
      notify("Сеанс завершён");
    } catch (e) {
      notify(e.message);
    }
  }
  useEffect(() => {
    const fn = () => {
      setRoute(routeFromLocation());
    };
    window.addEventListener("hashchange", fn);
    return () => window.removeEventListener("hashchange", fn);
  }, []);
  useEffect(() => {
    if (legal) return;
    let live = true;
    setError("");
    request("/open", "POST", { preview: routeFromLocation() !== "login" })
      .then((r) => {
        if (live) update(r);
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [tries, legal]);
  useEffect(() => {
    document.title =
      (legal ? "Персональные данные" : navTitles[route] || "Обзор") + " · Бюро";
  }, [route, legal]);
  if (legal) return <Legal consent={location.pathname === "/consent"} />;
  if (!data)
    return (
      <div className="boot">
        <Brand />
        {error ? (
          <>
            <p role="alert">{error}</p>
            <Btn kind="secondary" onClick={() => setTries((n) => n + 1)}>
              Попробовать снова
            </Btn>
          </>
        ) : (
          <LoaderCircle className="spin" size={18} />
        )}
      </div>
    );
  return (
    <Ctx.Provider
      value={{
        data,
        update,
        revision,
        route,
        go,
        modal,
        show,
        close: () => setModal(null),
        notify,
        mutate,
        preview,
        logout,
      }}
    >
      {!data.user || route === "login" ? <Login /> : <Workspace />}
      <Dialogs />
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          {toast}
          <button onClick={() => setToast("")} aria-label="Скрыть сообщение">
            <X size={14} />
          </button>
        </div>
      )}
    </Ctx.Provider>
  );
}
createRoot(document.getElementById("root")).render(<App />);
