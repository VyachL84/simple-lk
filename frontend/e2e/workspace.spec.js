import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  const ready = page.waitForResponse((r) => r.url().endsWith("/api/open"));
  await page.goto("/");
  expect(
    (await (await ready).json()).config.demo,
    "Use a local demo, never a customer database",
  ).toBe(true);
  await expect(
    page.getByRole("heading", { name: "Обзор кабинета" }),
  ).toBeVisible();
});

test("goals, client, task, upgrade and persisted entitlement", async ({
  page,
}) => {
  await page.getByRole("button", { name: /Выбрать задачи бизнеса/ }).click();
  await page.getByRole("button", { name: /Вести клиентскую базу/ }).click();
  await page.getByRole("button", { name: "Сохранить цели" }).click();
  await expect(page.locator(".quick-start .count-badge")).toHaveText("2 из 4");
  await page.getByRole("button", { name: /Заполнить профиль/ }).click();
  await page.getByLabel("Как к вам обращаться").fill("Демо");
  await page.getByLabel("Название компании").fill("Студия Тест");
  await page.getByRole("button", { name: "Сохранить профиль" }).click();
  await expect(page.locator(".quick-start .count-badge")).toHaveText("3 из 4");
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Клиенты" })
    .click();
  await page.getByRole("button", { name: "Добавить клиента" }).click();
  await page.getByLabel("Имя клиента").fill("Учебный клиент");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Добавить клиента" })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("Поиск клиентов").fill("учебный");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page
    .getByRole("navigation")
    .getByRole("link", { name: /Мои задачи/ })
    .click();
  await page.getByRole("button", { name: "Новая задача" }).click();
  await page.getByLabel("Что нужно сделать?").fill("Проверить план");
  await page.getByRole("button", { name: "Создать задачу" }).click();
  await page.getByRole("checkbox", { name: "Статус: Проверить план" }).click();
  await page.getByRole("button", { name: "Готово", exact: true }).click();
  await expect(
    page.getByRole("checkbox", { name: "Статус: Проверить план" }),
  ).toBeChecked();
  await page.getByRole("link", { name: "Тариф и оплата", exact: true }).click();
  await page.getByRole("button", { name: "Подключить Бизнес" }).click();
  await page.getByRole("button", { name: "Подключить в демо" }).click();
  await expect(
    page.getByText("Подключён тариф Бизнес", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Подключён тариф Бизнес", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Клиенты" })
    .click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Экспорт CSV" }).click();
  expect((await download).suggestedFilename()).toBe("buro-clients.csv");
});

test("phone login and explicit logout", async ({ page }) => {
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await page.getByRole("button", { name: /По номеру телефона/ }).click();
  await expect(
    page.getByRole("button", { name: "Получить код" }),
  ).toBeDisabled();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Получить код" }).click();
  await page
    .getByLabel("Код из SMS", { exact: true })
    .fill(await page.locator(".demo-code").innerText());
  await page.getByRole("button", { name: "Войти в кабинет" }).click();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("heading", { name: "Задачи вашего бизнеса" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();
  await page.getByRole("link", { name: "Настройки", exact: true }).click();
  await expect(
    page.getByText("По телефону", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Выйти из кабинета" }).click();
  await expect(
    page.getByRole("heading", { name: "Вход в Бюро" }),
  ).toBeVisible();
});

test("mobile navigation, notifications and help", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Уведомления", exact: true }).click();
  await page.getByRole("button", { name: "Отметить прочитанными" }).click();
  await expect(page.getByText("Все уведомления прочитаны")).toBeVisible();
  await page.getByRole("button", { name: "Закрыть уведомления" }).click();
  await page.getByRole("button", { name: "Открыть навигацию" }).click();
  await page.getByRole("button", { name: "Центр помощи", exact: true }).click();
  await page.getByText("Что произойдёт после 14 дней?").click();
  await expect(page.locator("details[open] p")).toBeVisible();
  for (const link of await page.locator("a.guide").all()) {
    expect((await page.request.get(await link.getAttribute("href"))).ok()).toBe(
      true,
    );
  }
});
