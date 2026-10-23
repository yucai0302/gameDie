/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        ink: {
          900: "rgb(var(--ink-900) / <alpha-value>)",
          800: "rgb(var(--ink-800) / <alpha-value>)",
          700: "rgb(var(--ink-700) / <alpha-value>)",
          600: "rgb(var(--ink-600) / <alpha-value>)",
          500: "rgb(var(--ink-500) / <alpha-value>)",
          400: "rgb(var(--ink-400) / <alpha-value>)",
        },
        flame: {
          DEFAULT: "rgb(var(--flame) / <alpha-value>)",
          soft: "rgb(var(--flame-soft) / <alpha-value>)",
          deep: "rgb(var(--flame-deep) / <alpha-value>)",
          glow: "rgba(var(--flame), 0.4)",
        },
        cyan: {
          neon: "rgb(var(--cyan-neon) / <alpha-value>)",
          soft: "rgb(var(--cyan-soft) / <alpha-value>)",
          glow: "rgba(var(--cyan-neon), 0.4)",
        },
        lime: {
          neon: "rgb(var(--lime-neon) / <alpha-value>)",
          soft: "rgb(var(--lime-soft) / <alpha-value>)",
        },
        mist: {
          100: "rgb(var(--mist-100) / <alpha-value>)",
          200: "rgb(var(--mist-200) / <alpha-value>)",
          300: "rgb(var(--mist-300) / <alpha-value>)",
          400: "rgb(var(--mist-400) / <alpha-value>)",
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', '"PingFang SC"', '"Noto Sans SC"', "sans-serif"],
        sans: ['"Noto Sans SC"', '"PingFang SC"', '"Space Grotesk"', "sans-serif"],
        mono: ['"JetBrains Mono"', '"SF Mono"', "Menlo", "monospace"],
      },
      borderRadius: {
        xl: "12px",
        "2xl": "16px",
        "3xl": "24px",
      },
      boxShadow: {
        glow: "0 0 30px rgba(var(--flame), 0.25)",
        "glow-cyan": "0 0 30px rgba(var(--cyan-neon), 0.25)",
        card: "0 8px 32px rgba(0, 0, 0, 0.4)",
      },
      backdropBlur: {
        glass: "20px",
      },
      keyframes: {
        "pulse-flame": {
          "0%, 100%": { opacity: "1", filter: "drop-shadow(0 0 4px rgba(var(--flame), 0.6))" },
          "50%": { opacity: "0.6", filter: "drop-shadow(0 0 8px rgba(var(--flame), 0.9))" },
        },
        "slide-in-top": {
          "0%": { transform: "translateY(-12px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        "flash-row": {
          "0%": { backgroundColor: "rgba(var(--flame), 0.25)" },
          "100%": { backgroundColor: "transparent" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "pulse-flame": "pulse-flame 1.4s ease-in-out infinite",
        "slide-in-top": "slide-in-top 0.4s cubic-bezier(0.22, 1, 0.36, 1)",
        "flash-row": "flash-row 2s ease-out",
        "shimmer": "shimmer 2.5s linear infinite",
      },
    },
  },
  plugins: [],
};
