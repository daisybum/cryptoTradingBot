/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          light: '#4da6ff',
          DEFAULT: '#0078ff',
          dark: '#0057b8',
        },
        secondary: {
          light: '#8c54ff',
          DEFAULT: '#6200ee',
          dark: '#4b00b5',
        },
        success: {
          light: '#4caf50',
          DEFAULT: '#2e7d32',
          dark: '#1b5e20',
        },
        danger: {
          light: '#ef5350',
          DEFAULT: '#d32f2f',
          dark: '#b71c1c',
        },
        warning: {
          light: '#ffb74d',
          DEFAULT: '#ff9800',
          dark: '#f57c00',
        },
        info: {
          light: '#4fc3f7',
          DEFAULT: '#29b6f6',
          dark: '#0288d1',
        },
      },
    },
  },
  plugins: [],
}
