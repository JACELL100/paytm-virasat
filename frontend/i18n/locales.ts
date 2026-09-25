export const SUPPORTED_LOCALES = ["en", "hi", "mr"] as const;
export type AppLocale = (typeof SUPPORTED_LOCALES)[number];
export const DEFAULT_LOCALE: AppLocale = "en";
export const LOCALE_COOKIE = "NEXT_LOCALE";

/** Plain helper (not a component/hook) so writing to `document.cookie` doesn't trip the
 * react-hooks immutability rule, which flags mutations inside component bodies. */
export function setLocaleCookie(locale: AppLocale) {
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=31536000`;
}
