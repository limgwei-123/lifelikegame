export const weekDayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export function formatWeeklyDays(days) {
  if (!Array.isArray(days) || days.length === 0) return "Weekly";

  return days
    .map((day) => weekDayNames[Number(day)])
    .filter(Boolean)
    .join(", ");
}

export function formatSimpleScheduleLabel(scheduleType) {
  if (scheduleType === "daily") return "Daily";
  if (scheduleType === "weekly") return "Weekly";
  if (scheduleType === "monthly") return "Monthly";
  if (scheduleType === "once") return "Once";

  return scheduleType || "Scheduled";
}

export function formatScheduleLabel(scheduleType, scheduleValue = {}) {
  if (scheduleType === "weekly") return `Weekly: ${formatWeeklyDays(scheduleValue.days)}`;
  if (scheduleType === "monthly") return `Monthly: day ${scheduleValue.day ?? 1}`;

  return formatSimpleScheduleLabel(scheduleType);
}
