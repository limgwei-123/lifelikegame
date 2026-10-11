export function apiErrorMessage(data) {
  if (typeof data === "string") return data;
  if (typeof data?.message === "string") return data.message;
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) {
    const messages = data.detail.filter((item) => typeof item.msg === "string").map((item) => {
      const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
      return field ? `${field}: ${item.msg}` : item.msg;
    });
    if (messages.length) return messages.join("; ");
  }
  return "API request failed";
}
