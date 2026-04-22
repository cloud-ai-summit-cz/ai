/**
 * Internationalization translations
 *
 * Supports Czech (cs) and English (en) languages.
 */

export type Language = 'cs' | 'en';

export interface Translations {
  // Landing page
  landing: {
    title: string;
    tagline: string;
    placeholder: string;
    tryExample: string;
    loadDemo: string;
    loadDemoDescription: string;
  };
  // Example queries
  exampleQueries: string[];
  // Header
  header: {
    researching: string;
    preparing: string;
    pending: string;
    complete: string;
    failed: string;
    newResearch: string;
    saveDemo: string;
    demoMode: string;
  };
  // Panel tabs
  panels: {
    activity: string;
    plan: string;
    notes: string;
    draft: string;
    finalReport: string;
  };
  // Activity panel
  activity: {
    title: string;
    empty: string;
  };
  // Plan panel
  plan: {
    title: string;
    empty: string;
    tasksCompleted: string;
  };
  // Notes panel
  notes: {
    title: string;
    empty: string;
  };
  // Draft panel
  draft: {
    title: string;
    empty: string;
  };
  // Final report
  finalReport: {
    title: string;
    empty: string;
    download: string;
  };
  // Questions
  questions: {
    title: string;
    pending: string;
    submit: string;
    placeholder: string;
  };
  // Common
  common: {
    loading: string;
    error: string;
    close: string;
  };
}

export const translations: Record<Language, Translations> = {
  cs: {
    landing: {
      title: 'Cofilot Research',
      tagline: 'AI průzkum trhu pro vaše další obchodní rozhodnutí',
      placeholder: 'Co byste chtěli prozkoumat?',
      tryExample: 'Vyzkoušejte příklad:',
      loadDemo: 'Načíst demo stav',
      loadDemoDescription: 'Načíst dříve uloženou výzkumnou session',
    },
    exampleQueries: [
      'Vyplatí se založit pobočku Cofilot ve Vídni?',
      'V Brně se rozšiřuje technologický park u VUT, vyplatí se tam mít pobočku Cofilot?',
      'Chceme expandovat do Brna nebo do Vídně, ale máme omezené investice. Kde začít?',
    ],
    header: {
      researching: 'Zkoumám...',
      preparing: 'Připravuji...',
      pending: 'Čeká se',
      complete: 'Dokončeno',
      failed: 'Selhalo',
      newResearch: 'Nový průzkum',
      saveDemo: 'Uložit demo',
      demoMode: 'Demo režim',
    },
    panels: {
      activity: 'Aktivita',
      plan: 'Plán',
      notes: 'Poznámky',
      draft: 'Koncept',
      finalReport: 'Závěrečná zpráva',
    },
    activity: {
      title: 'Časová osa aktivit',
      empty: 'Zatím žádná aktivita',
    },
    plan: {
      title: 'Plán výzkumu',
      empty: 'Plán bude vygenerován po spuštění výzkumu',
      tasksCompleted: 'úkolů dokončeno',
    },
    notes: {
      title: 'Výzkumné poznámky',
      empty: 'Poznámky budou shromážděny během výzkumu',
    },
    draft: {
      title: 'Koncept zprávy',
      empty: 'Koncept bude vytvořen na základě poznámek',
    },
    finalReport: {
      title: 'Závěrečná zpráva',
      empty: 'Závěrečná zpráva bude k dispozici po dokončení výzkumu',
      download: 'Stáhnout zprávu',
    },
    questions: {
      title: 'Otázky',
      pending: 'čekající',
      submit: 'Odeslat odpověď',
      placeholder: 'Zadejte odpověď...',
    },
    common: {
      loading: 'Načítání...',
      error: 'Chyba',
      close: 'Zavřít',
    },
  },
  en: {
    landing: {
      title: 'Cofilot Research',
      tagline: 'AI-powered market research for your next business move',
      placeholder: 'What would you like to research?',
      tryExample: 'Try an example:',
      loadDemo: 'Load Demo State',
      loadDemoDescription: 'Load a previously saved research session',
    },
    exampleQueries: [
      'Should Cofilot open a branch in Vienna?',
      'The technology park at VUT in Brno is expanding, should Cofilot have a branch there?',
      'We want to expand to Brno or Vienna, but we have limited investments. Where to start?',
    ],
    header: {
      researching: 'Researching...',
      preparing: 'Preparing...',
      pending: 'Pending',
      complete: 'Complete',
      failed: 'Failed',
      newResearch: 'New Research',
      saveDemo: 'Save Demo',
      demoMode: 'Demo Mode',
    },
    panels: {
      activity: 'Activity',
      plan: 'Plan',
      notes: 'Notes',
      draft: 'Draft',
      finalReport: 'Final Report',
    },
    activity: {
      title: 'Activity Timeline',
      empty: 'No activity yet',
    },
    plan: {
      title: 'Research Plan',
      empty: 'Plan will be generated when research starts',
      tasksCompleted: 'tasks completed',
    },
    notes: {
      title: 'Research Notes',
      empty: 'Notes will be gathered during research',
    },
    draft: {
      title: 'Draft Report',
      empty: 'Draft will be created from notes',
    },
    finalReport: {
      title: 'Final Report',
      empty: 'Final report will be available when research completes',
      download: 'Download Report',
    },
    questions: {
      title: 'Questions',
      pending: 'pending',
      submit: 'Submit Answer',
      placeholder: 'Enter your answer...',
    },
    common: {
      loading: 'Loading...',
      error: 'Error',
      close: 'Close',
    },
  },
};
