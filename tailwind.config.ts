import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "#F9F9FB",
        "surface-container-low": "#F2F4F6",
        "surface-container-lowest": "#FFFFFF",
        "surface-container": "#ECEEF0",
        "surface-container-high": "#E6E8EA",
        "surface-container-highest": "#E2E4E6",
        primary: "#5F5E60",
        secondary: "#5E5F63",
        tertiary: "#5F5F5F",
        tertiary-container: "#A3A79D",
        "primary-container": "#E0E3E2",
        "primary-fixed": "#C8CBD8",
        "primary-dim": "#4A494B",
        inverse_surface: "#0C0E10",
        "on-surface": "#2D3338",
        "on-surface-variant": "#596065",
        "on-background": "#2D3338",
        "on-primary": "#FFFFFF",
        "on-tertiary": "#FFFFFF",
        error: "#9F403D",
        "on-error": "#FFFFFF",
        "inverse-primary": "#C8CBD8",
        outline: "#757C81",
        "outline-variant": "#ACB3B8",
        "on-outline-variant": "#898F94",
      },
      fontFamily: {
        heading: ["Inter", "sans-serif"],
        body: ["Inter", "sans-serif"],
        label: ["Inter", "sans-serif"],
      },
      fontSize: {
        displayLg: ["57px", { lineHeight: "1.12", letterSpacing: "-0.02em" }],
        displayMd: ["45px", { lineHeight: "1.16", letterSpacing: "-0.02em" }],
        headlineLg: ["32px", { lineHeight: "1.25", letterSpacing: "-0.01em" }],
        headlineMd: ["28px", { lineHeight: "1.29", letterSpacing: "-0.01em" }],
        headlineSm: ["22px", { lineHeight: "1.32", letterSpacing: "-0.01em" }],
        titleLg: ["20px", { lineHeight: "1.40", fontWeight: "bold" }],
        titleMd: ["16px", { lineHeight: "1.50", fontWeight: "bold" }],
        bodyLg: ["16px", { lineHeight: "1.60", color: "#6E6E73" }],
        bodyMd: ["14px", { lineHeight: "1.60", color: "#6E6E73" }],
        labelSm: ["12px", { lineHeight: "1.67", letterSpacing: "0.1em" }],
      },
      borderRadius: {
        xl: "0.75rem",
        md: "0.375rem",
        full: "9999px",
      },
      backdropBlur: {
        glass: "20px",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.4", transform: "scale(0.92)" },
        },
      },
      animation: {
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
