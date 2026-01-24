/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        book: {
          primary: 'var(--color-primary)',
          'primary-light': 'var(--color-primary-light)',
          'text-main': 'var(--color-text-primary)',
          'text-sub': 'var(--color-text-secondary)',
          'text-muted': 'var(--color-text-tertiary)',
          bg: 'var(--color-bg-primary)',
          'bg-paper': 'var(--color-bg-secondary)',
          'bg-glass': 'var(--color-bg-glass)',
          border: 'var(--color-border)',
        }
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', 'serif'],
        sans: ['"Noto Sans SC"', 'sans-serif'],
      },
      boxShadow: {
        'book-card': 'var(--shadow-card)',
        'glass': 'var(--shadow-glass)',
      }
    },
  },
  plugins: [],
}