/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Couleurs principales MIA IA SYSTEM
        mia: {
          gold: '#D4AF37',
          'gold-light': '#E5C158',
          'gold-dark': '#B8960C',
          cyan: '#00B4DC',
          'cyan-light': '#33C9E8',
          'cyan-dark': '#0090B0',
          blue: '#1E3A5F',
          'blue-dark': '#0A1628',
        },
        // Background
        dark: {
          DEFAULT: '#0A0E17',
          100: '#0D1321',
          200: '#131722',
          300: '#1C2333',
          400: '#252D3D',
        },
        // Texte
        light: {
          DEFAULT: '#FFFFFF',
          100: '#F8FAFC',
          200: '#E2E8F0',
          300: '#CBD5E1',
          400: '#94A3B8',
          500: '#64748B',
        },
        // Accents
        accent: {
          success: '#00C853',
          warning: '#FFB300',
          error: '#FF5252',
          purple: '#6366F1',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-slow': 'float 8s ease-in-out infinite',
        'glow': 'glow 4s ease-in-out infinite',
        'shimmer': 'shimmer 3s linear infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 20s linear infinite',
        'bounce-slow': 'bounce 3s infinite',
        'fade-in': 'fadeIn 0.6s ease-out forwards',
        'fade-in-up': 'fadeInUp 0.6s ease-out forwards',
        'fade-in-down': 'fadeInDown 0.6s ease-out forwards',
        'scale-in': 'scaleIn 0.5s ease-out forwards',
        'slide-in-right': 'slideInRight 0.5s ease-out forwards',
        'slide-in-left': 'slideInLeft 0.5s ease-out forwards',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        glow: {
          '0%, 100%': { 
            boxShadow: '0 0 40px rgba(212, 175, 55, 0.4), 0 0 80px rgba(0, 180, 220, 0.2)',
            borderColor: 'rgba(212, 175, 55, 0.7)',
          },
          '50%': { 
            boxShadow: '0 0 60px rgba(212, 175, 55, 0.6), 0 0 120px rgba(0, 180, 220, 0.3)',
            borderColor: 'rgba(212, 175, 55, 0.9)',
          },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeInDown: {
          '0%': { opacity: '0', transform: 'translateY(-30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(50px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        slideInLeft: {
          '0%': { opacity: '0', transform: 'translateX(-50px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'mia-gradient': 'linear-gradient(135deg, #D4AF37 0%, #00B4DC 50%, #1E3A5F 100%)',
        'mia-gradient-text': 'linear-gradient(90deg, #FFFFFF, #00B4DC, #D4AF37)',
      },
      boxShadow: {
        'glow-gold': '0 0 40px rgba(212, 175, 55, 0.4)',
        'glow-cyan': '0 0 40px rgba(0, 180, 220, 0.4)',
        'glow-mia': '0 0 40px rgba(212, 175, 55, 0.3), 0 0 80px rgba(0, 180, 220, 0.2)',
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
