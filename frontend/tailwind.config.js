/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: { 50: '#f0f1f8', 100: '#d9daf0', 500: '#302b63', 700: '#1a1a2e', 900: '#0f0c29' }
      }
    }
  },
  plugins: [],
}
