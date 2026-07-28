import { useEffect } from "react";
import { create } from "zustand";
import api from "../lib/api";
import { labelsFor } from "../lib/labels";

// Caches the current tenant's clinic settings (incl. industry) so per-vertical
// labels are available across pages without each one refetching. Populated once
// on first use; Settings calls setClinic() after a save so labels update live.
export const useClinicStore = create((set, get) => ({
  clinic: null,
  loaded: false,
  loading: false,
  fetchClinic: async (force = false) => {
    const { loading, loaded } = get();
    if (loading || (loaded && !force)) return;
    set({ loading: true });
    try {
      const res = await api.get("/clinics/settings");
      if (res.data?.success) set({ clinic: res.data.data, loaded: true });
    } catch {
      /* leave unloaded so a later mount can retry */
    } finally {
      set({ loading: false });
    }
  },
  setClinic: (clinic) => set({ clinic, loaded: true }),
}));

// Hook returning the label set for the current tenant's industry. Triggers the
// one-time clinic fetch on mount (guarded, so many callers share one request).
export function useLabels() {
  const clinic = useClinicStore((s) => s.clinic);
  const fetchClinic = useClinicStore((s) => s.fetchClinic);
  useEffect(() => {
    fetchClinic();
  }, [fetchClinic]);
  return labelsFor(clinic?.industry);
}
