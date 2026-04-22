/// <reference types="vite/client" />

declare global {
  interface Window {
    env: {
      API_URL: string;
      APP_VERSION?: string;
      ENABLE_MOCK?: boolean;
    };
  }
}

export {};
