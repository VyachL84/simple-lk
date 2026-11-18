import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  Info,
  Layers3,
  ShieldCheck,
  Smartphone,
  Trash2,
} from "lucide-react";
import { request } from "./api";
import {
  Btn,
  ErrorLine,
  goals,
  Mark,
  Modal,
  Notice,
  useAction,
  useBuro,
} from "./ui";

export function ProfileForm({ onDone }) {
  const {
    data: { user: u, config },
    mutate,
    notify,
  } = useBuro();
  const [name, setName] = useState(u.name),
    [company, setCompany] = useState(u.company);
  const { busy, error, run } = useAction();
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        run(async () => {
          await mutate("/profile", { name, company });
          notify("Профиль сохранён");
          onDone?.();
        });
      }}
    >
      <label>
        Как к вам обращаться
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Имя"
          maxLength={64}
          required
          autoComplete="off"
        />
      </label>
      <label>
        Название компании
        <input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="Например, студия «Линия»"
          maxLength={80}
          required
        />
      </label>
      {config.demo && (
        <p className="field-help">
          Это демо-кабинет. Используйте вымышленные данные.
        </p>
      )}
      <ErrorLine error={error} />
      <div className="form-actions">
        <Btn busy={busy} type="submit" tail={Check}>
          Сохранить профиль
        </Btn>
      </div>
    </form>
  );
}
export function GoalForm({ onDone }) {
  const {
    data: { user },
    mutate,
    notify,
  } = useBuro();
  const [selected, setSelected] = useState(user.goals);
  const { busy, error, run } = useAction();
  function flip(id) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }
  return (
    <>
      <p className="modal-sub">
        Что вы хотите делать в Бюро? Выберите цели, и мы добавим первые задачи в
        ваш список.
      </p>
      <div className="goal-options">
        {goals.map(({ id, title, desc, Icon, tone }) => (
          <button
            key={id}
            aria-pressed={selected.includes(id)}
            className={"goal-option " + (selected.includes(id) ? "chosen" : "")}
            onClick={() => flip(id)}
          >
            <Mark Icon={Icon} tone={tone} />
            <span>
              <strong>{title}</strong>
              <small>{desc}</small>
            </span>
            <i className="choice-check">
              {selected.includes(id) && <Check size={13} />}
            </i>
          </button>
        ))}
      </div>
      <ErrorLine error={error} />
      <div className="form-actions">
        <Btn
          disabled={!selected.length}
          busy={busy}
          tail={ArrowRight}
          onClick={() =>
            run(async () => {
              await mutate("/goals", { goals: selected });
              notify("Цели сохранены. План доступен в «Моих задачах».");
              onDone?.();
            })
          }
        >
          Сохранить цели
        </Btn>
      </div>
    </>
  );
}
function ClientForm({ item, close }) {
  const {
    data: { config },
    mutate,
    notify,
  } = useBuro();
  const [v, set] = useState({
    name: item?.name || "",
    company: item?.company || "",
    email: item?.email || "",
  });
  const { busy, error, run } = useAction();
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        run(async () => {
          await mutate(
            item ? "/clients/" + item.id : "/clients",
            v,
            item ? "PUT" : "POST",
          );
          notify(item ? "Карточка обновлена" : "Клиент добавлен");
          close();
        });
      }}
    >
      {[
        ["name", "Имя клиента", "Имя и фамилия", 100],
        ["company", "Компания", "Необязательно", 100],
        ["email", "Электронная почта", "name@example.test", 180],
      ].map(([key, l, ph, max]) => (
        <label key={key}>
          {l}
          <input
            type={key === "email" ? "email" : "text"}
            required={key === "name"}
            maxLength={max}
            placeholder={ph}
            value={v[key]}
            onChange={(e) => set({ ...v, [key]: e.target.value })}
          />
        </label>
      ))}
      {config.demo && (
        <p className="field-help">
          Для знакомства с кабинетом вводите только вымышленные данные.
        </p>
      )}
      <ErrorLine error={error} />
      <div className="form-actions">
        <Btn kind="secondary" type="button" onClick={close}>
          Отмена
        </Btn>
        <Btn busy={busy} type="submit">
          {item ? "Сохранить" : "Добавить клиента"}
        </Btn>
      </div>
    </form>
  );
}
function TaskForm({ close }) {
  const { mutate, notify } = useBuro(),
    [title, setTitle] = useState(""),
    [category, setCategory] = useState("Работа");
  const { run, busy, error } = useAction();
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        run(async () => {
          await mutate("/tasks", { title, category });
          notify("Задача добавлена");
          close();
        });
      }}
    >
      <label>
        Что нужно сделать?
        <input
          required
          maxLength={150}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Например, подготовить предложение"
        />
      </label>
      <label>
        Категория
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          {["Работа", "Клиенты", "Продажи", "Настройка"].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </label>
      <ErrorLine error={error} />
      <div className="form-actions">
        <Btn type="button" kind="secondary" onClick={close}>
          Отмена
        </Btn>
        <Btn busy={busy} type="submit">
          Создать задачу
        </Btn>
      </div>
    </form>
  );
}
function Confirm({ modal, close }) {
  const {
    mutate,
    notify,
    data: { config },
    update,
    go,
  } = useBuro();
  const { run, busy, error } = useAction();
  if (modal.type === "checkout")
    return (
      <>
        <p className="modal-sub">
          Тариф «Бизнес» на 30 дней. Один платёж, без автоматических списаний.
        </p>
        <div className="order-summary">
          <Mark Icon={Layers3} tone="orange" />
          <div>
            <strong>Бизнес</strong>
            <small>30 дней доступа</small>
          </div>
          <b>{(config.price / 100).toLocaleString("ru-RU")} ₽</b>
        </div>
        <Notice Icon={config.demo ? Info : ShieldCheck}>
          {config.demo
            ? "Демонстрация оплаты: карта не нужна, деньги не списываются."
            : "Для оплаты вы перейдёте на защищённую страницу ЮKassa. Данные карты не попадут в Бюро."}
        </Notice>
        <ErrorLine error={error} />
        <div className="form-actions">
          <Btn kind="secondary" onClick={close}>
            Отмена
          </Btn>
          <Btn
            busy={busy}
            tail={ArrowRight}
            onClick={() =>
              run(async () => {
                const r = await request("/billing/checkout", "POST", {
                  plan: "business",
                  confirmed: true,
                });
                if (r.url) {
                  window.location.assign(r.url);
                  return;
                }
                update(r.workspace);
                notify("Тариф Бизнес подключён на 30 дней");
                close();
                go("billing");
              })
            }
          >
            {config.demo ? "Подключить в демо" : "Перейти к оплате"}
          </Btn>
        </div>
      </>
    );
  return (
    <>
      <p className="modal-sub">
        «{modal.item.name || modal.item.title}» будет удалено из вашего
        кабинета. Отменить это действие нельзя.
      </p>
      <ErrorLine error={error} />
      <div className="form-actions">
        <Btn kind="secondary" onClick={close}>
          Отмена
        </Btn>
        <Btn
          kind="danger"
          busy={busy}
          Icon={Trash2}
          onClick={() =>
            run(async () => {
              await mutate(
                "/" + modal.table + "/" + modal.item.id,
                {},
                "DELETE",
              );
              notify("Запись удалена");
              close();
            })
          }
        >
          Удалить
        </Btn>
      </div>
    </>
  );
}

