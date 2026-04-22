/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ChatGPT-inspired grayscale palette
        'surface': {
          DEFAULT: '#212121',
          light: '#2f2f2f',
          lighter: '#424242',
          dark: '#171717',
          darker: '#0d0d0d',
        },
        'text': {
          DEFAULT: '#ececec',
          muted: '#9b9b9b',
          dim: '#6b6b6b',
        },
        'border': {
          DEFAULT: '#424242',
          light: '#4a4a4a',
        },
        'accent': {
          DEFAULT: '#10a37f',
          hover: '#1a7f64',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
