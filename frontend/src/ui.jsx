import { createContext, useContext, useEffect, useRef, useState } from "react";
import {
  Activity,
  CalendarDays,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  CreditCard,
  Flag,
  LoaderCircle,
  ShieldCheck,
  SquareCheckBig,
  UserRoundPlus,
  UsersRound,
  X,
  Zap,
} from "lucide-react";
export const Ctx = createContext(null);
export const useBuro = () => useContext(Ctx);
export const goals = [
  {
    id: "clients",
    title: "Вести клиентскую базу",
    desc: "Контакты и компании в одном месте",
    Icon: UsersRound,
    tone: "blue",
  },
  {
    id: "tasks",
    title: "Организовать работу",
    desc: "Задачи и понятный план на неделю",
    Icon: SquareCheckBig,
    tone: "violet",
  },
  {
    id: "sales",
    title: "Развивать продажи",
    desc: "Предложения и работа с клиентами",
    Icon: Flag,
    tone: "orange",
  },
];
export const navTitles = {
  overview: "Обзор",
  clients: "Клиенты",
  tasks: "Мои задачи",
  billing: "Тариф и оплата",
  settings: "Настройки",
  help: "Центр помощи",
  events: "История активности",
  onboarding: "Быстрый старт",
  login: "Вход",
};
export const methodNames = {
  guest: "Демо-аккаунт",
  phone: "По телефону",
  yandex: "Яндекс ID",
  esia: "Госуслуги",
};
export function Brand() {
  return (
    <span className="brand">
      <img src="/mark.svg" alt="" />
      Бюро<span className="brand-point">.</span>
    </span>
  );
}
export function Mark({ Icon, tone = "neutral", size = 17, round = false }) {
  return (
    <span className={`mark ${tone} ${round ? "round" : ""}`}>
      <Icon size={size} strokeWidth={1.8} />
    </span>
  );
}
export function Btn({
  children,
  Icon,
  tail,
  kind = "primary",
  busy = false,
  className = "",
  ...props
}) {
  const Tail = tail;
  return (
    <button
      {...props}
      disabled={busy || props.disabled}
      className={`btn ${kind} ${className}`}
    >
      {busy ? (
        <LoaderCircle size={16} className="spin" />
      ) : Icon ? (
        <Icon size={16} />
      ) : null}
      {children}
      {Tail && <Tail size={16} />}
    </button>
  );
}
export function Title({ kicker, title, sub, action }) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">
          <i />
          {kicker}
        </div>
        <h1>{title}</h1>
        <p>{sub}</p>
      </div>
      {action}
    </div>
  );
}
export function DateLabel() {
  return (
    <span className="date-label">
      <CalendarDays size={15} />
      {new Date()
        .toLocaleDateString("ru-RU", {
          day: "numeric",
          month: "long",
          year: "numeric",
        })
        .replace(" г.", "")}
    </span>
  );
}
export function formatDate(sec) {
  return new Date(sec * 1000)
    .toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
    })
    .replace(" г.", "");
}
export function when(sec) {
  const d = new Date(sec * 1000);
  return (
    (d.toDateString() === new Date().toDateString()
      ? "Сегодня"
      : d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" })) +
    ", " +
    d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
  );
}
export function days(n) {
  return (
    n +
    " " +
    (n % 10 === 1 && n % 100 !== 11
      ? "день"
      : n % 10 >= 2 && n % 10 <= 4 && !(n % 100 >= 12 && n % 100 <= 14)
        ? "дня"
        : "дней")
  );
}
export function useAction() {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const guard = useRef(false);
  async function run(fn) {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message || "Ошибка запроса.");
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  return { busy, error, run, setError };
}
export function ErrorLine({ error }) {
  return error ? (
    <p role="alert" className="form-error">
      {error}
    </p>
  ) : null;
}
export function Notice({ children, Icon = ShieldCheck, tone = "" }) {
  return (
    <div className={"notice " + tone}>
      <Icon size={18} />
      <div>{children}</div>
    </div>
  );
}
export function Modal({ title, kicker, children, onClose, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    el.showModal();
    document.body.classList.add("has-modal");
    return () => {
      el.close();
      document.body.classList.remove("has-modal");
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={"modal" + (wide ? " wide" : "")}
      aria-labelledby="dialog-title"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) {
          const b = ref.current.getBoundingClientRect();
          if (
            e.clientX < b.left ||
            e.clientX > b.right ||
            e.clientY < b.top ||
            e.clientY > b.bottom
          )
            onClose();
        }
      }}
    >
      <div className="modal-head">
        <div className="eyebrow">
          <i />
          {kicker || "РАБОЧЕЕ ПРОСТРАНСТВО"}
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Закрыть">
          <X size={19} />
        </button>
      </div>
      <h2 id="dialog-title">{title}</h2>
      {children}
    </dialog>
  );
}
export function Pager({ page, setPage, total }) {
  const last = Math.ceil(total / 20);
  return last > 1 ? (
    <div className="pager">
      <button
        className="icon-button"
        disabled={page === 1}
        onClick={() => setPage(page - 1)}
        aria-label="Предыдущая страница"
      >
        <ChevronLeft size={17} />
      </button>
      Страница {page} из {last}
      <button
        className="icon-button"
        disabled={page === last}
        onClick={() => setPage(page + 1)}
        aria-label="Следующая страница"
      >
        <ChevronRight size={17} />
      </button>
    </div>
  ) : null;
}
export function Empty({ Icon = ClipboardList, title, sub, children }) {
  return (
    <div className="empty">
      <Mark Icon={Icon} />
      <h3>{title}</h3>
      <p>{sub}</p>
      {children}
    </div>
  );
}
export const eventIcons = {
  account: [UserRoundPlus, "blue"],
  clients: [UsersRound, "violet"],
  trial: [Zap, "orange"],
  tasks: [CheckCheck, "blue"],
  billing: [CreditCard, "green"],
};
export function EventList({ items, compact = false }) {
  return (
    <div className={"timeline" + (compact ? " compact" : "")}>
      {items.map((e) => {
        const [Icon, tone] = eventIcons[e.kind] || [Activity, "neutral"];
        return (
          <div className="event" key={e.id}>
            <Mark Icon={Icon} tone={tone} round size={16} />
            <div>
              <strong>{e.title}</strong>
              {!compact && <p>{e.detail}</p>}
              <small>{when(e.created)}</small>
            </div>
          </div>
        );
      })}
    </div>
  );
}
