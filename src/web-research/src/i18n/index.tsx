/**
 * i18n Context and Hook
 *
 * Provides language state and translations throughout the app.
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { translations, type Language, type Translations } from './translations';

interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

const STORAGE_KEY = 'cofilot-language';

interface I18nProviderProps {
  children: ReactNode;
}

export function I18nProvider({ children }: I18nProviderProps) {
  const [language, setLanguageState] = useState<Language>(() => {
    // Check localStorage first
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'cs' || stored === 'en') {
        return stored;
      }
    }
    // Default to Czech
    return 'cs';
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem(STORAGE_KEY, lang);
  };

  // Sync with localStorage on mount
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  const value: I18nContextType = {
    language,
    setLanguage,
    t: translations[language],
  };

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextType {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

export { type Language, type Translations };
