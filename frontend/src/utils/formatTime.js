/**
 * Utility functions for formatting time and duration values
 */

/**
 * Formats decimal hours into human-readable hours and minutes
 * @param {number} decimalHours - Hours in decimal format (e.g., 9.97)
 * @param {boolean} compact - If true, returns compact format for mobile (e.g., "9h 58m")
 * @returns {string} Formatted string (e.g., "9 hours 58 minutes" or "9h 58m")
 */
export const formatHoursMinutes = (decimalHours, compact = false) => {
  if (!decimalHours && decimalHours !== 0) return '0 minutes';

  const totalMinutes = Math.round(decimalHours * 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (compact) {
    // Compact format for mobile
    if (hours === 0) return `${minutes}m`;
    if (minutes === 0) return `${hours}h`;
    return `${hours}h ${minutes}m`;
  }

  // Full format for desktop
  if (hours === 0) {
    return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
  }

  if (minutes === 0) {
    return `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
  }

  return `${hours} ${hours === 1 ? 'hour' : 'hours'} ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
};
