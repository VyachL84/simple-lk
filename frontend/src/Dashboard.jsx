import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  Clock3,
  CreditCard,
  Rocket,
  SquareCheckBig,
  UsersRound,
} from "lucide-react";
import { Btn, DateLabel, days, EventList, Mark, Title, useBuro } from "./ui";

export function Hero() {
  const {
    data: { user: u },
    go,
  } = useBuro();
  return (
    <section className="hero">
      <div className="hero-grid" />
      <img className="growth-art" src="/growth.svg" alt="" />
      <div className="hero-content">
        <div className="hero-meta">
          <span className="hero-badge">
            <span />
            {u.paid ? "ТАРИФ БИЗНЕС" : "ДЕМО-ПЕРИОД"}
          </span>
          <span className="hero-time">
            <Clock3 size={12} />
            {u.days ? "Осталось " + days(u.days) : "Период завершён"}
          </span>
        </div>
        <h2>{u.paid ? "Бюро для вашего бизнеса" : "Пространство для роста"}</h2>
        <p>
          {u.paid
            ? "Ваш тариф активен. Управляйте клиентами и задачами в своём рабочем пространстве."
            : "Изучите возможности кабинета в демо-режиме и выберите тариф, когда будете готовы."}
        </p>
        <Btn tail={ArrowRight} onClick={() => go("billing")}>
          {u.paid ? "Мой тариф" : "Выбрать тариф"}
        </Btn>
      </div>
    </section>
  );
}

function Sparkline({ values }) {
  const vs = values || [0, 0],
    max = Math.max(...vs, 1),
    min = Math.min(...vs),
    pts = vs.map((v, i) => [
      3 + (i * 86) / (vs.length - 1),
      34 - ((v - min) / Math.max(1, max - min)) * 25,
    ]);
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"} ${x} ${y}`).join(" ");
  return (
    <svg
      className="sparkline"
      viewBox="0 0 94 40"
      aria-label="Динамика клиентской базы за 7 дней"
      role="img"
    >
      <defs>
        <linearGradient id="sparkfill" x2="0" y2="1">
          <stop stopColor="#9a8bda" stopOpacity=".26" />
          <stop offset="1" stopColor="#ad9ae1" stopOpacity=".015" />
        </linearGradient>
      </defs>
      <path d={d + " L 89 40 L 3 40 Z"} fill="url(#sparkfill)" />
      <path
        d={d}
        stroke="#a28ad7"
        strokeWidth="2.1"
        fill="none"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={pts.at(-1)[0]} cy={pts.at(-1)[1]} r="2.7" fill="#a28ad7" />
    </svg>
  );
}
function Metrics() {
  const {
    data: { user: u, stats: s },
    go,
  } = useBuro();
  const total = s.tasks,
    done = s.done;
  return (
    <div className="metrics">
      <button className="metric" onClick={() => go("clients")}>
        <div className="metric-top">
          <Mark Icon={UsersRound} tone="violet" />
          <span>Клиентская база</span>
          <ArrowUpRight className="metric-link" size={14} />
        </div>
        <div className="metric-bottom">
          <b>{s.clients}</b>
          <Sparkline values={s.growth} />
        </div>
      </button>
      <button className="metric" onClick={() => go("tasks")}>
        <div className="metric-top">
          <Mark Icon={SquareCheckBig} tone="blue" />
          <span>Задачи в работе</span>
          <ArrowUpRight className="metric-link" size={14} />
        </div>
        <div className="metric-bottom">
          <b>{total - done}</b>
          <span className="metric-hint">из {total} задач</span>
        </div>
      </button>
      <button className="metric" onClick={() => go("billing")}>
        <div className="metric-top">
          <Mark Icon={CreditCard} tone="green" />
          <span>Текущий тариф</span>
          <ArrowUpRight className="metric-link" size={14} />
        </div>
        <div className="metric-bottom">
          <b className="metric-plan">{u.paid ? "Бизнес" : "Демо"}</b>
          <span className={"pill " + (u.active ? "success" : "neutral")}>
            <i />
            {u.active ? "Активен" : "Истёк"}
          </span>
        </div>
      </button>
    </div>
  );
}
export function QuickStart() {
  const {
    data: { user: u },
    show,
    go,
    notify,
  } = useBuro();
  const steps = [
    {
      title: "Создать кабинет",
      sub: "Рабочее пространство готово",
      done: true,
      action: () => go("settings"),
    },
    {
      title: "Выбрать задачи бизнеса",
      sub: "Подберите инструменты под свои цели",
      done: u.goals.length > 0,
      action: () => show("goals"),
    },
    {
      title: "Заполнить профиль",
      sub: "Расскажите немного о своей компании",
      done: !!u.profile_ready,
      action: () => show("profile"),
    },
    {
      title: "Подключить тариф",
      sub: "Продолжите работу после демо",
      done: u.paid,
      action: () => go("billing"),
    },
  ];
  const count = steps.filter((x) => x.done).length,
    first = steps.findIndex((x) => !x.done);
  return (
    <section className="card quick-start">
      <div className="section-title">
        <h2>
          <Rocket size={19} />
          Быстрый старт
        </h2>
        <span className="count-badge">{count} из 4</span>
      </div>
      <p className="section-desc">Несколько шагов для настройки кабинета</p>
      <div className="step-progress" aria-label={`Готово ${count} из 4`}>
        {steps.map((s, i) => (
          <i className={s.done ? "filled" : ""} key={i} />
        ))}
      </div>
      <div className="steps">
        {steps.map((s, i) => (
          <button
            onClick={s.action}
            key={s.title}
            className={
              "step " + (s.done ? "complete" : first === i ? "current" : "")
            }
          >
            <span className="step-indicator">
              {s.done ? (
                <Check size={14} strokeWidth={2.6} />
              ) : (
                String(i + 1).padStart(2, "0")
              )}
            </span>
            <span className="step-text">
              <strong>{s.title}</strong>
              <small>{s.sub}</small>
            </span>
            {s.done ? (
              <span className="step-ok">Готово</span>
            ) : (
              <ChevronRight className="step-arrow" size={16} />
            )}
          </button>
        ))}
      </div>
    </section>
  );
}
export default function Dashboard() {
  const {
    data: { events },
    go,
  } = useBuro();
  return (
    <>
      <Title
        kicker="РАБОЧЕЕ ПРОСТРАНСТВО"
        title="Обзор кабинета"
        sub="Главное о вашем бизнесе в одном месте."
        action={<DateLabel />}
      />
      <Hero />
      <Metrics />
      <div className="overview-grid">
        <QuickStart />
        <section className="card recent">
          <div className="section-title">
            <h2>
              <Activity size={20} />
              Активность
            </h2>
            <span className="live-dot" title="Последние события" />
          </div>
          <p className="section-desc">Последние события в кабинете</p>
          <EventList items={events.slice(0, 3)} />
          <button className="history-link" onClick={() => go("events")}>
            Вся история
            <ArrowRight size={15} />
          </button>
        </section>
      </div>
    </>
  );
}