export function AuthBox({ onDone, onPreview }) {
  const {
    data: { config },
    update,
  } = useBuro();
  const [method, setMethod] = useState(""),
    [consent, setConsent] = useState(false),
    [phone, setPhone] = useState(config.demo ? "+7 900 000-00-00" : ""),
    [otp, setOtp] = useState(null),
    [code, setCode] = useState("");
  const { busy, error, setError, run } = useAction();
  const methods = {
    yandex: "Яндекс ID",
    esia: "Госуслуги",
    phone: "По номеру телефона",
  };
  function success(r) {
    update(r);
    onDone(r);
  }
  function reset() {
    setMethod("");
    setOtp(null);
    setCode("");
    setError("");
    setConsent(false);
  }
  const agreement = { consent, version: config.consentVersion };
  async function next() {
    if (method === "phone") {
      if (otp) {
        success(
          await request("/auth/phone/verify", "POST", {
            challenge: otp.challenge,
            code,
          }),
        );
        return;
      }
      setOtp(
        await request("/auth/phone/request", "POST", { phone, ...agreement }),
      );
      return;
    }
    if (config.demo) {
      success(await request("/auth/demo/" + method, "POST", agreement));
    } else {
      const r = await request("/auth/" + method + "/start", "POST", agreement);
      window.location.assign(r.url);
    }
  }
  return (
    <div className="auth-box">
      {!method ? (
        <>
          <p className="modal-sub">
            Выберите удобный способ входа. Для нового пользователя кабинет
            создастся автоматически.
          </p>
          <div className="auth-options">
            {Object.entries(methods).map(([id, label]) => (
              <button
                disabled={!config.providers[id]}
                key={id}
                onClick={() => {
                  setMethod(id);
                  setError("");
                }}
              >
                <span className={"auth-brand " + id}>
                  {id === "phone" ? (
                    <Smartphone size={19} />
                  ) : id === "yandex" ? (
                    "Я"
                  ) : (
                    <ShieldCheck size={21} />
                  )}
                </span>
                <strong>{label}</strong>
                <span className="auth-arrow">
                  {config.providers[id] ? (
                    <ChevronRight size={17} />
                  ) : (
                    <small>Не подключено</small>
                  )}
                </span>
              </button>
            ))}
          </div>
          {config.demo && (
            <Notice Icon={Info}>
              Демо-вход без обращения к внешним сервисам. Настоящие учётные
              данные не нужны.
            </Notice>
          )}
          {onPreview && config.demo && (
            <button className="text-link auth-preview" onClick={onPreview}>
              Открыть демо без входа
              <ArrowRight size={15} />
            </button>
          )}
        </>
      ) : (
        <>
          <button className="back-link" onClick={reset}>
            <ArrowLeft size={14} />
            Все способы входа
          </button>
          <h3>{otp ? "Подтверждение номера" : methods[method]}</h3>
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              run(next);
            }}
          >
            {method === "phone" ? (
              otp ? (
                <>
                  <p className="field-help">
                    {config.demo
                      ? "Проверка тестового номера"
                      : "SMS отправлено на " + phone}
                    . Код действует 5 минут.
                  </p>
                  {otp.demoCode && (
                    <Notice Icon={Smartphone}>
                      Тестовый код: <b className="demo-code">{otp.demoCode}</b>
                    </Notice>
                  )}
                  <label>
                    Код из SMS
                    <input
                      autoFocus
                      className="code-input"
                      aria-label="Код из SMS"
                      value={code}
                      onChange={(e) =>
                        setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                      }
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      required
                      placeholder="000000"
                    />
                  </label>
                  <button
                    className="back-link"
                    type="button"
                    onClick={() => {
                      setOtp(null);
                      setCode("");
                      setError("");
                    }}
                  >
                    Запросить новый код
                  </button>
                </>
              ) : (
                <label>
                  Номер телефона
                  <input
                    autoComplete="tel"
                    type="tel"
                    value={phone}
                    readOnly={config.demo}
                    maxLength={25}
                    onChange={(e) => setPhone(e.target.value)}
                    required
                    placeholder="+7 900 000-00-00"
                  />
                  {config.demo && (
                    <small>Тестовый номер. SMS не отправляется.</small>
                  )}
                </label>
              )
            ) : (
              <Notice Icon={ShieldCheck}>
                {config.demo
                  ? `Это демонстрация входа через ${methods[method]}. Настоящего перехода к провайдеру не будет.`
                  : `Вы перейдёте на страницу авторизации ${method === "esia" ? "ЕСИА через подключённый шлюз" : "Яндекс ID"}. Мы не получаем ваш пароль.`}
              </Notice>
            )}
            {!otp && (
              <label className="consent-check">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                <span>
                  Даю{" "}
                  <a href={config.consentUrl} target="_blank" rel="noreferrer">
                    отдельное согласие на обработку персональных данных
                  </a>
                  .
                </span>
              </label>
            )}
            <ErrorLine error={error} />
            <Btn
              type="submit"
              busy={busy}
              disabled={!consent || (otp && code.length !== 6)}
              tail={ArrowRight}
            >
              {method === "phone"
                ? otp
                  ? "Войти в кабинет"
                  : "Получить код"
                : config.demo
                  ? "Продолжить в демо"
                  : "К провайдеру входа"}
            </Btn>
          </form>
        </>
      )}
      <a
        className="policy-link"
        href={config.policyUrl}
        target="_blank"
        rel="noreferrer"
      >
        <ShieldCheck size={13} />
        Политика обработки данных
      </a>
    </div>
  );
}

