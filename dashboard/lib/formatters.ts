/**
 * Format large numbers into K/M notation with one decimal place
 * 13000 -> 13.0K
 * 1000000 -> 1.0M
 * 
 * @param num - Number to format
 * @returns Formatted string with one decimal place
 */
export function formatStarCount(num: number | null | undefined): string {
  if (num === null || num === undefined) {
    return '0'
  }
  
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  
  return num.toString()
}

