import { test, expect } from "@playwright/test";

test("read both documents from the Yandex login form without consenting", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByRole("button", { name: /Яндекс ID/ }).click();
  const checkbox = page.getByRole("checkbox");
  const proceed = page.getByRole("button", { name: "Продолжить в демо" });
  await expect(checkbox).not.toBeChecked();
  await expect(proceed).toBeDisabled();

  for (const [link, path, title] of [
    [
      "Политика обработки данных",
      "/legal/policy",
      "Политика обработки персональных данных",
    ],
    [
      "отдельное согласие на обработку персональных данных",
      "/legal/consent",
      "Согласие на обработку персональных данных",
    ],
  ]) {
    const popup = page.waitForEvent("popup");
    await page.getByRole("link", { name: link, exact: true }).click();
    const document = await popup;
    await expect(document).toHaveURL(new URL(path, page.url()).href);
    await expect(
      document.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
    await expect(
      document.getByText("Иван Пупкин", { exact: true }),
    ).toBeVisible();
    await document.close();
  }
  await expect(checkbox).not.toBeChecked();
  await expect(proceed).toBeDisabled();
  await checkbox.check();
  await expect(proceed).toBeEnabled();
});