export default function Dialogs() {
  const { modal, close, go, show, notify } = useBuro();
  if (!modal) return null;
  const t = modal.type;
  const titles = {
    client: modal.item ? "Карточка клиента" : "Новый клиент",
    task: "Новая задача",
    goals: "Задачи вашего бизнеса",
    profile: "Профиль компании",
    checkout: "Подключение тарифа",
    remove: "Удалить запись?",
    login: "Вход в Бюро",
  };
  return (
    <Modal
      key={t}
      title={titles[t]}
      kicker={
        t === "goals"
          ? "БЫСТРЫЙ СТАРТ"
          : t === "login"
            ? "ЛИЧНЫЙ КАБИНЕТ"
            : t === "checkout"
              ? "ТАРИФ И ОПЛАТА"
              : undefined
      }
      onClose={close}
    >
      {t === "client" ? (
        <ClientForm item={modal.item} close={close} />
      ) : t === "task" ? (
        <TaskForm close={close} />
      ) : t === "profile" ? (
        <ProfileForm onDone={close} />
      ) : t === "goals" ? (
        <GoalForm onDone={close} />
      ) : t === "login" ? (
        <AuthBox
          onDone={(r) => {
            close();
            go("overview");
            notify("Вы вошли в кабинет");
            if (!r.user.goals.length) show("goals");
          }}
        />
      ) : (
        <Confirm modal={modal} close={close} />
      )}
    </Modal>
  );
}
