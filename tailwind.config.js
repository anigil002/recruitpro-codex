/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // Unified primary color - using #1173d4 across entire app
        primary: {
          DEFAULT: '#1173d4',
          50: '#e6f2fd',
          100: '#b3d9f9',
          200: '#80c0f5',
          300: '#4da7f1',
          400: '#2d8ae8',
          500: '#1173d4',
          600: '#0d5aa8',
          700: '#0a447c',
          800: '#072d50',
          900: '#041724',
        },
        // Background colors
        background: {
          light: '#f6f7f8',
          dark: '#101922',
        },
        // Surface colors
        surface: {
          light: '#ffffff',
          dark: '#111a22',
          elevated: '#1a2633',
          border: '#233648',
        },
        // Text colors with proper contrast
        text: {
          primary: '#ffffff',
          secondary: '#cbd5e1',
          muted: '#94a3b8',
          'primary-light': '#0f172a',
          'secondary-light': '#475569',
          'muted-light': '#64748b',
        },
        // Semantic colors
        success: '#15d58a',
        warning: '#f59e0b',
        error: '#ef4444',
        info: '#3b82f6',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      spacing: {
        xs: '0.25rem',
        sm: '0.5rem',
        md: '1rem',
        lg: '1.5rem',
        xl: '2rem',
        '2xl': '2.5rem',
        '3xl': '3rem',
      },
      borderRadius: {
        DEFAULT: '0.5rem',
        sm: '0.25rem',
        md: '0.5rem',
        lg: '0.75rem',
        xl: '1rem',
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(17, 115, 212, 0.2)',
        'glow': '0 0 20px rgba(17, 115, 212, 0.3)',
        'glow-lg': '0 0 30px rgba(17, 115, 212, 0.4)',
      },
    },
  },
  plugins: [],
}
