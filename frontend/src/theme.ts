export type Theme = {
  outerBg: string;
  panelBg: string;
  panelBorder: string;
  textPrimary: string;
  textBody: string;
  textMuted: string;
  accent: string;
  inputBg: string;
  inputBorder: string;
  ruleColor: string;
  bubbleBg: string;
  bubbleText: string;
  cardBorder: string;
  tagBorder: string;
  tagText: string;
};

export const darkTheme: Theme = {
  outerBg: "oklch(22% 0.008 260)",
  panelBg: "oklch(17% 0.006 260)",
  panelBorder: "oklch(32% 0.01 260)",
  textPrimary: "oklch(95% 0.005 90)",
  textBody: "oklch(70% 0.01 90)",
  textMuted: "oklch(60% 0.01 90)",
  accent: "oklch(78% 0.15 70)",
  inputBg: "oklch(20% 0.008 260)",
  inputBorder: "oklch(35% 0.01 260)",
  ruleColor: "oklch(30% 0.01 260)",
  bubbleBg: "oklch(24% 0.01 260)",
  bubbleText: "oklch(95% 0.005 90)",
  cardBorder: "oklch(32% 0.01 260)",
  tagBorder: "oklch(40% 0.02 260)",
  tagText: "oklch(85% 0.01 90)",
};

export const lightTheme: Theme = {
  outerBg: "oklch(93% 0.008 260)",
  panelBg: "oklch(99% 0.004 90)",
  panelBorder: "oklch(85% 0.01 260)",
  textPrimary: "oklch(20% 0.01 90)",
  textBody: "oklch(35% 0.01 90)",
  textMuted: "oklch(48% 0.01 90)",
  accent: "oklch(48% 0.14 55)",
  inputBg: "oklch(96% 0.006 260)",
  inputBorder: "oklch(82% 0.01 260)",
  ruleColor: "oklch(88% 0.01 260)",
  bubbleBg: "oklch(90% 0.02 260)",
  bubbleText: "oklch(20% 0.01 90)",
  cardBorder: "oklch(85% 0.01 260)",
  tagBorder: "oklch(78% 0.02 260)",
  tagText: "oklch(30% 0.01 90)",
};
