/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f5f7ff',
          100: '#ebf0ff',
          200: '#c3cfff',  
          400: '#889cf2',
          500: '#667eea',
          600: '#5568d3',
          700: '#4c52bb',
        },
        secondary: {
          500: '#764ba2',
          600: '#6a4391',
        }
      }
    },
  },
  plugins: [],
}