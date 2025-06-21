// Language preference persistence utilities

const LANGUAGE_PREFERENCE_KEY = 'voice_language_preference';
const DETECTION_HISTORY_KEY = 'language_detection_history';

export interface LanguagePreference {
  language: string;
  isManual: boolean;
  lastUsed: number;
  confidence?: number;
}

export interface DetectionHistoryEntry {
  language: string;
  confidence: number;
  timestamp: number;
  source: 'auto' | 'manual';
}

/**
 * Save user's language preference to localStorage
 */
export function saveLanguagePreference(preference: LanguagePreference): void {
  try {
    localStorage.setItem(LANGUAGE_PREFERENCE_KEY, JSON.stringify(preference));
  } catch (error) {
    console.warn('Failed to save language preference:', error);
  }
}

/**
 * Load user's language preference from localStorage
 */
export function loadLanguagePreference(): LanguagePreference | null {
  try {
    const stored = localStorage.getItem(LANGUAGE_PREFERENCE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.warn('Failed to load language preference:', error);
  }
  return null;
}

/**
 * Add detection history entry
 */
export function addDetectionHistory(entry: DetectionHistoryEntry): void {
  try {
    const stored = localStorage.getItem(DETECTION_HISTORY_KEY);
    let history: DetectionHistoryEntry[] = stored ? JSON.parse(stored) : [];
    
    // Add new entry
    history.push(entry);
    
    // Keep only last 50 entries
    if (history.length > 50) {
      history = history.slice(-50);
    }
    
    localStorage.setItem(DETECTION_HISTORY_KEY, JSON.stringify(history));
  } catch (error) {
    console.warn('Failed to save detection history:', error);
  }
}

/**
 * Get language detection history
 */
export function getDetectionHistory(): DetectionHistoryEntry[] {
  try {
    const stored = localStorage.getItem(DETECTION_HISTORY_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.warn('Failed to load detection history:', error);
    return [];
  }
}

/**
 * Get user's most frequently detected languages
 */
export function getFrequentLanguages(): Array<{ language: string; count: number; avgConfidence: number }> {
  const history = getDetectionHistory();
  const languageStats: Record<string, { count: number; totalConfidence: number }> = {};
  
  // Count occurrences and sum confidence
  history.forEach(entry => {
    if (!languageStats[entry.language]) {
      languageStats[entry.language] = { count: 0, totalConfidence: 0 };
    }
    languageStats[entry.language].count++;
    languageStats[entry.language].totalConfidence += entry.confidence;
  });
  
  // Convert to array and calculate averages
  return Object.entries(languageStats)
    .map(([language, stats]) => ({
      language,
      count: stats.count,
      avgConfidence: stats.totalConfidence / stats.count
    }))
    .sort((a, b) => b.count - a.count) // Sort by frequency
    .slice(0, 5); // Top 5
}

/**
 * Smart language suggestion based on history and context
 */
export function suggestLanguage(): string {
  const preference = loadLanguagePreference();
  
  // If user has a recent manual preference, use it
  if (preference && preference.isManual) {
    const timeSinceLastUse = Date.now() - preference.lastUsed;
    // Use manual preference if used within last 7 days
    if (timeSinceLastUse < 7 * 24 * 60 * 60 * 1000) {
      return preference.language;
    }
  }
  
  // Otherwise, suggest most frequent auto-detected language
  const frequentLanguages = getFrequentLanguages();
  if (frequentLanguages.length > 0) {
    return frequentLanguages[0].language;
  }
  
  // Default to auto-detection
  return 'auto';
}

/**
 * Clear all language data (for privacy/reset)
 */
export function clearLanguageData(): void {
  try {
    localStorage.removeItem(LANGUAGE_PREFERENCE_KEY);
    localStorage.removeItem(DETECTION_HISTORY_KEY);
  } catch (error) {
    console.warn('Failed to clear language data:', error);
  }
}