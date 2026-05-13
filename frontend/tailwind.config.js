/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'sv-bg':        '#f8fffe',
        'sv-green':     '#16a34a',
        'sv-green-light': '#22c55e',
        'sv-mint':      '#f0fdf4',
        'sv-border':    '#bbf7d0',
        'sv-danger':    '#dc2626',
        'sv-danger-bg': '#fef2f2',
      },
    },
  },
  plugins: [],
}
