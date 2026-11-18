import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  CreditCard,
  Database,
  Flag,
  History,
  Info,
  KeyRound,
  Layers3,
  LockKeyhole,
  LogIn,
  LogOut,
  Mail,
  Pencil,
  Plus,
  RefreshCw,
  Rocket,
  Search,
  ShieldCheck,
  Trash2,
  UsersRound,
  Wallet,
} from "lucide-react";
import { request } from "./api";
import {
  Brand,
  Btn,
  DateLabel,
  days,
  Empty,
  ErrorLine,
  EventList,
  formatDate,
  goals,
  Mark,
  methodNames,
  Notice,
  Pager,
  Title,
  useAction,
  useBuro,
  when,
} from "./ui";
import { AuthBox, GoalForm, ProfileForm } from "./Dialogs";

function useList(path) {
  const { revision } = useBuro();
  const [value, setValue] = useState({ items: [], total: 0 }),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [retry, setRetry] = useState(0);
  useEffect(() => {
    let current = true;
    setLoading(true);
    setError("");
    request(path)
      .then((r) => {
        if (current) setValue(r);
      })
      .catch((e) => {
        if (current) setError(e.message);
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [path, revision, retry]);
  return { ...value, loading, error, retry: () => setRetry((n) => n + 1) };
}
function ListStatus({ list, empty, sub, Icon }) {
  if (list.error)
    return (
      <div className="empty">
        <ErrorLine error={list.error} />
        <Btn kind="secondary" onClick={list.retry}>
          Повторить
        </Btn>
      </div>
    );
  if (list.loading && !list.items.length)
    return <div className="list-loading">Загрузка…</div>;
  if (!list.items.length) return <Empty Icon={Icon} title={empty} sub={sub} />;
  return null;
}
export function Directory({ type }) {
  const isClient = type === "clients",
    {
      data: { user, stats },
      show,
      go,
      mutate,
      notify,
    } = useBuro();
  const [query, setQuery] = useState(""),
    [settled, setSettled] = useState(""),
    [filter, setFilter] = useState("all"),
    [page, setPage] = useState(1);
  useEffect(() => {
    const t = setTimeout(() => {
      setSettled(query);
      setPage(1);
    }, 200);
    return () => clearTimeout(t);
  }, [query]);
  const list = useList(
    `/${type}?q=${encodeURIComponent(settled)}&page=${page}&status=${filter}`,
  );
  useEffect(() => {
    if (
      !list.loading &&
      !list.error &&
      page > 1 &&
      page > Math.max(Math.ceil(list.total / 20), 1)
    )
      setPage(Math.max(Math.ceil(list.total / 20), 1));
  }, [list.total, list.loading, page]);
  const { busy, error, run } = useAction();
  async function exportList() {
    if (!user.paid) {
      go("billing");
      notify("Экспорт CSV доступен на тарифе Бизнес");
      return;
    }
    const blob = await request("/clients/export"),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = "buro-clients.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <>
      <Title
        kicker="РАБОЧЕЕ ПРОСТРАНСТВО"
        title={isClient ? "Клиентская база" : "Мои задачи"}
        sub={
          isClient
            ? "Контакты и компании, с которыми вы работаете."
            : "Планируйте работу и отмечайте выполненные задачи."
        }
        action={
          <Btn Icon={Plus} onClick={() => show(isClient ? "client" : "task")}>
            {isClient ? "Добавить клиента" : "Новая задача"}
          </Btn>
        }
      />
      {!isClient && (
        <div className="context-strip">
          <Mark Icon={Flag} tone="orange" />
          <div>
            <strong>План под ваши цели</strong>
            <small>
              {user.goals.length
                ? user.goals
                    .map((id) => goals.find((g) => g.id === id)?.title)
                    .join(" · ")
                : "Выберите цели бизнеса для персонального списка задач."}
            </small>
          </div>
          <button className="text-link" onClick={() => show("goals")}>
            Настроить
            <ArrowRight size={15} />
          </button>
        </div>
      )}
      <section className="card data-card">
        <div className="data-card-title">
          <h2>
            {isClient ? "Все клиенты" : "Список задач"}{" "}
            <span className="count-badge">
              {isClient ? stats.clients : stats.tasks}
            </span>
          </h2>
          {isClient && (
            <Btn
              kind="secondary"
              Icon={user.paid ? ArrowDownToLine : LockKeyhole}
              busy={busy}
              onClick={() => run(exportList)}
            >
              Экспорт CSV
            </Btn>
          )}
        </div>
        <div className="list-tools">
          <label className="search-field">
            <Search size={17} />
            <input
              aria-label={isClient ? "Поиск клиентов" : "Поиск задач"}
              placeholder={isClient ? "Найти клиента по имени" : "Найти задачу"}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          {!isClient && (
            <div className="tabs">
              {[
                ["all", "Все"],
                ["open", "В работе"],
                ["done", "Готово"],
              ].map(([id, t]) => (
                <button
                  key={id}
                  className={filter === id ? "selected" : ""}
                  onClick={() => {
                    setFilter(id);
                    setPage(1);
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>
        <ErrorLine error={error} />
        <ListStatus
          list={list}
          Icon={isClient ? UsersRound : ClipboardList}
          empty={
            query
              ? "Ничего не найдено"
              : isClient
                ? "Пока нет клиентов"
                : "Задач пока нет"
          }
          sub={
            query
              ? "Попробуйте другое название или имя."
              : isClient
                ? "Добавьте первый контакт в свою базу."
                : "Создайте задачу или выберите цели бизнеса."
          }
        />
        {!list.error &&
          list.items.length > 0 &&
          (isClient ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Клиент</th>
                    <th>Компания</th>
                    <th>Почта</th>
                    <th>
                      <span className="sr-only">Действия</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {list.items.map((c, i) => (
                    <tr key={c.id}>
                      <td>
                        <button
                          className="client-name"
                          onClick={() => show("client", { item: c })}
                        >
                          <span className={"initials tone-" + (i % 4)}>
                            {c.name
                              .split(/\s+/)
                              .slice(0, 2)
                              .map((x) => x[0])
                              .join("")}
                          </span>
                          {c.name}
                        </button>
                      </td>
                      <td>{c.company || "—"}</td>
                      <td>{c.email || "—"}</td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="icon-button"
                            aria-label={"Изменить: " + c.name}
                            onClick={() => show("client", { item: c })}
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            className="icon-button remove"
                            aria-label={"Удалить: " + c.name}
                            onClick={() =>
                              show("remove", { table: "clients", item: c })
                            }
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="task-list">
              {list.items.map((t) => (
                <div
                  className={"task-row " + (t.done ? "is-done" : "")}
                  key={t.id}
                >
                  <button
                    role="checkbox"
                    aria-checked={!!t.done}
                    aria-label={"Статус: " + t.title}
                    className="task-check"
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        await mutate(
                          "/tasks/" + t.id,
                          { done: !t.done },
                          "PUT",
                        );
                        notify(
                          t.done
                            ? "Задача возвращена в работу"
                            : "Задача выполнена",
                        );
                      })
                    }
                  >
                    {!!t.done && <Check size={14} />}
                  </button>
                  <div className="task-label">
                    <strong>{t.title}</strong>
                    <small>{formatDate(t.created)}</small>
                  </div>
                  <span className="tag">{t.category}</span>
                  <button
                    className="icon-button remove"
                    aria-label={"Удалить: " + t.title}
                    onClick={() => show("remove", { table: "tasks", item: t })}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          ))}
        <Pager page={page} setPage={setPage} total={list.total} />
      </section>
    </>
  );
}

export function Billing() {
  const {
      data: { config, user: u },
      show,
      mutate,
      notify,
    } = useBuro(),
    list = useList("/billing"),
    { run, error, busy } = useAction(),
    checked = useRef("");
  const pending = list.items.find((x) => x.state === "pending");
  useEffect(() => {
    if (!config.demo && pending?.url && checked.current !== pending.id) {
      checked.current = pending.id;
      run(() => mutate("/billing/check"));
    }
  }, [pending?.id]);
  return (
    <>
      <Title
        kicker="УПРАВЛЕНИЕ"
        title="Тариф и оплата"
        sub="Выберите доступ, который подходит вашему бизнесу."
      />
      <div className="context-strip">
        <Mark Icon={Wallet} tone="green" />
        <div>
          <strong>
            {u.paid
              ? "Подключён тариф Бизнес"
              : u.active
                ? "У вас демо-доступ"
                : "Демо-период завершён"}
          </strong>
          <small>
            {u.active
              ? `Действует до ${formatDate(u.paid_until || u.trial_until)} · Осталось ${days(u.days)}`
              : "Данные сохранены. Чтение кабинета по-прежнему доступно."}
          </small>
        </div>
      </div>
      <div className="plan-grid">
        {[false, true].map((paid) => (
          <section
            key={String(paid)}
            className={"card plan-card " + (paid ? "business" : "")}
          >
            <div className="plan-top">
              <Mark
                Icon={paid ? Layers3 : Rocket}
                tone={paid ? "orange" : "neutral"}
              />
              {paid === u.paid && (
                <span className={"pill " + (u.active ? "success" : "neutral")}>
                  <i />
                  {u.active ? "Ваш тариф" : "Завершён"}
                </span>
              )}
            </div>
            <h2>{paid ? "Бизнес" : "Демо"}</h2>
            <p>
              {paid
                ? "Для ежедневной работы с клиентами"
                : "Чтобы познакомиться с Бюро"}
            </p>
            <div className="price">
              {paid ? (config.price / 100).toLocaleString("ru-RU") : "0"} ₽{" "}
              <small>/ {paid ? "30" : "14"} дней</small>
            </div>
            <ul>
              {(paid
                ? [
                    "До 2 000 клиентов в базе",
                    "До 500 задач",
                    "Экспорт клиентской базы в CSV",
                    "Без автоматического продления",
                  ]
                : [
                    "До 100 клиентов в базе",
                    "До 30 задач",
                    "Настройка по целям бизнеса",
                    "Без привязки карты",
                  ]
              ).map((s) => (
                <li key={s}>
                  <Check size={16} />
                  {s}
                </li>
              ))}
            </ul>
            {paid && !u.paid ? (
              <Btn
                tail={ArrowRight}
                disabled={!config.billing}
                onClick={() => show("checkout")}
              >
                {config.billing
                  ? pending
                    ? "Продолжить оплату"
                    : "Подключить Бизнес"
                  : "Оплата ещё не настроена"}
              </Btn>
            ) : (
              <span className="plan-foot">
                {paid ? <CheckCircle2 size={16} /> : <Info size={16} />}{" "}
                {paid ? "Тариф подключён" : "Предоставляется один раз"}
              </span>
            )}
          </section>
        ))}
      </div>
      {config.demo && (
        <Notice Icon={Info}>
          В демо-кабинете оплата тестовая. Переход на Бизнес не спишет деньги.
        </Notice>
      )}
      <section className="card payments">
        <div className="section-title">
          <h2>
            <History size={18} />
            История платежей
          </h2>
          {pending && (
            <Btn
              kind="secondary"
              busy={busy}
              Icon={RefreshCw}
              onClick={() =>
                run(async () => {
                  const d = await mutate("/billing/check");
                  notify(
                    d.user.paid
                      ? "Оплата подтверждена"
                      : "Статус платежа обновлён",
                  );
                })
              }
            >
              Проверить оплату
            </Btn>
          )}
        </div>
        <ErrorLine error={error || list.error} />
        {!list.items.length ? (
          <p className="muted">
            Платежей пока нет. Здесь появятся сведения о подключении тарифа.
          </p>
        ) : (
          list.items.map((p) => (
            <div className="payment-row" key={p.id}>
              <Mark Icon={CreditCard} tone="green" />
              <div>
                <strong>Бизнес · 30 дней</strong>
                <small>
                  {when(p.created)}
                  {config.demo ? " · Тестовый платёж" : ""}
                </small>
              </div>
              <span className="payment-state">
                {
                  {
                    succeeded: "Подтверждён",
                    pending: "Ожидает оплаты",
                    canceled: "Отменён",
                  }[p.state]
                }
              </span>
              <b>{(p.amount / 100).toLocaleString("ru-RU")} ₽</b>
            </div>
          ))
        )}
      </section>
    </>
  );
}

export function Settings() {
  const {
    data: { user: u, config },
    show,
    logout,
  } = useBuro();
  return (
    <>
      <Title
        kicker="УПРАВЛЕНИЕ"
        title="Настройки"
        sub="Профиль компании и доступ к рабочему пространству."
      />
      <div className="settings-grid">
        <section className="card form-card">
          <div className="section-title">
            <h2>
              <BriefcaseBusiness size={18} />
              Профиль компании
            </h2>
          </div>
          <ProfileForm />
        </section>
        <section className="card form-card">
          <div className="section-title">
            <h2>
              <ShieldCheck size={18} />
              Доступ в кабинет
            </h2>
          </div>
          <p className="muted">Текущий способ входа</p>
          <div className="access-method">
            <Mark Icon={KeyRound} tone="orange" />
            <b>{methodNames[u.login_method]}</b>
          </div>
          <p className="field-help">
            {config.demo
              ? "Это изолированный демо-кабинет. Внешняя авторизация и платежи имитируются."
              : "Аккаунт привязан к подтверждённому идентификатору провайдера."}
          </p>
          <div className="settings-actions">
            {u.login_method === "guest" && (
              <Btn kind="secondary" Icon={LogIn} onClick={() => show("login")}>
                Попробовать вход
              </Btn>
            )}
            <Btn kind="ghost" Icon={LogOut} onClick={logout}>
              Выйти из кабинета
            </Btn>
          </div>
          <a
            className="inline-link"
            href={config.policyUrl}
            target="_blank"
            rel="noreferrer"
          >
            Обработка персональных данных
            <ArrowUpRight size={14} />
          </a>
          {config.contact && (
            <p className="field-help">Запросы о данных: {config.contact}</p>
          )}
        </section>
      </div>
    </>
  );
}
export function Events() {
  const [page, setPage] = useState(1),
    list = useList("/events?page=" + page);
  return (
    <>
      <Title
        kicker="ЖУРНАЛ КАБИНЕТА"
        title="История активности"
        sub="Важные изменения в вашем рабочем пространстве."
        action={<DateLabel />}
      />
      <section className="card form-card">
        <div className="section-title">
          <h2>
            <Activity size={19} />
            Все события
          </h2>
          <span className="count-badge">{list.total}</span>
        </div>
        <ListStatus
          list={list}
          empty="Пока нет событий"
          sub="Здесь появятся изменения кабинета."
        />
        {!list.error && <EventList items={list.items} />}
        <Pager page={page} setPage={setPage} total={list.total} />
      </section>
    </>
  );
}
const faq = [
  [
    "Как начать работу?",
    "Откройте «Быстрый старт» на странице обзора. Выберите цели бизнеса: Бюро добавит подходящие задачи. Затем заполните профиль компании и создайте карточки клиентов.",
  ],
  [
    "Как устроен вход?",
    "В рабочей версии доступны подключённые оператором способы: Яндекс ID, Госуслуги через шлюз ЕСИА или одноразовый SMS-код. В демо эти сценарии работают только с тестовыми данными. Аккаунты разных провайдеров не объединяются автоматически.",
  ],
  [
    "Что произойдёт после 14 дней?",
    "После демо-периода клиенты и задачи сохранятся. Вы сможете просматривать кабинет, а для редактирования потребуется тариф Бизнес. Автопродления и скрытых списаний нет.",
  ],
  [
    "Как перенести клиентскую базу?",
    "На тарифе Бизнес откройте «Клиенты» → «Экспорт CSV». Скачается таблица с именами, компаниями и адресами почты, которую можно открыть в табличном редакторе.",
  ],
];
export function Help() {
  const {
    data: { config },
  } = useBuro();
  return (
    <>
      <Title
        kicker="ПОДДЕРЖКА"
        title="Центр помощи"
        sub="Ответы на вопросы и документация Бюро."
      />
      <section className="card form-card">
        <div className="section-title">
          <h2>
            <BookOpen size={19} />
            Частые вопросы
          </h2>
        </div>
        <div className="faqs">
          {faq.map(([q, a]) => (
            <details key={q}>
              <summary>
                {q}
                <ChevronDown size={16} />
              </summary>
              <p>{a}</p>
            </details>
          ))}
        </div>
      </section>
      <h2 className="sub-heading">Для администратора</h2>
      <div className="guide-grid">
        {[
          [KeyRound, "integrations", "Вход и оплата", "Настройка провайдеров"],
          [Database, "database", "Хранение данных", "Схема и нагрузочный тест"],
          [
            ShieldCheck,
            "personal-data",
            "Персональные данные",
            "Требования законодательства РФ",
          ],
        ].map(([Icon, id, title, sub]) => (
          <a
            key={id}
            className="card guide"
            href={"/guides/" + id + ".md"}
            target="_blank"
            rel="noreferrer"
          >
            <Mark Icon={Icon} tone="orange" />
            <h3>
              {title}
              <ArrowUpRight size={15} />
            </h3>
            <p>{sub}</p>
          </a>
        ))}
      </div>
      {config.contact && (
        <Notice Icon={Mail}>Для обращения к оператору: {config.contact}</Notice>
      )}
    </>
  );
}
export function Onboarding() {
  const { go } = useBuro();
  return (
    <>
      <Title
        kicker="БЫСТРЫЙ СТАРТ"
        title="Задачи вашего бизнеса"
        sub="Настройте Бюро под свой рабочий день."
      />
      <section className="card form-card narrow">
        <GoalForm onDone={() => go("tasks")} />
      </section>
    </>
  );
}
export function Login() {
  const {
    data: { config },
    update,
    go,
    show,
    preview,
  } = useBuro();
  return (
    <div className="login-screen">
      <div className="login-brand">
        <Brand />
      </div>
      <div className="login-shell">
        <div className="login-intro">
          <div className="eyebrow">
            <i />
            ДЛЯ МАЛОГО БИЗНЕСА
          </div>
          <h1>
            Ваш бизнес.
            <br />
            Ваше Бюро.
          </h1>
          <p>
            Клиенты, задачи и планы —<br />в одном рабочем пространстве.
          </p>
          <img src="/growth.svg" alt="" />
        </div>
        <section className="login-form">
          <div className="eyebrow">
            <i />
            ЛИЧНЫЙ КАБИНЕТ
          </div>
          <h2>Вход в Бюро</h2>
          {new URLSearchParams(location.search).get("login") === "failed" && (
            <ErrorLine error="Вход отменён или не подтверждён. Попробуйте ещё раз." />
          )}
          <AuthBox
            onPreview={preview}
            onDone={(r) => {
              go("overview");
              if (!r.user.goals.length) show("goals");
            }}
          />
        </section>
      </div>
      <small className="login-credit">
        Бюро · Рабочее пространство для бизнеса
      </small>
    </div>
  );
}
