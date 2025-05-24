module.exports = {
	darkMode: ["class"],
	content: [
		"./index.html",
		"./src/**/*.{js,jsx}", // Main JS/JSX files
		"./src/components/ui/**/*.{ts,tsx}", // Only TS/TSX for UI components
	  ],
	prefix: "",
	theme: {
	  container: {
		center: true,
		padding: '2rem',
		screens: {
		  '2xl': '1400px'
		}
	  },
	  extend: {
		fontFamily: {
		  sans: ['Inter', 'SF Pro Display', 'sans-serif'],
		  mono: ['SF Mono', 'monospace'],
		},
		colors: {
		  border: 'hsl(var(--border))',
		  input: 'hsl(var(--input))',
		  ring: 'hsl(var(--ring))',
		  background: 'hsl(var(--background))',
		  foreground: 'hsl(var(--foreground))',
		  primary: {
			DEFAULT: 'hsl(var(--primary))',
			foreground: 'hsl(var(--primary-foreground))'
		  },
		  secondary: {
			DEFAULT: 'hsl(var(--secondary))',
			foreground: 'hsl(var(--secondary-foreground))'
		  },
		  destructive: {
			DEFAULT: 'hsl(var(--destructive))',
			foreground: 'hsl(var(--destructive-foreground))'
		  },
		  muted: {
			DEFAULT: 'hsl(var(--muted))',
			foreground: 'hsl(var(--muted-foreground))'
		  },
		  accent: {
			DEFAULT: 'hsl(var(--accent))',
			foreground: 'hsl(var(--accent-foreground))'
		  },
		  popover: {
			DEFAULT: 'hsl(var(--popover))',
			foreground: 'hsl(var(--popover-foreground))'
		  },
		  card: {
			DEFAULT: 'hsl(var(--card))',
			foreground: 'hsl(var(--card-foreground))'
		  },
		  sidebar: {
			DEFAULT: 'hsl(var(--sidebar-background))',
			foreground: 'hsl(var(--sidebar-foreground))',
			primary: 'hsl(var(--sidebar-primary))',
			'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
			accent: 'hsl(var(--sidebar-accent))',
			'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
			border: 'hsl(var(--sidebar-border))',
			ring: 'hsl(var(--sidebar-ring))'
		  }
		},
		borderRadius: {
		  lg: 'var(--radius)',
		  md: 'calc(var(--radius) - 2px)',
		  sm: 'calc(var(--radius) - 4px)'
		},
		keyframes: {
		  'accordion-down': {
			from: { height: '0' },
			to: { height: 'var(--radix-accordion-content-height)' }
		  },
		  'accordion-up': {
			from: { height: 'var(--radix-accordion-content-height)' },
			to: { height: '0' }
		  },
		  'fade-in': {
			'0%': { opacity: '0', transform: 'translateY(10px)' },
			'100%': { opacity: '1', transform: 'translateY(0)' }
		  },
		  'fade-out': {
			'0%': { opacity: '1', transform: 'translateY(0)' },
			'100%': { opacity: '0', transform: 'translateY(10px)' }
		  },
		  'scale-in': {
			'0%': { transform: 'scale(0.95)', opacity: '0' },
			'100%': { transform: 'scale(1)', opacity: '1' }
		  },
		  'scale-out': {
			from: { transform: 'scale(1)', opacity: '1' },
			to: { transform: 'scale(0.95)', opacity: '0' }
		  },
		  'slide-in': {
			'0%': { transform: 'translateX(-100%)' },
			'100%': { transform: 'translateX(0)' }
		  },
		  'slide-out': {
			'0%': { transform: 'translateX(0)' },
			'100%': { transform: 'translateX(-100%)' }
		  },
		  'slide-up': {
			'0%': { transform: 'translateY(100%)' },
			'100%': { transform: 'translateY(0)' }
		  },
		  'slide-down': {
			'0%': { transform: 'translateY(0)' },
			'100%': { transform: 'translateY(100%)' }
		  },
		  'float': {
			'0%, 100%': { transform: 'translateY(0)' },
			'50%': { transform: 'translateY(-10px)' }
		  },
		  'pulse-slow': {
			'0%, 100%': { opacity: '1' },
			'50%': { opacity: '0.8' }
		  },
		  'spin-slow': {
			'0%': { transform: 'rotate(0deg)' },
			'100%': { transform: 'rotate(360deg)' }
		  },
		  'bounce-subtle': {
			'0%, 100%': { transform: 'translateY(0)' },
			'50%': { transform: 'translateY(-5px)' }
		  },
		  'shimmer': {
			'0%': { backgroundPosition: '-200% 0' },
			'100%': { backgroundPosition: '200% 0' }
		  },
		  'ripple': {
			'0%': { transform: 'scale(0)', opacity: '1' },
			'100%': { transform: 'scale(4)', opacity: '0' }
		  },
		  'typewriter': {
			'from': { width: '0' },
			'to': { width: '100%' }
		  },
		  'blink-caret': {
			'50%': { borderColor: 'transparent' }
		  },
		  'wave': {
			'0%': { transform: 'rotate(0deg)' },
			'10%': { transform: 'rotate(14deg)' },
			'20%': { transform: 'rotate(-8deg)' },
			'30%': { transform: 'rotate(14deg)' },
			'40%': { transform: 'rotate(-4deg)' },
			'50%': { transform: 'rotate(10deg)' },
			'60%': { transform: 'rotate(0deg)' },
			'100%': { transform: 'rotate(0deg)' }
		  },
		  'gradient-move': {
			'0%': { backgroundPosition: '0% 50%' },
			'50%': { backgroundPosition: '100% 50%' },
			'100%': { backgroundPosition: '0% 50%' }
		  }
		},
		animation: {
		  'accordion-down': 'accordion-down 0.2s ease-out',
		  'accordion-up': 'accordion-up 0.2s ease-out',
		  'fade-in': 'fade-in 0.6s ease-out',
		  'fade-out': 'fade-out 0.6s ease-out',
		  'scale-in': 'scale-in 0.4s ease-out',
		  'scale-out': 'scale-out 0.4s ease-out',
		  'slide-in': 'slide-in 0.5s ease-out',
		  'slide-out': 'slide-out 0.5s ease-out',
		  'slide-up': 'slide-up 0.5s ease-out',
		  'slide-down': 'slide-down 0.5s ease-out',
		  'float': 'float 5s ease-in-out infinite',
		  'pulse-slow': 'pulse-slow 3s ease-in-out infinite',
		  'spin-slow': 'spin-slow 9s linear infinite',
		  'bounce-subtle': 'bounce-subtle 3s ease-in-out infinite',
		  'shimmer': 'shimmer 2s linear infinite',
		  'ripple': 'ripple 1s linear infinite',
		  'typewriter': 'typewriter 2s steps(40, end)',
		  'blink-caret': 'blink-caret 0.75s step-end infinite',
		  'wave': 'wave 2s linear infinite',
		  'gradient-move': 'gradient-move 6s ease infinite'
		}
	  }
	},
	plugins: [require("tailwindcss-animate")]
  }