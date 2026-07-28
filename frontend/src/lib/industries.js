// Industry (vertical) options for the onboarding + Settings pickers.
// Keys MUST match the backend templates in backend/services/industry_templates.py.
// The full templates (with prompts) are fetched from GET /industries; this list
// is the lightweight source for dropdown labels so the picker renders instantly.
export const INDUSTRIES = [
  { key: "clinic", label: "Healthcare / Clinic" },
  { key: "real_estate", label: "Real Estate" },
  { key: "restaurant", label: "Restaurant / Hospitality" },
  { key: "salon", label: "Salon & Spa" },
  { key: "services", label: "Home & Local Services" },
  { key: "general", label: "General / Other" },
];

export const DEFAULT_INDUSTRY = "clinic";
