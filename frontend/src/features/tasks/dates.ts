// Calendar-only arithmetic: these values are player dates, never device instants.
function dateObject(value: string) {
  const [y, m, d] = value.split('-').map(Number);
  const result = new Date(0);
  result.setUTCFullYear(y, m - 1, d); result.setUTCHours(12, 0, 0, 0);
  return result;
}
function format(value: Date) {
  return `${String(value.getUTCFullYear()).padStart(4, '0')}-${String(value.getUTCMonth() + 1).padStart(2, '0')}-${String(value.getUTCDate()).padStart(2, '0')}`;
}
export function validDate(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number(value.slice(0, 4)) >= 1 && format(dateObject(value)) === value;
}
export function addDays(value: string, amount: number) {
  const day = dateObject(value); day.setUTCDate(day.getUTCDate() + amount); return format(day);
}
export function weekday(value: string) { return (dateObject(value).getUTCDay() + 6) % 7; }
export function shiftMonth(value: string, amount: number) {
  const day = dateObject(value), original = day.getUTCDate();
  day.setUTCDate(1); day.setUTCMonth(day.getUTCMonth() + amount);
  const end = new Date(day); end.setUTCMonth(end.getUTCMonth() + 1, 0);
  day.setUTCDate(Math.min(original, end.getUTCDate())); return format(day);
}
export function monthGrid(value: string): (string | null)[] {
  const first = `${value.slice(0, 7)}-01`, result: (string | null)[] = Array(weekday(first)).fill(null);
  for (let day = first; day.slice(0, 7) === first.slice(0, 7); day = addDays(day, 1)) result.push(day);
  while (result.length % 7) result.push(null);
  return result;
}
export function dateLabel(value: string) {
  return `${Number(value.slice(5, 7))}月${Number(value.slice(8))}日`;
}
export const weekNames = ['一', '二', '三', '四', '五', '六', '日'];
