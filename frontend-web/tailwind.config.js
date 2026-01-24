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
          // 使用 rgb(var(--token) / <alpha-value>) 形式，保证 Tailwind 的 /xx 透明度语法可用
          primary: 'rgb(var(--color-primary) / <alpha-value>)',
          'primary-light': 'rgb(var(--color-primary-light) / <alpha-value>)',
          'text-main': 'rgb(var(--color-text-primary) / <alpha-value>)',
          'text-sub': 'rgb(var(--color-text-secondary) / <alpha-value>)',
          'text-muted': 'rgb(var(--color-text-tertiary) / <alpha-value>)',
          bg: 'rgb(var(--color-bg-primary) / <alpha-value>)',
          'bg-paper': 'rgb(var(--color-bg-secondary) / <alpha-value>)',
          // 玻璃态背景默认固定 0.85 透明度（避免被 /xx 覆盖导致不透明）
          'bg-glass': 'rgb(var(--color-bg-glass) / 0.85)',
          border: 'rgb(var(--color-border) / <alpha-value>)',
          accent: 'rgb(var(--color-primary) / <alpha-value>)',
        }
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', 'serif'],
        sans: ['"Noto Sans SC"', 'sans-serif'],
      },
      boxShadow: {
        'book-card': 'var(--shadow-card)',
        'glass': 'var(--shadow-glass)',
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 },
        },
        slideInFromLeft: {
          "0%": { transform: "translateX(-20px)", opacity: 0 },
          "100%": { transform: "translateX(0)", opacity: 1 },
        },
        slideInFromBottom: {
          "0%": { transform: "translateY(20px)", opacity: 0 },
          "100%": { transform: "translateY(0)", opacity: 1 },
        },
        zoomIn: {
          "0%": { opacity: 0, transform: "scale(0.95)" },
          "100%": { opacity: 1, transform: "scale(1)" },
        },
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out",
        "slide-in-left": "slideInFromLeft 0.5s ease-out",
        "slide-in-bottom": "slideInFromBottom 0.5s ease-out",
        "zoom-in": "zoomIn 0.3s ease-out",
      },
    },
  },
  plugins: [
    // Simple plugin to match 'animate-in' utility behavior if needed, 
    // or just rely on custom classes
    function({ addUtilities }) {
      addUtilities({
        '.animate-in': {
          'animation-fill-mode': 'forwards',
        },
        '.slide-in-from-left-4': {
          '--tw-enter-translate-x': '-1rem',
          'animation': 'enter 0.5s ease-out',
        },
        '.slide-in-from-bottom-2': {
          '--tw-enter-translate-y': '0.5rem',
          'animation': 'enter 0.3s ease-out',
        },
        '@keyframes enter': {
          '0%': {
            opacity: '0',
            transform: 'translate3d(var(--tw-enter-translate-x, 0), var(--tw-enter-translate-y, 0), 0) scale3d(var(--tw-enter-scale, 1), var(--tw-enter-scale, 1), var(--tw-enter-scale, 1))',
          },
          '100%': {
            opacity: '1',
            transform: 'translate3d(0, 0, 0) scale3d(1, 1, 1)',
          },
        }
      })
    }
  ],
}
